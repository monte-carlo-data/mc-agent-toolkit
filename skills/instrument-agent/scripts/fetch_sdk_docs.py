#!/usr/bin/env python3
"""
Fetch Monte Carlo OpenTelemetry SDK docs at runtime so the instrument-agent
skill stays in sync with the SDK without per-release skill updates.

Pulls the README from GitHub and metadata from PyPI, parses the README for
the supported instrumentor list, and emits a JSON document on stdout.

Falls back to the sibling `instrumentor_map.json` snapshot when the live
fetch fails. If the snapshot is older than STALE_AFTER_DAYS and the live
fetch also failed, fails closed (exit 1) with an actionable error.

Usage:
    python3 fetch_sdk_docs.py
    python3 fetch_sdk_docs.py --no-pypi
    python3 fetch_sdk_docs.py --no-github
    python3 fetch_sdk_docs.py --quiet

Set GITHUB_TOKEN env var to raise the GitHub raw-content rate limit from 60
to 5,000 requests/hour. Set MC_SDK_DOCS_URL to override the README URL for
testing (PyPI URL cannot be overridden).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

REPO = "monte-carlo-data/montecarlo-opentelemetry"
SDK_README_URL = f"https://raw.githubusercontent.com/{REPO}/main/README.md"
PYPI_URL = "https://pypi.org/pypi/montecarlo-opentelemetry/json"
READ_BYTES_CAP = 1_000_000  # 1 MB
TIMEOUT_SECONDS = 10
STALE_AFTER_DAYS = 180  # ~6 months — after this, fail-closed if live fetch also fails

README_EXCERPT_BYTES = 2_048
MAX_INSTRUMENTOR_MATCHES = 50
MIN_PARSED_INSTRUMENTORS = 2

# Core libraries the PRD requires the skill to support. A live parse that
# misses any of these is treated as below-threshold and falls back to the
# committed snapshot. Identifiers are package suffixes (the slug after
# "opentelemetry-instrumentation-") plus "langgraph", which has no separate
# package — it rides on opentelemetry-instrumentation-langchain and is
# surfaced via the README's "# For Langchain/LangGraph" header.
PRD_CORE_LIBRARIES = frozenset(
    {
        "langchain",
        "langgraph",
        "openai",
        "anthropic",
        "crewai",
        "bedrock",
        "sagemaker",
        "vertexai",
    }
)

# "# For Langchain/LangGraph" or "### For OpenAI"
_HEADER_RE = re.compile(
    r"^\s*(?:#{1,6}\s+|<!--\s*)?For\s+([A-Za-z0-9_./+\- ]+?)\s*(?:-->|$)",
    re.MULTILINE,
)
# pip install "opentelemetry-instrumentation-<lib><=0.53.4>"
_PIP_INSTALL_RE = re.compile(
    r"""pip\s+install\s+["']?
        (opentelemetry-instrumentation-[a-z0-9_\-]+)
        \s*
        (
            (?:[<>=!~]=?|===)\s*[A-Za-z0-9_.\-+*]+
            (?:\s*,\s*(?:[<>=!~]=?|===)\s*[A-Za-z0-9_.\-+*]+)*
        )?
        ["']?""",
    re.IGNORECASE | re.VERBOSE,
)
# Markdown bullet listing each supported package as a PyPI link, e.g.
#   * [opentelemetry-instrumentation-anthropic](https://pypi.org/project/opentelemetry-instrumentation-anthropic/)
_BULLET_PACKAGE_RE = re.compile(
    r"""^\s*[-*+]\s+
        \[\s*opentelemetry-instrumentation-([a-z0-9][a-z0-9_\-]*)\s*\]
        \(\s*https?://pypi\.org/project/opentelemetry-instrumentation-[a-z0-9_\-]+/?\s*\)
    """,
    re.MULTILINE | re.IGNORECASE | re.VERBOSE,
)


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------


def _build_headers(*, with_github_auth: bool) -> dict[str, str]:
    """Build request headers. GITHUB_TOKEN is only included when explicitly opted
    into — never sent to non-GitHub destinations like pypi.org.
    """
    headers = {"User-Agent": "mc-agent-toolkit/instrument-agent"}
    if with_github_auth:
        token = os.environ.get("GITHUB_TOKEN")
        if token:
            headers["Authorization"] = f"Bearer {token}"
    return headers


def _fetch_bytes(url: str, *, with_github_auth: bool) -> bytes:
    """Fetch up to READ_BYTES_CAP+1 bytes with an explicit timeout.

    `with_github_auth` controls whether GITHUB_TOKEN (if set) is sent in the
    Authorization header. Set True only for GitHub-owned destinations.

    Caller must check `len(result) > READ_BYTES_CAP` to detect overruns.
    """
    req = urllib.request.Request(
        url, headers=_build_headers(with_github_auth=with_github_auth)
    )
    with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
        # Read one extra byte so the caller can detect responses that exceed
        # the cap (rather than silently truncating).
        return resp.read(READ_BYTES_CAP + 1)


# ---------------------------------------------------------------------------
# README parsing
# ---------------------------------------------------------------------------


def _canonical_libraries(label: str) -> list[str]:
    """Map a header label to canonical lowercase library identifiers.

    "Langchain/LangGraph" -> ["langchain", "langgraph"]
    "OpenAI" -> ["openai"]
    "Google Gen AI" -> ["google_gen_ai"]
    """
    parts = re.split(r"[/,&+]| and ", label)
    libs: list[str] = []
    for part in parts:
        cleaned = part.strip()
        if not cleaned:
            continue
        slug = re.sub(r"[^a-z0-9]+", "_", cleaned.lower()).strip("_")
        if slug and slug not in libs:
            libs.append(slug)
    return libs


def _parse_supported_instrumentors(
    readme_text: str,
    warnings: list[str],
) -> list[dict]:
    """Extract `(library, package, version_constraint)` tuples from the README.

    The README has two surfaces describing supported instrumentors:

    1. Quick-start `# For <Label>` headers paired with a `pip install` line —
       these include explicit version constraints (e.g. `<=0.53.4`).
    2. A bullet list further down ("See a selection of available instrumentation
       libraries below.") with one PyPI link per supported package — no version
       constraints, but covers the long tail (Anthropic, Bedrock, CrewAI,
       SageMaker, Vertex AI, …).

    We parse both, deduplicate by `(library, package)`, and return the union.
    Header-derived entries take precedence so any version_constraint they
    surface is preserved.

    We do NOT exec/eval/compile/import any fetched bytes — this is plain
    regex over text. Bounded to MAX_INSTRUMENTOR_MATCHES to avoid pathological
    inputs.
    """
    instrumentors: list[dict] = []
    seen: set[tuple[str, str]] = set()
    parse_warned = False

    # ----- Pass 1: header + pip install pairs (with version_constraint) -----
    headers = list(_HEADER_RE.finditer(readme_text))
    for idx, header in enumerate(headers):
        if len(instrumentors) >= MAX_INSTRUMENTOR_MATCHES:
            break

        body_start = header.end()
        body_end = (
            headers[idx + 1].start() if idx + 1 < len(headers) else len(readme_text)
        )
        # Cap the body window so a missing next-header doesn't make us scan
        # the whole document.
        body_end = min(body_end, body_start + 4_000)
        body = readme_text[body_start:body_end]

        pip_match = _PIP_INSTALL_RE.search(body)
        if not pip_match:
            continue

        package = pip_match.group(1).strip()
        version_constraint = (pip_match.group(2) or "").strip() or None
        libraries = _canonical_libraries(header.group(1))
        if not libraries:
            if not parse_warned:
                warnings.append(
                    f"Could not derive canonical library from header: {header.group(1)!r}"
                )
                parse_warned = True
            continue

        for library in libraries:
            key = (library, package)
            if key in seen:
                continue
            seen.add(key)
            entry: dict = {"library": library, "package": package}
            if version_constraint:
                entry["version_constraint"] = version_constraint
            instrumentors.append(entry)
            if len(instrumentors) >= MAX_INSTRUMENTOR_MATCHES:
                break

    # ----- Pass 2: PyPI-link bullet list (no version_constraint) ------------
    for match in _BULLET_PACKAGE_RE.finditer(readme_text):
        if len(instrumentors) >= MAX_INSTRUMENTOR_MATCHES:
            break
        suffix = match.group(1).lower()
        # The library identifier is the package suffix (post
        # "opentelemetry-instrumentation-"). It already lines up with PRD
        # canonical IDs for the core PRD libraries (anthropic, bedrock,
        # crewai, sagemaker, vertexai, …).
        library = suffix
        package = f"opentelemetry-instrumentation-{suffix}"
        key = (library, package)
        if key in seen:
            continue
        seen.add(key)
        instrumentors.append({"library": library, "package": package})

    return instrumentors


def _missing_prd_core(instrumentors: list[dict]) -> set[str]:
    """Return the set of PRD core libraries not represented in `instrumentors`.

    A non-empty result means the live parse is below threshold and the caller
    should fall back to the snapshot — even if the raw count met
    MIN_PARSED_INSTRUMENTORS.
    """
    found = {entry.get("library") for entry in instrumentors if isinstance(entry, dict)}
    return {lib for lib in PRD_CORE_LIBRARIES if lib not in found}


def _readme_excerpt(readme_text: str) -> str:
    """First ~README_EXCERPT_BYTES of UTF-8 text, cut on a char boundary."""
    encoded = readme_text.encode("utf-8")
    if len(encoded) <= README_EXCERPT_BYTES:
        return readme_text
    truncated = encoded[:README_EXCERPT_BYTES]
    # Trim incomplete trailing UTF-8 sequence rather than crashing on decode.
    return truncated.decode("utf-8", errors="ignore")


# ---------------------------------------------------------------------------
# Live fetchers
# ---------------------------------------------------------------------------


_GITHUB_AUTH_HOSTS = frozenset(
    {"github.com", "raw.githubusercontent.com", "api.github.com"}
)


def _is_github_auth_host(url: str) -> bool:
    """True only when the URL's hostname is exactly one of the trusted GitHub
    hosts. Substring matching would let an override like
    `https://example.com/github.com/README.md` leak GITHUB_TOKEN — parse the
    URL and compare the hostname exactly.
    """
    try:
        parsed = urllib.parse.urlparse(url)
    except (ValueError, AttributeError):
        return False
    hostname = (parsed.hostname or "").lower()
    return hostname in _GITHUB_AUTH_HOSTS


def _fetch_readme(url: str) -> str:
    """Fetch the SDK README. Raises on overrun, HTTP, or network errors.

    GitHub auth is sent only when the URL's hostname is exactly one of the
    trusted GitHub hosts. The `MC_SDK_DOCS_URL` testing override and any
    other non-GitHub URL never receive the token. Production `SDK_README_URL`
    points at `raw.githubusercontent.com`.
    """
    raw = _fetch_bytes(url, with_github_auth=_is_github_auth_host(url))
    if len(raw) > READ_BYTES_CAP:
        raise OSError(f"README exceeded {READ_BYTES_CAP} byte cap")
    return raw.decode("utf-8", errors="replace")


def _fetch_pypi() -> dict:
    """Fetch PyPI metadata. Raises on overrun, HTTP, or network errors.

    GITHUB_TOKEN is never sent to pypi.org.
    """
    raw = _fetch_bytes(PYPI_URL, with_github_auth=False)
    if len(raw) > READ_BYTES_CAP:
        raise OSError(f"PyPI metadata exceeded {READ_BYTES_CAP} byte cap")
    payload = json.loads(raw.decode("utf-8"))
    info = payload.get("info") or {}
    project_urls = info.get("project_urls") or {}
    pypi_project_url = (
        project_urls.get("Homepage")
        or project_urls.get("Source")
        or "https://pypi.org/project/montecarlo-opentelemetry/"
    )
    requires_dist = info.get("requires_dist") or []
    if not isinstance(requires_dist, list):
        requires_dist = []
    description = info.get("description") or ""
    if not isinstance(description, str):
        description = ""
    return {
        "version": info.get("version") or "",
        "pypi_url": pypi_project_url,
        "requires_dist": [str(r) for r in requires_dist],
        # README content as PyPI knows it; used as a backup source when the
        # GitHub README fetch fails. Captured under a separate key so it is
        # not surfaced in the final SDK metadata block.
        "_description": description,
    }


def _describe_fetch_error(exc: BaseException) -> str:
    if isinstance(exc, urllib.error.HTTPError):
        return f"HTTP {exc.code} {exc.reason}"
    if isinstance(exc, urllib.error.URLError):
        return f"network error: {exc.reason}"
    if isinstance(exc, TimeoutError):
        return f"timed out after {TIMEOUT_SECONDS}s"
    return f"{type(exc).__name__}: {exc}"


# ---------------------------------------------------------------------------
# Fallback
# ---------------------------------------------------------------------------


def _fallback_path() -> Path:
    return Path(__file__).parent / "instrumentor_map.json"


def _load_fallback() -> dict:
    """Read and lightly validate the sibling instrumentor_map.json snapshot.

    Raises FileNotFoundError if missing, ValueError if malformed.
    """
    path = _fallback_path()
    if not path.exists():
        raise FileNotFoundError(str(path))
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"could not parse {path.name}: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError(f"{path.name} must be a JSON object")
    if "snapshot_date" not in data:
        raise ValueError(f"{path.name} missing required 'snapshot_date'")
    if "supported_instrumentors" not in data:
        raise ValueError(f"{path.name} missing required 'supported_instrumentors'")
    return data


def _snapshot_age_days(snapshot_date: str) -> int | None:
    try:
        snap = date.fromisoformat(snapshot_date)
    except (TypeError, ValueError):
        return None
    return (date.today() - snap).days


# ---------------------------------------------------------------------------
# Output assembly
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _build_live(
    sdk_meta: dict | None,
    instrumentors: list[dict],
    readme_text: str,
    readme_source: str,
    warnings: list[str],
) -> dict:
    # Strip the internal `_description` field from the published sdk block —
    # it is only used as an internal README backup source.
    public_sdk = None
    if sdk_meta is not None:
        public_sdk = {k: v for k, v in sdk_meta.items() if not k.startswith("_")}
    return {
        "source": "live",
        "readme_source": readme_source,
        "fetched_at": _now_iso(),
        "sdk": public_sdk,
        "supported_instrumentors": instrumentors,
        "readme_excerpt": _readme_excerpt(readme_text),
        "warnings": warnings,
    }


def _build_fallback(
    snapshot: dict,
    age_days: int | None,
    stale: bool,
    warnings: list[str],
) -> dict:
    snapshot_date = snapshot.get("snapshot_date", "")
    age_blurb = f"{age_days} days ago" if age_days is not None else "an unknown time ago"
    warnings.append(
        f"Using fallback snapshot from {snapshot_date} — last verified {age_blurb}."
    )
    return {
        "source": "fallback",
        "fetched_at": _now_iso(),
        "snapshot_date": snapshot_date,
        "stale": stale,
        "sdk": None,
        "supported_instrumentors": snapshot.get("supported_instrumentors", []),
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def _emit_failure(reason: str, warnings: list[str]) -> None:
    payload = {
        "source": "error",
        "fetched_at": _now_iso(),
        "error": reason,
        "guidance": (
            "Live fetch failed and the local snapshot is unavailable or stale. "
            "Run `pip install montecarlo-opentelemetry` and consult "
            "https://pypi.org/project/montecarlo-opentelemetry/ to identify "
            "the current set of supported instrumentors."
        ),
        "warnings": warnings,
    }
    print(json.dumps(payload, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Fetch Monte Carlo OpenTelemetry SDK docs (GitHub README + PyPI "
            "metadata) for the instrument-agent skill."
        ),
    )
    parser.add_argument(
        "--no-pypi", action="store_true", help="Skip the PyPI fetch (testing)"
    )
    parser.add_argument(
        "--no-github", action="store_true", help="Skip the GitHub README fetch (testing)"
    )
    parser.add_argument(
        "--quiet", action="store_true", help="Suppress stderr warnings"
    )
    args = parser.parse_args()

    warnings: list[str] = []
    readme_text: str | None = None
    readme_source: str | None = None
    sdk_meta: dict | None = None
    instrumentors: list[dict] = []

    readme_url = os.environ.get("MC_SDK_DOCS_URL") or SDK_README_URL

    # ----- README (GitHub) -------------------------------------------------
    if args.no_github:
        warnings.append("GitHub fetch skipped via --no-github")
    else:
        try:
            readme_text = _fetch_readme(readme_url)
            readme_source = "github"
        except (
            urllib.error.HTTPError,
            urllib.error.URLError,
            TimeoutError,
            OSError,
        ) as exc:
            warnings.append(f"Live fetch failed: README {_describe_fetch_error(exc)}")

    # ----- PyPI ------------------------------------------------------------
    if args.no_pypi:
        warnings.append("PyPI fetch skipped via --no-pypi")
    else:
        try:
            sdk_meta = _fetch_pypi()
        except (
            urllib.error.HTTPError,
            urllib.error.URLError,
            TimeoutError,
            OSError,
            json.JSONDecodeError,
        ) as exc:
            warnings.append(f"Live fetch failed: PyPI {_describe_fetch_error(exc)}")

    # ----- Backup README source: PyPI info.description ---------------------
    # If the GitHub README fetch failed (or was skipped) but PyPI succeeded
    # and exposes a description, use it as the README source. The PyPI
    # description for `montecarlo-opentelemetry` mirrors the GitHub README,
    # so the same parser produces the same result.
    if readme_text is None and sdk_meta is not None:
        description = sdk_meta.get("_description") or ""
        if description.strip():
            readme_text = description
            readme_source = "pypi"
            warnings.append(
                "Using PyPI 'info.description' as README source "
                "(GitHub README fetch failed or skipped)."
            )

    # ----- Parse README ----------------------------------------------------
    if readme_text:
        instrumentors = _parse_supported_instrumentors(readme_text, warnings)

    parse_count_below_threshold = len(instrumentors) < MIN_PARSED_INSTRUMENTORS
    missing_core = _missing_prd_core(instrumentors) if readme_text else set()

    if readme_text is not None and parse_count_below_threshold:
        warnings.append(
            "README parser found fewer than "
            f"{MIN_PARSED_INSTRUMENTORS} instrumentors — falling back to snapshot."
        )
    if readme_text is not None and missing_core:
        warnings.append(
            "Live parse missing PRD core libraries: "
            f"{sorted(missing_core)} — falling back to snapshot for completeness."
        )

    # Live succeeds when we can produce a usable instrumentor list, regardless
    # of which source supplied the README. Fall back when:
    # (a) neither the GitHub README nor the PyPI description was available, OR
    # (b) the parser found fewer than MIN_PARSED_INSTRUMENTORS entries, OR
    # (c) the parser missed any PRD core library — partial coverage is worse
    #     than the snapshot's known-complete coverage.
    live_failed = (
        readme_text is None
        or parse_count_below_threshold
        or bool(missing_core)
    )

    if not args.quiet and warnings:
        for w in warnings:
            print(w, file=sys.stderr)

    # ----- Live success path -----------------------------------------------
    if not live_failed and readme_text is not None and readme_source is not None:
        if sdk_meta is None:
            warnings.append(
                "Live instrumentor list available but PyPI metadata "
                "is missing; sdk version/requires_dist will be null."
            )
        result = _build_live(
            sdk_meta, instrumentors, readme_text, readme_source, warnings
        )
        print(json.dumps(result, indent=2))
        sys.exit(0)

    # ----- Fallback -------------------------------------------------------
    try:
        snapshot = _load_fallback()
    except FileNotFoundError:
        _emit_failure(
            "Fallback snapshot instrumentor_map.json is missing.", warnings
        )
        sys.exit(1)
    except ValueError as exc:
        _emit_failure(f"Fallback snapshot is malformed: {exc}", warnings)
        sys.exit(1)

    age_days = _snapshot_age_days(snapshot.get("snapshot_date", ""))
    stale = age_days is None or age_days > STALE_AFTER_DAYS

    if stale and live_failed:
        snapshot_date = snapshot.get("snapshot_date", "<unknown>")
        _emit_failure(
            (
                f"Live fetch failed and the fallback snapshot from {snapshot_date} "
                f"is older than {STALE_AFTER_DAYS} days."
            ),
            warnings,
        )
        sys.exit(1)

    result = _build_fallback(snapshot, age_days, stale, warnings)
    print(json.dumps(result, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()
