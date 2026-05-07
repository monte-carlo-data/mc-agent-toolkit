#!/usr/bin/env python3
"""
Tests for fetch_sdk_docs.py — unit-tests internal helpers and an end-to-end
subprocess check for fail-closed behavior.

Run:
    python3 skills/instrument-agent/scripts/test_fetch_sdk_docs.py
    pytest skills/instrument-agent/scripts/test_fetch_sdk_docs.py -q
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
FETCH_SCRIPT = SCRIPT_DIR / "fetch_sdk_docs.py"

sys.path.insert(0, str(SCRIPT_DIR))
from fetch_sdk_docs import (  # noqa: E402
    PRD_CORE_LIBRARIES,
    STALE_AFTER_DAYS,
    _canonical_libraries,
    _is_github_auth_host,
    _missing_prd_core,
    _parse_supported_instrumentors,
    _snapshot_age_days,
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
# test_is_github_auth_host
# ---------------------------------------------------------------------------


def test_is_github_auth_host() -> None:
    print("\n== _is_github_auth_host ==")

    # TRUE cases — exact trusted hosts
    check(
        "github.com is trusted",
        _is_github_auth_host("https://github.com/foo/bar"),
    )
    check(
        "api.github.com is trusted",
        _is_github_auth_host("https://api.github.com/repos/foo/bar"),
    )
    check(
        "raw.githubusercontent.com is trusted",
        _is_github_auth_host(
            "https://raw.githubusercontent.com/foo/bar/main/README.md"
        ),
    )

    # FALSE cases — substring tricks, wrong hosts, malformed
    check(
        "github.com as a path segment is NOT trusted",
        not _is_github_auth_host("https://example.com/github.com/README.md"),
    )
    check(
        "github.com.evil.example is NOT trusted",
        not _is_github_auth_host(
            "https://github.com.evil.example/repos/foo/bar"
        ),
    )
    check(
        "raw.githubusercontent.com as path segment is NOT trusted",
        not _is_github_auth_host(
            "https://example.com/raw.githubusercontent.com/foo/bar/README.md"
        ),
    )
    check(
        "pypi.org is NOT trusted",
        not _is_github_auth_host("https://pypi.org/project/montecarlo-opentelemetry/"),
    )
    check(
        "localhost is NOT trusted",
        not _is_github_auth_host("http://localhost:8080/README.md"),
    )
    check(
        "empty string is NOT trusted",
        not _is_github_auth_host(""),
    )
    check(
        "malformed URL string is NOT trusted",
        not _is_github_auth_host("not-a-url-at-all"),
    )
    check(
        "None-like non-string value is NOT trusted",
        not _is_github_auth_host("://"),
    )


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
# test_missing_prd_core
# ---------------------------------------------------------------------------

_ALL_PRD_CORE = list(PRD_CORE_LIBRARIES)
# PRD core as of F1 fix: langchain, openai, anthropic, crewai, bedrock, sagemaker, vertexai
# langgraph is NOT in PRD_CORE_LIBRARIES.
_PRD_CORE_WITHOUT_LANGGRAPH = [lib for lib in _ALL_PRD_CORE if lib != "langgraph"]


def _make_instrumentors(libraries: list[str]) -> list[dict]:
    return [{"library": lib, "package": f"opentelemetry-instrumentation-{lib}"} for lib in libraries]


def test_missing_prd_core() -> None:
    print("\n== _missing_prd_core ==")

    # Empty list -> all PRD core libraries are missing
    missing = _missing_prd_core([])
    check(
        "empty instrumentors -> full PRD core set returned as missing",
        missing == PRD_CORE_LIBRARIES,
        hint=f"missing={missing!r}, PRD_CORE={PRD_CORE_LIBRARIES!r}",
    )

    # Just langchain -> everything else missing
    missing = _missing_prd_core(_make_instrumentors(["langchain"]))
    check(
        "langchain-only -> other core libs still missing",
        "langchain" not in missing,
        hint=f"missing={missing!r}",
    )
    check(
        "langchain-only -> openai still in missing",
        "openai" in missing,
        hint=f"missing={missing!r}",
    )

    # Full PRD core set (without langgraph, since langgraph is NOT in PRD_CORE_LIBRARIES after F1)
    full_core_instrumentors = _make_instrumentors(_PRD_CORE_WITHOUT_LANGGRAPH)
    missing = _missing_prd_core(full_core_instrumentors)
    check(
        "all PRD core libs present -> missing is empty set",
        missing == set(),
        hint=f"missing={missing!r}",
    )

    # Verify langgraph is NOT in PRD_CORE_LIBRARIES (F1 fix assurance)
    check(
        "langgraph is NOT in PRD_CORE_LIBRARIES (F1 fix)",
        "langgraph" not in PRD_CORE_LIBRARIES,
        hint=f"PRD_CORE_LIBRARIES={set(PRD_CORE_LIBRARIES)!r}",
    )

    # The 7 expected PRD core libs (no langgraph) should satisfy completeness
    expected_core = {"langchain", "openai", "anthropic", "crewai", "bedrock", "sagemaker", "vertexai"}
    missing = _missing_prd_core(_make_instrumentors(list(expected_core)))
    check(
        "7-lib set (langchain/openai/anthropic/crewai/bedrock/sagemaker/vertexai) -> no missing",
        missing == set(),
        hint=f"missing={missing!r}",
    )


# ---------------------------------------------------------------------------
# test_snapshot_age_days
# ---------------------------------------------------------------------------


def test_snapshot_age_days() -> None:
    print("\n== _snapshot_age_days ==")

    today_utc = datetime.now(timezone.utc).date()

    yesterday = (today_utc.replace(day=today_utc.day) - timedelta(days=1)).isoformat()
    age = _snapshot_age_days(yesterday)
    check(
        "snapshot dated yesterday -> age is 1",
        age == 1,
        hint=f"got {age!r}",
    )

    thirty_days_ago = (today_utc - timedelta(days=30)).isoformat()
    age = _snapshot_age_days(thirty_days_ago)
    check(
        "snapshot dated 30 days ago -> age is 30",
        age == 30,
        hint=f"got {age!r}",
    )

    stale_plus_one = (today_utc - timedelta(days=STALE_AFTER_DAYS + 1)).isoformat()
    age = _snapshot_age_days(stale_plus_one)
    check(
        f"snapshot {STALE_AFTER_DAYS + 1} days ago -> age exceeds STALE_AFTER_DAYS",
        age is not None and age > STALE_AFTER_DAYS,
        hint=f"got {age!r}, STALE_AFTER_DAYS={STALE_AFTER_DAYS}",
    )

    age = _snapshot_age_days("not-a-date")
    check(
        "malformed snapshot_date -> returns None",
        age is None,
        hint=f"got {age!r}",
    )

    age = _snapshot_age_days("")
    check(
        "empty snapshot_date -> returns None",
        age is None,
        hint=f"got {age!r}",
    )

    age = _snapshot_age_days(None)  # type: ignore[arg-type]
    check(
        "None snapshot_date -> returns None",
        age is None,
        hint=f"got {age!r}",
    )


# ---------------------------------------------------------------------------
# test_e2e_fail_closed
# ---------------------------------------------------------------------------


def test_e2e_fail_closed() -> None:
    """End-to-end: both fetches disabled + unreachable MC_SDK_DOCS_URL.

    When --no-github and --no-pypi are passed and MC_SDK_DOCS_URL points at an
    unreachable host, the script must either:
      (a) exit non-zero with source="error" if the fallback snapshot is stale
          or missing, OR
      (b) exit 0 with source="fallback" and stale=False if the snapshot is
          fresh enough.

    We do not dictate which outcome occurs (it depends on the local snapshot
    state), but we assert the output is valid JSON and the source field is one
    of the expected values.
    """
    print("\n== end-to-end fail-closed (--no-github --no-pypi) ==")

    env = {**os.environ, "MC_SDK_DOCS_URL": "https://example.invalid/notfound"}
    result = subprocess.run(
        [
            sys.executable,
            str(FETCH_SCRIPT),
            "--no-github",
            "--no-pypi",
            "--quiet",
        ],
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )

    # Output must be valid JSON regardless of success/failure path
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        check(
            "output is valid JSON",
            False,
            hint=f"JSONDecodeError: {exc}; stdout={result.stdout[:200]!r}",
        )
        return

    check(
        "output is valid JSON",
        True,
    )

    source = payload.get("source")
    check(
        "source is one of: fallback, error",
        source in ("fallback", "error"),
        hint=f"got source={source!r}",
    )

    if source == "error":
        # Fail-closed path: exit code must be non-zero
        check(
            "exit code is non-zero on error source",
            result.returncode != 0,
            hint=f"got returncode={result.returncode}",
        )
        check(
            "error payload has 'error' key",
            "error" in payload,
            hint=f"payload keys: {list(payload.keys())}",
        )
    else:
        # Fallback path: snapshot was fresh — exit 0
        check(
            "exit code is 0 on fallback source",
            result.returncode == 0,
            hint=f"got returncode={result.returncode}",
        )
        check(
            "fallback payload has 'stale' key",
            "stale" in payload,
            hint=f"payload keys: {list(payload.keys())}",
        )
        check(
            "fallback payload stale=False (snapshot is fresh)",
            payload.get("stale") is False,
            hint=f"stale={payload.get('stale')!r}",
        )
        check(
            "fallback payload has supported_instrumentors list",
            isinstance(payload.get("supported_instrumentors"), list),
            hint=f"got {type(payload.get('supported_instrumentors'))}",
        )


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main() -> None:
    tests = [
        test_is_github_auth_host,
        test_canonical_libraries,
        test_parse_supported_instrumentors,
        test_missing_prd_core,
        test_snapshot_age_days,
        test_e2e_fail_closed,
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
