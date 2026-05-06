#!/usr/bin/env python3
"""
Smoke test for detect_libraries.py — runs it against each fixture in
test_fixtures/ and asserts the JSON output is correct.

Run:
    python3 skills/instrument-agent/scripts/test_detect_libraries.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
DETECT_SCRIPT = SCRIPT_DIR / "detect_libraries.py"
FIXTURES_DIR = SCRIPT_DIR / "test_fixtures"

PASSED = 0
FAILED = 0


def run_detect(fixture: str) -> dict:
    """Run detect_libraries.py against a fixture and return parsed JSON."""
    result = subprocess.run(
        [sys.executable, str(DETECT_SCRIPT), str(FIXTURES_DIR / fixture)],
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    return json.loads(result.stdout)


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


def _suggested_libraries(out: dict) -> set[str]:
    return {
        entry.get("library")
        for entry in out.get("suggested_instrumentors", [])
        if isinstance(entry, dict)
    }


def _unsupported_libraries(out: dict) -> set[str]:
    return {
        entry.get("library")
        for entry in out.get("unsupported", [])
        if isinstance(entry, dict)
    }


def test_requirements_txt() -> None:
    print("\n== requirements.txt ==")
    out = run_detect("requirements")
    detected = out["detected"]
    check("detects langchain", "langchain" in detected)
    check("detects openai", "openai" in detected)
    check("detects anthropic", "anthropic" in detected)
    check(
        "runtime is long_running",
        out["runtime"] == "long_running",
        hint=f"got {out['runtime']!r}",
    )
    check(
        "no existing setup",
        out["existing_setup"]["found"] is False,
        hint=f"existing_setup={out['existing_setup']!r}",
    )
    check(
        "no serverless signals",
        out["serverless_signals"] == [],
        hint=f"got {out['serverless_signals']!r}",
    )
    check(
        "suggested_instrumentors aligns with detected",
        _suggested_libraries(out) >= {"langchain", "openai", "anthropic"},
    )
    check(
        "unsupported is empty (no boto3 in fixture)",
        out["unsupported"] == [],
        hint=f"got {out['unsupported']!r}",
    )


def test_poetry_pyproject() -> None:
    print("\n== Poetry pyproject.toml ==")
    out = run_detect("poetry-pyproject")
    detected = out["detected"]
    check("detects langchain", "langchain" in detected)
    check("detects openai", "openai" in detected)
    check("detects crewai", "crewai" in detected)
    check(
        "python entry was filtered out",
        "python" not in detected,
        hint=f"detected={detected!r}",
    )
    check(
        "runtime is long_running",
        out["runtime"] == "long_running",
        hint=f"got {out['runtime']!r}",
    )
    check("no serverless signals", out["serverless_signals"] == [])


def test_pep621_pyproject() -> None:
    print("\n== PEP 621 pyproject.toml ==")
    out = run_detect("pep621-pyproject")
    detected = out["detected"]
    check("detects langchain", "langchain" in detected)
    check("detects anthropic", "anthropic" in detected)
    check(
        "detects vertex-ai (via google-cloud-aiplatform)",
        "vertex-ai" in detected,
        hint=f"detected={detected!r}",
    )
    check(
        "runtime is long_running",
        out["runtime"] == "long_running",
        hint=f"got {out['runtime']!r}",
    )


def test_pipfile() -> None:
    print("\n== Pipfile ==")
    out = run_detect("pipfile")
    detected = out["detected"]
    check("detects langchain", "langchain" in detected)
    check("detects openai", "openai" in detected)
    check(
        "runtime is long_running",
        out["runtime"] == "long_running",
        hint=f"got {out['runtime']!r}",
    )


def test_serverless() -> None:
    print("\n== serverless ==")
    out = run_detect("serverless")
    check(
        "runtime is serverless",
        out["runtime"] == "serverless",
        hint=f"got {out['runtime']!r}",
    )
    signals = out["serverless_signals"]
    check(
        "serverless_signals contains serverless.yml",
        "serverless.yml" in signals,
        hint=f"got {signals!r}",
    )
    check(
        "serverless_signals contains lambda_handler",
        "lambda_handler" in signals,
        hint=f"got {signals!r}",
    )
    check("still detects langchain", "langchain" in out["detected"])


def test_existing_setup() -> None:
    print("\n== existing setup ==")
    out = run_detect("existing-setup")
    existing = out["existing_setup"]
    check(
        "existing_setup.found is True",
        existing["found"] is True,
        hint=f"got {existing!r}",
    )
    check(
        "existing_setup.files contains src/tracing.py",
        any(f.replace("\\", "/") == "src/tracing.py" for f in existing["files"]),
        hint=f"got files={existing['files']!r}",
    )
    check("still detects langchain", "langchain" in out["detected"])


def test_no_deps() -> None:
    print("\n== no-deps ==")
    out = run_detect("no-deps")
    check(
        "detected is empty",
        out["detected"] == [],
        hint=f"got {out['detected']!r}",
    )
    check(
        "runtime is unknown",
        out["runtime"] == "unknown",
        hint=f"got {out['runtime']!r}",
    )
    check(
        "existing_setup.found is False",
        out["existing_setup"]["found"] is False,
    )
    check(
        "no serverless signals",
        out["serverless_signals"] == [],
    )
    check(
        "unsupported is empty",
        out["unsupported"] == [],
    )


def test_mixed() -> None:
    print("\n== mixed requirements + pyproject ==")
    out = run_detect("mixed-requirements-pyproject")
    detected = out["detected"]
    check(
        "detects langchain (from pyproject)",
        "langchain" in detected,
        hint=f"detected={detected!r}",
    )
    check(
        "detects openai (from requirements.txt)",
        "openai" in detected,
        hint=f"detected={detected!r}",
    )
    check(
        "runtime is long_running",
        out["runtime"] == "long_running",
        hint=f"got {out['runtime']!r}",
    )


def test_boto3_only() -> None:
    print("\n== boto3-only ==")
    out = run_detect("boto3-only")
    detected = out["detected"]
    check(
        "detects langchain",
        "langchain" in detected,
        hint=f"detected={detected!r}",
    )
    check(
        "bedrock is NOT in detected (boto3 alone is ambiguous)",
        "bedrock" not in detected,
        hint=f"detected={detected!r}",
    )
    unsupported = out["unsupported"]
    check(
        "unsupported has at least one entry",
        len(unsupported) >= 1,
        hint=f"unsupported={unsupported!r}",
    )
    check(
        "unsupported contains bedrock entry",
        "bedrock" in _unsupported_libraries(out),
        hint=f"unsupported={unsupported!r}",
    )
    bedrock_entry = next(
        (e for e in unsupported if isinstance(e, dict) and e.get("library") == "bedrock"),
        None,
    )
    check(
        "bedrock unsupported entry mentions boto3 in matched_dependencies",
        bool(
            bedrock_entry
            and "boto3" in (bedrock_entry.get("matched_dependencies") or [])
        ),
        hint=f"bedrock_entry={bedrock_entry!r}",
    )
    check(
        "bedrock unsupported entry has a reason string",
        bool(
            bedrock_entry
            and isinstance(bedrock_entry.get("reason"), str)
            and bedrock_entry["reason"]
        ),
        hint=f"bedrock_entry={bedrock_entry!r}",
    )


def main() -> None:
    tests = [
        test_requirements_txt,
        test_poetry_pyproject,
        test_pep621_pyproject,
        test_pipfile,
        test_serverless,
        test_existing_setup,
        test_no_deps,
        test_mixed,
        test_boto3_only,
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
