#!/usr/bin/env python3
"""
Smoke test for detect_libraries.py — runs it against each fixture in
fixtures/ and asserts the JSON output is correct.

The script's contract is "raw discovery surface": dependencies (sorted list
of normalized pip package names), runtime classification, serverless
signals, and existing-`mc.setup()` detection. AI-library disambiguation
is the LLM's job and is not exercised here.

Run:
    python3 skills/instrument-agent/tests/test_detect_libraries.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

TESTS_DIR = Path(__file__).parent
SKILL_ROOT = TESTS_DIR.parent
DETECT_SCRIPT = SKILL_ROOT / "scripts" / "detect_libraries.py"
FIXTURES_DIR = TESTS_DIR / "fixtures"

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


def test_requirements_txt() -> None:
    print("\n== requirements.txt ==")
    out = run_detect("requirements")
    deps = out["dependencies"]
    check("dependencies includes langchain", "langchain" in deps)
    check("dependencies includes openai", "openai" in deps)
    check("dependencies includes anthropic", "anthropic" in deps)
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
        "dependencies sorted",
        deps == sorted(deps),
        hint=f"dependencies={deps!r}",
    )


def test_poetry_pyproject() -> None:
    print("\n== Poetry pyproject.toml ==")
    out = run_detect("poetry-pyproject")
    deps = out["dependencies"]
    check("dependencies includes langchain", "langchain" in deps)
    check("dependencies includes openai", "openai" in deps)
    check("dependencies includes crewai", "crewai" in deps)
    check(
        "python entry was filtered out",
        "python" not in deps,
        hint=f"dependencies={deps!r}",
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
    deps = out["dependencies"]
    check("dependencies includes langchain", "langchain" in deps)
    check("dependencies includes anthropic", "anthropic" in deps)
    check(
        "dependencies includes google-cloud-aiplatform (Vertex AI surface)",
        "google-cloud-aiplatform" in deps,
        hint=f"dependencies={deps!r}",
    )
    check(
        "runtime is long_running",
        out["runtime"] == "long_running",
        hint=f"got {out['runtime']!r}",
    )


def test_pipfile() -> None:
    print("\n== Pipfile ==")
    out = run_detect("pipfile")
    deps = out["dependencies"]
    check("dependencies includes langchain", "langchain" in deps)
    check("dependencies includes openai", "openai" in deps)
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
    check(
        "dependencies still includes langchain",
        "langchain" in out["dependencies"],
    )


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
    check(
        "existing_setup.files contains aliased module setup call",
        any(
            f.replace("\\", "/") == "src/tracing_alias.py"
            for f in existing["files"]
        ),
        hint=f"got files={existing['files']!r}",
    )
    check(
        "existing_setup.files contains direct imported setup call",
        any(
            f.replace("\\", "/") == "src/tracing_direct.py"
            for f in existing["files"]
        ),
        hint=f"got files={existing['files']!r}",
    )
    check(
        "dependencies still includes langchain",
        "langchain" in out["dependencies"],
    )


def test_no_deps() -> None:
    print("\n== no-deps ==")
    out = run_detect("no-deps")
    check(
        "dependencies is empty",
        out["dependencies"] == [],
        hint=f"got {out['dependencies']!r}",
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


def test_mixed() -> None:
    print("\n== mixed requirements + pyproject ==")
    out = run_detect("mixed-requirements-pyproject")
    deps = out["dependencies"]
    check(
        "dependencies includes langchain (from pyproject)",
        "langchain" in deps,
        hint=f"dependencies={deps!r}",
    )
    check(
        "dependencies includes openai (from requirements.txt)",
        "openai" in deps,
        hint=f"dependencies={deps!r}",
    )
    check(
        "runtime is long_running",
        out["runtime"] == "long_running",
        hint=f"got {out['runtime']!r}",
    )


def test_boto3_only() -> None:
    """boto3 lands in dependencies like any other package.

    Disambiguation (is this Bedrock, SageMaker, or just S3?) is the LLM's
    job — it sees boto3 in the deps list and asks the user. The script
    itself doesn't single boto3 out; this test pins that contract.
    """
    print("\n== boto3-only ==")
    out = run_detect("boto3-only")
    deps = out["dependencies"]
    check(
        "dependencies includes langchain",
        "langchain" in deps,
        hint=f"dependencies={deps!r}",
    )
    check(
        "dependencies includes boto3 (raw, no special handling)",
        "boto3" in deps,
        hint=f"dependencies={deps!r}",
    )
    check(
        "runtime is long_running",
        out["runtime"] == "long_running",
        hint=f"got {out['runtime']!r}",
    )


def test_sample_agent() -> None:
    """Phase 3 structural smoke — long-running LangGraph fixture.

    Validates that detect_libraries produces JSON the workflow's step #1 can
    consume to drive the rest of the flow toward the long-running mc.setup()
    template path.
    """
    print("\n== sample_agent (Phase 3 smoke, long-running) ==")
    out = run_detect("sample_agent")
    deps = out["dependencies"]
    check("dependencies includes langchain", "langchain" in deps)
    check("dependencies includes langgraph", "langgraph" in deps)
    check("dependencies includes openai", "openai" in deps)
    check(
        "runtime is long_running",
        out["runtime"] == "long_running",
        hint=f"got {out['runtime']!r}",
    )
    check(
        "no serverless signals",
        out["serverless_signals"] == [],
        hint=f"got {out['serverless_signals']!r}",
    )
    check(
        "no false-positive existing setup",
        out["existing_setup"]["found"] is False,
        hint=f"existing_setup={out['existing_setup']!r}",
    )


def test_sample_serverless_agent() -> None:
    """Phase 3 structural smoke — Lambda-shaped LangGraph fixture.

    Validates that detect_libraries flips runtime to "serverless" and
    surfaces the framework signals the workflow needs to route toward the
    SimpleSpanProcessor mc.setup() variant.
    """
    print("\n== sample_serverless_agent (Phase 3 smoke, serverless) ==")
    out = run_detect("sample_serverless_agent")
    deps = out["dependencies"]
    check("dependencies includes langchain", "langchain" in deps)
    check("dependencies includes langgraph", "langgraph" in deps)
    check("dependencies includes openai", "openai" in deps)
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
    check(
        "serverless_signals contains aws-lambda-powertools",
        "aws-lambda-powertools" in signals,
        hint=f"got {signals!r}",
    )
    check(
        "no false-positive existing setup",
        out["existing_setup"]["found"] is False,
        hint=f"existing_setup={out['existing_setup']!r}",
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
        test_sample_agent,
        test_sample_serverless_agent,
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
