"""Tests for classify_sandbox.py."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = (
    Path(__file__).resolve().parents[3]
    / "skills" / "prevent" / "scripts" / "sandbox" / "classify_sandbox.py"
)


def _run(name: str) -> dict:
    result = subprocess.run(
        [sys.executable, str(SCRIPT), name],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


@pytest.mark.parametrize("name,expected", [
    ("PERSONAL_ACHEN", "personal"),
    ("personal_alice", "personal"),
    ("DEV_PLATFORM", "dev"),
    ("SANDBOX_42", "dev"),
    ("MY_DEV", "dev"),
    ("DBT_ACHEN", "shared-dev"),
    ("ANALYTICS", "prod"),
    ("RAW", "prod"),
    ("INGEST", "prod"),
    ("MONTECARLODATA_SHARED", "prod"),
    ("FOO_BAR", "unknown"),
    ("", "unknown"),
])
def test_classify(name, expected):
    assert _run(name) == {"database": name, "classification": expected}


def test_classify_importable():
    """Function form works for direct calls from other scripts."""
    from classify_sandbox import classify
    assert classify("PERSONAL_ACHEN") == "personal"
    assert classify("ANALYTICS") == "prod"
