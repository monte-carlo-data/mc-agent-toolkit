"""Tests for substitute_placeholders.py."""
import json
import subprocess
import sys
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[3]
    / "skills" / "prevent" / "scripts" / "sandbox" / "substitute_placeholders.py"
)


def _run(sql_path: Path, dev_db: str) -> tuple[int, dict, str]:
    out = subprocess.run(
        [sys.executable, str(SCRIPT), str(sql_path), "--dev-db", dev_db],
        capture_output=True, text=True,
    )
    return out.returncode, json.loads(out.stdout or "{}"), out.stderr


SAMPLE = """-- Validation queries
SELECT *
FROM <YOUR_DEV_DATABASE>.prod.client_hub;

SELECT 'dev' AS source, COUNT(*) AS rows FROM <YOUR_DEV_DATABASE>.prod.client_hub
UNION ALL
SELECT 'prod' AS source, COUNT(*) AS rows FROM analytics.prod.client_hub;
"""


def test_substitutes_and_reports_literals(tmp_path):
    src = tmp_path / "queries.sql"
    src.write_text(SAMPLE)
    code, data, _ = _run(src, "PERSONAL_ACHEN")
    assert code == 0
    assert data["dev_db"] == "PERSONAL_ACHEN"
    assert data["replaced_count"] == 2
    assert sorted(data["literal_databases"]) == ["analytics"]
    out_path = Path(data["output_path"])
    contents = out_path.read_text()
    assert "<YOUR_DEV_DATABASE>" not in contents
    assert "PERSONAL_ACHEN.prod.client_hub" in contents
    assert "analytics.prod.client_hub" in contents


def test_no_placeholders_present(tmp_path):
    src = tmp_path / "q.sql"
    src.write_text("SELECT * FROM analytics.prod.orders;\n")
    code, data, _ = _run(src, "PERSONAL_ACHEN")
    assert code == 0
    assert data["replaced_count"] == 0
    assert data["literal_databases"] == ["analytics"]


def test_output_dir_is_run_subdir_by_default(tmp_path):
    src = tmp_path / "q.sql"
    src.write_text("SELECT 1 FROM <YOUR_DEV_DATABASE>.prod.t;\n")
    _, data, _ = _run(src, "DEV_X")
    out_path = Path(data["output_path"])
    assert out_path.parent == src.parent / "run"
    assert out_path.parent.exists()
    assert out_path.name == "q.run.sql"


def test_explicit_output_path_respected(tmp_path):
    src = tmp_path / "q.sql"
    src.write_text("SELECT 1 FROM <YOUR_DEV_DATABASE>.prod.t;\n")
    custom = tmp_path / "custom" / "elsewhere.sql"
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(src), "--dev-db", "DEV_X", "--output", str(custom)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    out_path = Path(data["output_path"])
    assert out_path == custom
    assert out_path.exists()


def test_missing_file(tmp_path):
    code, _, err = _run(tmp_path / "nope.sql", "PERSONAL_ACHEN")
    assert code == 1
    assert "not found" in err.lower()
