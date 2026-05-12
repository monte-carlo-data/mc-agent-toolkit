#!/usr/bin/env python3
"""
Tests for fetch_sdk_docs.py — unit-tests internal helpers and an end-to-end
subprocess check for the PyPI-fetch-failure fail-closed path.

Run:
    python3 skills/instrument-agent/tests/test_fetch_sdk_docs.py
    pytest skills/instrument-agent/tests/test_fetch_sdk_docs.py -q
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

TESTS_DIR = Path(__file__).parent
SKILL_ROOT = TESTS_DIR.parent
SCRIPT_DIR = SKILL_ROOT / "scripts"
FETCH_SCRIPT = SCRIPT_DIR / "fetch_sdk_docs.py"

sys.path.insert(0, str(SCRIPT_DIR))
from fetch_sdk_docs import (  # noqa: E402
    _build_success,
    _canonical_libraries,
    _parse_supported_instrumentors,
)

PASSED = 0
FAILED = 0


def check(label: str, condition: bool, hint: str = "") -> None:
    """Record a single check.

    Increments the global PASSED/FAILED counters and prints a PASS/FAIL line.
    On failure, raises AssertionError so pytest catches per-test failures
    (each `test_*` function fails on its first failed check). The standalone
    runner in `main()` wraps each test in its own try/except so all tests
    still run regardless of intermediate failures.
    """
    global PASSED, FAILED
    if condition:
        PASSED += 1
        print(f"  PASS  {label}")
        return
    FAILED += 1
    suffix = f" — {hint}" if hint else ""
    msg = f"FAIL  {label}{suffix}"
    print(f"  {msg}")
    raise AssertionError(msg)


# ---------------------------------------------------------------------------
# test_canonical_libraries
# ---------------------------------------------------------------------------


def test_canonical_libraries() -> None:
    print("\n== _canonical_libraries ==")

    result = _canonical_libraries("Langchain/LangGraph")
    check(
        "Langchain/LangGraph -> [langchain, langgraph]",
        result == ["langchain", "langgraph"],
        hint=f"got {result!r}",
    )

    result = _canonical_libraries("OpenAI")
    check(
        "OpenAI -> [openai]",
        result == ["openai"],
        hint=f"got {result!r}",
    )

    result = _canonical_libraries("Google Gen AI")
    check(
        "Google Gen AI -> [google_gen_ai]",
        result == ["google_gen_ai"],
        hint=f"got {result!r}",
    )

    result = _canonical_libraries("")
    check(
        "empty string -> []",
        result == [],
        hint=f"got {result!r}",
    )

    result = _canonical_libraries("   /   ")
    check(
        "whitespace-only slashes -> []",
        result == [],
        hint=f"got {result!r}",
    )

    result = _canonical_libraries("///")
    check(
        "only separators -> []",
        result == [],
        hint=f"got {result!r}",
    )


# ---------------------------------------------------------------------------
# test_parse_supported_instrumentors
# ---------------------------------------------------------------------------

_FIXTURE_README = """\
# Monte Carlo OpenTelemetry SDK

## For OpenAI

Install the following instrumentor:

```bash
pip install "opentelemetry-instrumentation-openai<=0.53.4"
```

## For Anthropic

```bash
pip install opentelemetry-instrumentation-anthropic
```

## Available instrumentation libraries

See a selection of available instrumentation libraries below.

* [opentelemetry-instrumentation-anthropic](https://pypi.org/project/opentelemetry-instrumentation-anthropic/)
* [opentelemetry-instrumentation-crewai](https://pypi.org/project/opentelemetry-instrumentation-crewai/)
* [opentelemetry-instrumentation-bedrock](https://pypi.org/project/opentelemetry-instrumentation-bedrock/)
"""


def test_parse_supported_instrumentors() -> None:
    print("\n== _parse_supported_instrumentors ==")
    warnings: list[str] = []
    instrumentors = _parse_supported_instrumentors(_FIXTURE_README, warnings)

    libraries = {entry["library"] for entry in instrumentors}

    check(
        "openai found via header+pip-install surface",
        "openai" in libraries,
        hint=f"libraries={libraries!r}",
    )
    check(
        "anthropic found (header or bullet list surface)",
        "anthropic" in libraries,
        hint=f"libraries={libraries!r}",
    )
    check(
        "crewai found via bullet list surface",
        "crewai" in libraries,
        hint=f"libraries={libraries!r}",
    )
    check(
        "bedrock found via bullet list surface",
        "bedrock" in libraries,
        hint=f"libraries={libraries!r}",
    )

    # Entries from header+pip should carry version_constraint
    openai_entry = next(
        (e for e in instrumentors if e.get("library") == "openai"), None
    )
    check(
        "openai entry has version_constraint from pip install line",
        openai_entry is not None
        and "version_constraint" in openai_entry
        and "0.53.4" in (openai_entry.get("version_constraint") or ""),
        hint=f"openai_entry={openai_entry!r}",
    )

    # Bullet-only entries should NOT carry version_constraint
    crewai_entry = next(
        (e for e in instrumentors if e.get("library") == "crewai"), None
    )
    check(
        "crewai (bullet-only) has no version_constraint",
        crewai_entry is not None and "version_constraint" not in crewai_entry,
        hint=f"crewai_entry={crewai_entry!r}",
    )

    # Deduplication: anthropic appears in both surfaces — only one entry
    anthropic_entries = [e for e in instrumentors if e.get("library") == "anthropic"]
    check(
        "anthropic deduplicated to a single entry",
        len(anthropic_entries) == 1,
        hint=f"count={len(anthropic_entries)}",
    )


# ---------------------------------------------------------------------------
# test_parse_failure_paths
# ---------------------------------------------------------------------------


def test_parse_failure_paths() -> None:
    """Description-parse must yield an empty list (caller fails closed)."""
    print("\n== _parse_supported_instrumentors failure paths ==")

    warnings: list[str] = []
    instrumentors = _parse_supported_instrumentors("", warnings)
    check(
        "empty description -> no instrumentors",
        instrumentors == [],
        hint=f"got {instrumentors!r}",
    )

    warnings = []
    instrumentors = _parse_supported_instrumentors(
        "# Some unrelated readme\n\nNothing to see here.\n", warnings
    )
    check(
        "readme without instrumentor markers -> no instrumentors",
        instrumentors == [],
        hint=f"got {instrumentors!r}",
    )


# ---------------------------------------------------------------------------
# test_build_success_shape
# ---------------------------------------------------------------------------


def test_build_success_shape() -> None:
    """Verify the success-path JSON shape — keys and types only."""
    print("\n== _build_success output shape ==")

    sdk_meta = {
        "version": "1.2.3",
        "pypi_url": "https://pypi.org/project/montecarlo-opentelemetry/",
        "requires_dist": ["opentelemetry-api>=1.0", "wrapt<2"],
        "_description": "# README body here",
    }
    instrumentors = [
        {
            "library": "openai",
            "package": "opentelemetry-instrumentation-openai",
            "version_constraint": "<=0.53.4",
        }
    ]
    warnings: list[str] = []

    result = _build_success(sdk_meta, instrumentors, warnings)

    check(
        "source == 'pypi'",
        result.get("source") == "pypi",
        hint=f"source={result.get('source')!r}",
    )
    check(
        "fetched_at present",
        isinstance(result.get("fetched_at"), str) and bool(result["fetched_at"]),
        hint=f"fetched_at={result.get('fetched_at')!r}",
    )
    check(
        "sdk block present and a dict",
        isinstance(result.get("sdk"), dict),
        hint=f"sdk={result.get('sdk')!r}",
    )
    check(
        "sdk block does not leak internal _description",
        "_description" not in (result.get("sdk") or {}),
        hint=f"sdk keys={list((result.get('sdk') or {}).keys())}",
    )
    check(
        "sdk.version preserved",
        (result.get("sdk") or {}).get("version") == "1.2.3",
        hint=f"sdk={result.get('sdk')!r}",
    )
    check(
        "sdk.requires_dist preserved",
        (result.get("sdk") or {}).get("requires_dist") == [
            "opentelemetry-api>=1.0",
            "wrapt<2",
        ],
        hint=f"sdk={result.get('sdk')!r}",
    )
    check(
        "supported_instrumentors matches input",
        result.get("supported_instrumentors") == instrumentors,
        hint=f"supported_instrumentors={result.get('supported_instrumentors')!r}",
    )
    check(
        "warnings list present",
        isinstance(result.get("warnings"), list),
        hint=f"warnings={result.get('warnings')!r}",
    )


# ---------------------------------------------------------------------------
# test_pypi_fetch_success (mocked)
# ---------------------------------------------------------------------------


def _make_pypi_payload(description: str, version: str = "1.2.3") -> bytes:
    return json.dumps(
        {
            "info": {
                "version": version,
                "description": description,
                "project_urls": {
                    "Homepage": "https://pypi.org/project/montecarlo-opentelemetry/",
                },
                "requires_dist": ["opentelemetry-api>=1.0"],
            }
        }
    ).encode("utf-8")


def test_pypi_fetch_success() -> None:
    """Mocked PyPI success path: _fetch_pypi parses the JSON and returns metadata."""
    print("\n== _fetch_pypi (mocked success) ==")

    from fetch_sdk_docs import _fetch_pypi

    payload = _make_pypi_payload(_FIXTURE_README)
    with patch("fetch_sdk_docs._fetch_bytes", return_value=payload):
        result = _fetch_pypi()

    check(
        "version extracted from PyPI payload",
        result.get("version") == "1.2.3",
        hint=f"got {result!r}",
    )
    check(
        "pypi_url extracted from project_urls.Homepage",
        result.get("pypi_url") == "https://pypi.org/project/montecarlo-opentelemetry/",
        hint=f"got {result!r}",
    )
    check(
        "requires_dist list preserved",
        result.get("requires_dist") == ["opentelemetry-api>=1.0"],
        hint=f"got {result!r}",
    )
    check(
        "_description carries README body",
        result.get("_description") == _FIXTURE_README,
        hint=f"got {result.get('_description')!r}",
    )


def test_pypi_fetch_failure() -> None:
    """Mocked PyPI failure path: _fetch_pypi propagates the error."""
    print("\n== _fetch_pypi (mocked failure) ==")

    import urllib.error

    from fetch_sdk_docs import _fetch_pypi

    with patch(
        "fetch_sdk_docs._fetch_bytes",
        side_effect=urllib.error.URLError("simulated network failure"),
    ):
        raised = False
        try:
            _fetch_pypi()
        except urllib.error.URLError:
            raised = True
        check(
            "URLError propagates out of _fetch_pypi",
            raised,
            hint="_fetch_pypi swallowed URLError instead of propagating",
        )


# ---------------------------------------------------------------------------
# test_e2e_fail_closed_on_pypi_failure
# ---------------------------------------------------------------------------


def test_e2e_fail_closed_on_pypi_failure() -> None:
    """End-to-end: when PyPI is unreachable, the script exits non-zero with
    source="error" and a JSON payload that includes guidance.
    """
    print("\n== end-to-end fail-closed on PyPI failure ==")

    # Monkey-patch the PYPI_URL via a wrapper script that imports and mutates
    # the module, then runs main(). We use a one-off Python invocation so the
    # subprocess shape mirrors normal usage but routes the fetch at an
    # unreachable host.
    runner = (
        "import sys; sys.path.insert(0, %r);"
        "import fetch_sdk_docs as m;"
        "m.PYPI_URL = 'https://example.invalid/notfound';"
        "m.main()"
    ) % str(SCRIPT_DIR)
    result = subprocess.run(
        [sys.executable, "-c", runner, "--quiet"],
        capture_output=True,
        text=True,
        timeout=30,
    )

    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        check(
            "output is valid JSON",
            False,
            hint=f"JSONDecodeError: {exc}; stdout={result.stdout[:200]!r}",
        )
        return

    check("output is valid JSON", True)
    check(
        "source == 'error' on unreachable PyPI",
        payload.get("source") == "error",
        hint=f"source={payload.get('source')!r}",
    )
    check(
        "exit code is non-zero on error",
        result.returncode != 0,
        hint=f"returncode={result.returncode}",
    )
    check(
        "error payload has 'error' key",
        "error" in payload,
        hint=f"payload keys={list(payload.keys())}",
    )
    check(
        "error payload has 'guidance' key pointing at PyPI",
        isinstance(payload.get("guidance"), str)
        and "pypi.org/project/montecarlo-opentelemetry" in payload["guidance"],
        hint=f"guidance={payload.get('guidance')!r}",
    )


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main() -> None:
    tests = [
        test_canonical_libraries,
        test_parse_supported_instrumentors,
        test_parse_failure_paths,
        test_build_success_shape,
        test_pypi_fetch_success,
        test_pypi_fetch_failure,
        test_e2e_fail_closed_on_pypi_failure,
    ]
    # Run every test even when an early one fails — `check()` raises on the
    # first failure inside a single test, but we want a complete pass/fail
    # summary across all tests when invoked standalone. pytest invokes each
    # `test_*` directly without going through main(), so per-test fast-fail
    # via AssertionError is the right behavior under pytest.
    for fn in tests:
        try:
            fn()
        except AssertionError:
            # Already logged by check(); continue so the summary covers all tests.
            pass
    print(f"\n{'=' * 40}")
    print(f"Results: {PASSED} passed, {FAILED} failed")
    sys.exit(0 if FAILED == 0 else 1)


if __name__ == "__main__":
    main()
