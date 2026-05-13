#!/usr/bin/env python3
"""
Fetch Monte Carlo OpenTelemetry SDK docs at runtime so the instrument-agent
skill stays in sync with the SDK without per-release skill updates.

PyPI is the canonical public source: the SDK's GitHub repo is private, so a
runtime fetch against it would always fail. We fetch the PyPI JSON metadata
for `montecarlo-opentelemetry`, parse the README that PyPI mirrors under
`info.description` for the supported instrumentor list, and emit a JSON
document on stdout. On any failure (network, parse, no instrumentors found)
we fail closed with exit code 1 and a JSON error payload pointing at
https://pypi.org/project/montecarlo-opentelemetry/.

Usage:
    python3 fetch_sdk_docs.py
    python3 fetch_sdk_docs.py --quiet
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

PYPI_URL = "https://pypi.org/pypi/montecarlo-opentelemetry/json"
PYPI_PROJECT_URL = "https://pypi.org/project/montecarlo-opentelemetry/"
READ_BYTES_CAP = 1_000_000  # 1 MB
TIMEOUT_SECONDS = 10

MAX_INSTRUMENTOR_MATCHES = 50

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


def _fetch_bytes(url: str) -> bytes:
    """Fetch up to READ_BYTES_CAP+1 bytes with an explicit timeout.

    Caller must check `len(result) > READ_BYTES_CAP` to detect overruns.
    """
    req = urllib.request.Request(
        url, headers={"User-Agent": "mc-agent-toolkit/instrument-agent"}
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
       SageMaker, Vertex AI, ...).

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
        # "opentelemetry-instrumentation-").
        library = suffix
        package = f"opentelemetry-instrumentation-{suffix}"
        key = (library, package)
        if key in seen:
            continue
        seen.add(key)
        instrumentors.append({"library": library, "package": package})

    return instrumentors


# ---------------------------------------------------------------------------
# PyPI fetch
# ---------------------------------------------------------------------------


def _fetch_pypi() -> dict:
    """Fetch PyPI metadata. Raises on overrun, HTTP, or network errors."""
    raw = _fetch_bytes(PYPI_URL)
    if len(raw) > READ_BYTES_CAP:
        raise OSError(f"PyPI metadata exceeded {READ_BYTES_CAP} byte cap")
    payload = json.loads(raw.decode("utf-8"))
    info = payload.get("info") or {}
    project_urls = info.get("project_urls") or {}
    pypi_project_url = (
        project_urls.get("Homepage")
        or project_urls.get("Source")
        or PYPI_PROJECT_URL
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
        # README content as PyPI knows it; parsed below for the instrumentor
        # list. Captured under a separate key so it is not surfaced in the
        # final SDK metadata block.
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
# Output assembly
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _build_success(
    sdk_meta: dict,
    instrumentors: list[dict],
    warnings: list[str],
) -> dict:
    # Strip the internal `_description` field from the published sdk block.
    public_sdk = {k: v for k, v in sdk_meta.items() if not k.startswith("_")}
    return {
        "source": "pypi",
        "fetched_at": _now_iso(),
        "sdk": public_sdk,
        "supported_instrumentors": instrumentors,
        "warnings": warnings,
    }


def _emit_failure(reason: str, warnings: list[str]) -> None:
    payload = {
        "source": "error",
        "fetched_at": _now_iso(),
        "error": reason,
        "guidance": (
            "Live PyPI fetch failed. Run `pip install montecarlo-opentelemetry` "
            f"and consult {PYPI_PROJECT_URL} to identify the current set of "
            "supported instrumentors."
        ),
        "warnings": warnings,
    }
    print(json.dumps(payload, indent=2))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Fetch Monte Carlo OpenTelemetry SDK metadata from PyPI for the "
            "instrument-agent skill."
        ),
    )
    parser.add_argument(
        "--quiet", action="store_true", help="Suppress stderr warnings"
    )
    args = parser.parse_args()

    warnings: list[str] = []

    # ----- PyPI fetch -------------------------------------------------------
    try:
        sdk_meta = _fetch_pypi()
    except (
        urllib.error.HTTPError,
        urllib.error.URLError,
        TimeoutError,
        OSError,
        json.JSONDecodeError,
    ) as exc:
        reason = f"PyPI fetch failed: {_describe_fetch_error(exc)}"
        warnings.append(reason)
        if not args.quiet:
            for w in warnings:
                print(w, file=sys.stderr)
        _emit_failure(reason, warnings)
        sys.exit(1)

    description = sdk_meta.get("_description") or ""
    if not description.strip():
        reason = "PyPI metadata has no 'info.description' to parse for supported instrumentors."
        warnings.append(reason)
        if not args.quiet:
            for w in warnings:
                print(w, file=sys.stderr)
        _emit_failure(reason, warnings)
        sys.exit(1)

    # ----- Parse PyPI description ------------------------------------------
    instrumentors = _parse_supported_instrumentors(description, warnings)

    if not instrumentors:
        reason = (
            "Parsed PyPI 'info.description' but found no supported instrumentors. "
            "The README format on PyPI may have changed."
        )
        warnings.append(reason)
        if not args.quiet:
            for w in warnings:
                print(w, file=sys.stderr)
        _emit_failure(reason, warnings)
        sys.exit(1)

    if not args.quiet and warnings:
        for w in warnings:
            print(w, file=sys.stderr)

    result = _build_success(sdk_meta, instrumentors, warnings)
    print(json.dumps(result, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()
