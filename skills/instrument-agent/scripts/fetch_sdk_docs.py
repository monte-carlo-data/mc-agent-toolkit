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

    We do NOT exec/eval/compile/import any fetched bytes — this is plain
    regex over text. Bounded to MAX_INSTRUMENTOR_MATCHES to avoid pathological
    inputs.
    """
    instrumentors: list[dict] = []
    seen: set[tuple[str, str]] = set()
    parse_warned = False

    headers = list(_HEADER_RE.finditer(readme_text))
    if not headers:
        return instrumentors

    # Map each header to the next ~20 lines of body text and look for a pip
    # install line within that window.
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

    return instrumentors


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


def _fetch_readme(url: str) -> str:
    """Fetch the SDK README from GitHub. Raises on overrun, HTTP, or network errors.

    GitHub auth is sent only when the URL points at a GitHub host — the
    `MC_SDK_DOCS_URL` testing override may point elsewhere, in which case we
    don't leak the token. Production `SDK_README_URL` is always GitHub.
    """
    is_github = (
        "github.com" in url
        or "githubusercontent.com" in url
        or "api.github.com" in url
    )
    raw = _fetch_bytes(url, with_github_auth=is_github)
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
    return {
        "version": info.get("version") or "",
        "pypi_url": pypi_project_url,
        "requires_dist": [str(r) for r in requires_dist],
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
    warnings: list[str],
) -> dict:
    return {
        "source": "live",
        "fetched_at": _now_iso(),
        "sdk": sdk_meta,
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
    sdk_meta: dict | None = None
    instrumentors: list[dict] = []
    live_failed = False

    readme_url = os.environ.get("MC_SDK_DOCS_URL") or SDK_README_URL

    # ----- README ----------------------------------------------------------
    if args.no_github:
        warnings.append("GitHub fetch skipped via --no-github")
        live_failed = True
    else:
        try:
            readme_text = _fetch_readme(readme_url)
        except (
            urllib.error.HTTPError,
            urllib.error.URLError,
            TimeoutError,
            OSError,
        ) as exc:
            warnings.append(f"Live fetch failed: README {_describe_fetch_error(exc)}")
            live_failed = True

    # ----- PyPI ------------------------------------------------------------
    if args.no_pypi:
        warnings.append("PyPI fetch skipped via --no-pypi")
        live_failed = True
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
            live_failed = True

    # ----- Parse README ---------------------------------------------------
    if readme_text:
        instrumentors = _parse_supported_instrumentors(readme_text, warnings)
        if len(instrumentors) < MIN_PARSED_INSTRUMENTORS:
            warnings.append(
                "README parser found fewer than "
                f"{MIN_PARSED_INSTRUMENTORS} instrumentors — falling back to snapshot."
            )
            live_failed = True

    if not args.quiet and warnings:
        for w in warnings:
            print(w, file=sys.stderr)

    # ----- Live success path ----------------------------------------------
    if not live_failed and readme_text is not None and sdk_meta is not None:
        result = _build_live(sdk_meta, instrumentors, readme_text, warnings)
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
