"""Tests for readonly_check.py."""
import json
import subprocess
import sys
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[3]
    / "skills" / "prevent" / "scripts" / "sandbox" / "readonly_check.py"
)


def _run(path: Path) -> tuple[int, dict]:
    out = subprocess.run(
        [sys.executable, str(SCRIPT), str(path)],
        capture_output=True, text=True,
    )
    return out.returncode, json.loads(out.stdout or "{}")


OK_SINGLE_SELECT = "SELECT 1\n"
OK_WITH_CTE = "WITH a AS (SELECT 1) SELECT * FROM a;\n"
OK_SHOW = "SHOW TABLES IN SCHEMA prod;\n"
OK_COMMENT_THEN_SELECT = "-- comment\n/* block */\nSELECT 1;\n"

BAD_INSERT = "INSERT INTO t VALUES (1);\n"
BAD_UPDATE = "-- lead comment\nUPDATE t SET x = 1;\n"
BAD_MERGE = "merge into t using s on s.id = t.id when matched then update set x = 1;"
BAD_CREATE = "CREATE TABLE x (id INT);\n"
BAD_DROP = "DROP TABLE x;\n"
BAD_CALL = "CALL sp_do_thing();\n"
BAD_USE = "USE DATABASE raw;\nSELECT 1;\n"
BAD_MULTI = "SELECT 1;\nSELECT 2;\n"


def test_ok_select(tmp_path):
    f = tmp_path / "q.sql"
    f.write_text(OK_SINGLE_SELECT)
    code, data = _run(f)
    assert code == 0
    assert data == {"ok": True, "rejected": None}


def test_ok_with_cte(tmp_path):
    f = tmp_path / "q.sql"
    f.write_text(OK_WITH_CTE)
    assert _run(f) == (0, {"ok": True, "rejected": None})


def test_ok_show(tmp_path):
    f = tmp_path / "q.sql"
    f.write_text(OK_SHOW)
    assert _run(f) == (0, {"ok": True, "rejected": None})


def test_ok_comment_then_select(tmp_path):
    f = tmp_path / "q.sql"
    f.write_text(OK_COMMENT_THEN_SELECT)
    assert _run(f) == (0, {"ok": True, "rejected": None})


def test_rejects_insert(tmp_path):
    f = tmp_path / "q.sql"
    f.write_text(BAD_INSERT)
    code, data = _run(f)
    assert code == 1
    assert data["ok"] is False
    assert data["rejected"] == "INSERT"


def test_rejects_update(tmp_path):
    f = tmp_path / "q.sql"
    f.write_text(BAD_UPDATE)
    assert _run(f)[1]["rejected"] == "UPDATE"


def test_rejects_merge_lowercase(tmp_path):
    f = tmp_path / "q.sql"
    f.write_text(BAD_MERGE)
    assert _run(f)[1]["rejected"] == "MERGE"


def test_rejects_create(tmp_path):
    f = tmp_path / "q.sql"
    f.write_text(BAD_CREATE)
    assert _run(f)[1]["rejected"] == "CREATE"


def test_rejects_drop(tmp_path):
    f = tmp_path / "q.sql"
    f.write_text(BAD_DROP)
    assert _run(f)[1]["rejected"] == "DROP"


def test_rejects_call(tmp_path):
    f = tmp_path / "q.sql"
    f.write_text(BAD_CALL)
    assert _run(f)[1]["rejected"] == "CALL"


def test_rejects_use(tmp_path):
    f = tmp_path / "q.sql"
    f.write_text(BAD_USE)
    assert _run(f)[1]["rejected"] == "USE"


def test_rejects_multi_statement(tmp_path):
    f = tmp_path / "q.sql"
    f.write_text(BAD_MULTI)
    code, data = _run(f)
    assert code == 1
    assert data["rejected"] == "MULTI_STATEMENT"


def test_rejects_get_stage(tmp_path):
    f = tmp_path / "q.sql"
    f.write_text("GET @stage FILE 'out.csv';\n")
    assert _run(f)[1]["rejected"] == "GET"


def test_rejects_put(tmp_path):
    f = tmp_path / "q.sql"
    f.write_text("PUT file:///tmp/x.csv @stage;\n")
    assert _run(f)[1]["rejected"] == "PUT"


def test_rejects_unload(tmp_path):
    f = tmp_path / "q.sql"
    f.write_text("UNLOAD ('SELECT 1') TO '@stage';\n")
    assert _run(f)[1]["rejected"] == "UNLOAD"


def test_rejects_set_session_var(tmp_path):
    f = tmp_path / "q.sql"
    f.write_text("SET v = 1;\nSELECT 1;\n")
    assert _run(f)[1]["rejected"] == "SET"
