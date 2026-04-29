"""Tests for parse_profiles.py."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "parse_profiles.py"


def _run(profiles_path: Path, profile_name: str | None = None, target_name: str | None = None) -> tuple[int, dict, str]:
    args = [sys.executable, str(SCRIPT), str(profiles_path)]
    if profile_name:
        args += ["--profile", profile_name]
    if target_name:
        args += ["--target", target_name]
    result = subprocess.run(args, capture_output=True, text=True)
    return result.returncode, json.loads(result.stdout or "{}"), result.stderr


SINGLE_TARGET = """
default:
  target: prod
  outputs:
    prod:
      type: snowflake
      account: dka87615.us-east-1
      user: alice@example.com
      role: DATA_ANALYST
      database: personal_alice
      schema: prod
      warehouse: research
      threads: 2
"""

TWO_TARGET = """
default:
  target: dev
  outputs:
    dev:
      type: snowflake
      account: hda34492.us-east-1
      database: prod
      schema: dbt_alice
      role: data_analyst
      warehouse: dev
    local_prod:
      type: snowflake
      account: dka87615.us-east-1
      database: personal_alice
      schema: prod
      role: developer
      warehouse: research
"""


def test_single_target(tmp_path):
    path = tmp_path / "profiles.yml"
    path.write_text(SINGLE_TARGET)
    code, data, _ = _run(path)
    assert code == 0
    assert data == {
        "profile": "default",
        "target_name": "prod",
        "database": "personal_alice",
        "schema": "prod",
        "role": "DATA_ANALYST",
        "warehouse": "research",
        "account": "dka87615.us-east-1",
    }


def test_two_target_default_active(tmp_path):
    path = tmp_path / "profiles.yml"
    path.write_text(TWO_TARGET)
    code, data, _ = _run(path)
    assert code == 0
    assert data["target_name"] == "dev"
    assert data["database"] == "prod"
    assert data["schema"] == "dbt_alice"


def test_explicit_target_override(tmp_path):
    path = tmp_path / "profiles.yml"
    path.write_text(TWO_TARGET)
    code, data, _ = _run(path, target_name="local_prod")
    assert code == 0
    assert data["target_name"] == "local_prod"
    assert data["database"] == "personal_alice"


def test_missing_file(tmp_path):
    code, _, err = _run(tmp_path / "nope.yml")
    assert code == 1
    assert "not found" in err.lower()


def test_unparseable_yaml(tmp_path):
    path = tmp_path / "profiles.yml"
    path.write_text("not: [valid: yaml")
    code, _, err = _run(path)
    assert code == 1
    assert "parse" in err.lower() or "yaml" in err.lower()


def test_target_not_defined(tmp_path):
    path = tmp_path / "profiles.yml"
    path.write_text("default:\n  target: ghost\n  outputs:\n    other:\n      database: foo\n")
    code, _, err = _run(path)
    assert code == 1
    assert "ghost" in err


def test_profile_not_found(tmp_path):
    path = tmp_path / "profiles.yml"
    path.write_text(TWO_TARGET)
    code, _, err = _run(path, profile_name="nonexistent_profile")
    assert code == 1
    assert "nonexistent_profile" in err
    assert "not found" in err.lower()
