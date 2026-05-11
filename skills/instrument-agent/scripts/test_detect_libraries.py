#!/usr/bin/env python3
"""
Smoke test for detect_libraries.py — runs it against each fixture in
test_fixtures/ and asserts the JSON output is correct.

Run:
    python3 skills/instrument-agent/scripts/test_detect_libraries.py
"""

from __future__ import annotations

import json
import re
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


def _suggested_packages(out: dict) -> list[str]:
    return [
        entry.get("package")
        for entry in out.get("suggested_instrumentors", [])
        if isinstance(entry, dict)
    ]


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
        "detects vertexai (via google-cloud-aiplatform)",
        "vertexai" in detected,
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


def test_sample_agent() -> None:
    """Phase 3 structural smoke — long-running LangGraph fixture.

    Validates that detect_libraries produces JSON the workflow's step #1 can
    consume to drive the rest of the flow toward the long-running mc.setup()
    template path.
    """
    print("\n== sample_agent (Phase 3 smoke, long-running) ==")
    out = run_detect("sample_agent")
    detected = out["detected"]
    check("detects langchain", "langchain" in detected)
    check("detects langgraph", "langgraph" in detected)
    check("detects openai", "openai" in detected)
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
    # langchain and langgraph share opentelemetry-instrumentation-langchain,
    # so suggested_instrumentors dedupes by package — only one of the two
    # appears, plus openai. Both libraries still appear in `detected`.
    suggested_libs = _suggested_libraries(out)
    check(
        "suggested_instrumentors includes langchain or langgraph (shared package)",
        bool(suggested_libs & {"langchain", "langgraph"}),
        hint=f"got {suggested_libs}",
    )
    check(
        "suggested_instrumentors includes openai",
        "openai" in suggested_libs,
        hint=f"got {suggested_libs}",
    )
    suggested_packages = _suggested_packages(out)
    check(
        "suggested_instrumentors has no duplicate packages",
        len(suggested_packages) == len(set(suggested_packages)),
        hint=f"got {suggested_packages}",
    )
    check(
        "shared langchain instrumentor appears exactly once",
        suggested_packages.count("opentelemetry-instrumentation-langchain") == 1,
        hint=f"got {suggested_packages}",
    )


def test_sample_serverless_agent() -> None:
    """Phase 3 structural smoke — Lambda-shaped LangGraph fixture.

    Validates that detect_libraries flips runtime to "serverless" and
    surfaces the framework signals the workflow needs to route toward the
    SimpleSpanProcessor mc.setup() variant.
    """
    print("\n== sample_serverless_agent (Phase 3 smoke, serverless) ==")
    out = run_detect("sample_serverless_agent")
    detected = out["detected"]
    check("detects langchain", "langchain" in detected)
    check("detects langgraph", "langgraph" in detected)
    check("detects openai", "openai" in detected)
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


# Libraries the static detection map (`instrumentor_map.json`) must cover so
# `detect_libraries.py` can recognize them in customer dependency files without
# a network call. The SDK's actual supported set is whatever PyPI shows; this
# list is the offline detection baseline.
_BASELINE_DETECTION_LIBRARIES = {
    "langchain",
    "langgraph",
    "openai",
    "anthropic",
    "crewai",
    "bedrock",
    "sagemaker",
    "vertexai",
}

_LIBRARY_NAME_RE = re.compile(r"^[a-z][a-z0-9_-]*$")


def test_instrumentor_map_schema() -> None:
    """Validate the committed instrumentor_map.json against its canonical schema."""
    print("\n== instrumentor_map.json schema validation ==")
    map_path = SCRIPT_DIR / "instrumentor_map.json"
    check(
        "instrumentor_map.json exists",
        map_path.is_file(),
        hint=f"expected at {map_path}",
    )
    with map_path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)

    # supported_instrumentors — non-empty list.
    entries = data.get("supported_instrumentors")
    check(
        "supported_instrumentors is a non-empty list",
        isinstance(entries, list) and len(entries) > 0,
        hint=f"got {type(entries).__name__} with length {len(entries) if isinstance(entries, list) else 'n/a'}",
    )

    # Per-entry field shapes.
    required_fields = {"library": str, "package": str, "version_constraint": str}
    for i, entry in enumerate(entries or []):
        for field, expected_type in required_fields.items():
            check(
                f"entry[{i}] has {field!r} ({expected_type.__name__})",
                isinstance(entry, dict) and isinstance(entry.get(field), expected_type),
                hint=f"entry={entry!r}",
            )
        covers = entry.get("covers_dependencies") if isinstance(entry, dict) else None
        check(
            f"entry[{i}] has covers_dependencies (list)",
            isinstance(covers, list),
            hint=f"covers_dependencies={covers!r}",
        )

    # library naming convention — lowercase, no special chars beyond _-.
    libraries = [e.get("library") for e in (entries or []) if isinstance(e, dict)]
    for lib in libraries:
        if lib is None:
            continue
        check(
            f"library {lib!r} matches naming convention (lowercase, [a-z0-9_-])",
            bool(_LIBRARY_NAME_RE.match(lib)),
            hint=f"got {lib!r}",
        )

    # library uniqueness.
    seen: set[str] = set()
    duplicates: list[str] = []
    for lib in libraries:
        if lib is None:
            continue
        if lib in seen:
            duplicates.append(lib)
        seen.add(lib)
    check(
        "library values are unique (no duplicates)",
        len(duplicates) == 0,
        hint=f"duplicates={duplicates!r}",
    )

    library_set = set(lib for lib in libraries if lib is not None)
    missing_baseline = _BASELINE_DETECTION_LIBRARIES - library_set
    check(
        "all baseline detection libraries are present in the static map",
        len(missing_baseline) == 0,
        hint=f"missing={sorted(missing_baseline)!r}",
    )

    # Every package follows the opentelemetry-instrumentation- prefix.
    packages = [e.get("package") for e in (entries or []) if isinstance(e, dict)]
    bad_packages = [
        p for p in packages if isinstance(p, str) and not p.startswith("opentelemetry-instrumentation-")
    ]
    check(
        "all packages start with 'opentelemetry-instrumentation-'",
        len(bad_packages) == 0,
        hint=f"non-conforming packages={bad_packages!r}",
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
        test_instrumentor_map_schema,
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
