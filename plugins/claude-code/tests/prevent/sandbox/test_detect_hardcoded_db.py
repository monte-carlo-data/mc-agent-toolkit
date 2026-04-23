"""Tests for detect_hardcoded_db.py."""
import json
import subprocess
import sys
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[3]
    / "skills" / "prevent" / "scripts" / "sandbox" / "detect_hardcoded_db.py"
)


def _run(path: Path) -> dict:
    out = subprocess.run(
        [sys.executable, str(SCRIPT), str(path)],
        capture_output=True, text=True, check=True,
    )
    return json.loads(out.stdout)


def test_no_hardcoded_db(tmp_path):
    f = tmp_path / "m.sql"
    f.write_text("{{ config(materialized='table', schema='prod') }}\nSELECT 1\n")
    assert _run(f) == {"database": None}


def test_hardcoded_db_single_quotes(tmp_path):
    f = tmp_path / "m.sql"
    f.write_text("{{ config(materialized='table', database='MONTECARLODATA_SHARED', schema='exports') }}\nSELECT 1\n")
    assert _run(f) == {"database": "MONTECARLODATA_SHARED"}


def test_hardcoded_db_double_quotes(tmp_path):
    f = tmp_path / "m.sql"
    f.write_text('{{ config(database="shared") }}\n')
    assert _run(f) == {"database": "shared"}


def test_no_config_block(tmp_path):
    f = tmp_path / "m.sql"
    f.write_text("SELECT 1\n")
    assert _run(f) == {"database": None}


def test_config_spread_across_lines(tmp_path):
    f = tmp_path / "m.sql"
    f.write_text(
        "{{ config(\n"
        "    materialized='incremental',\n"
        "    database='EXPORTS_DB',\n"
        "    unique_key='id'\n"
        ") }}\n"
        "SELECT 1\n"
    )
    assert _run(f) == {"database": "EXPORTS_DB"}


def test_missing_file(tmp_path):
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(tmp_path / "nope.sql")],
        capture_output=True, text=True,
    )
    assert result.returncode == 1
