import json
import pytest
from unittest.mock import patch
from io import StringIO

import lib.cache as cache


def _make_stdin(file_path):
    return json.dumps({
        "session_id": "test_session",
        "transcript_path": "/tmp/test_transcript.jsonl",
        "cwd": "/project",
        "hook_event_name": "PostToolUse",
        "tool_name": "Edit",
        "tool_input": {"file_path": file_path},
        "tool_response": {"success": True},
        "tool_use_id": "toolu_test123",
    })


class TestPostEditHook:
    def test_non_dbt_file_no_accumulation(self, capsys):
        from post_edit_hook import main
        with patch("sys.stdin", StringIO(_make_stdin("/project/readme.md"))):
            main()
        assert capsys.readouterr().out == ""
        assert cache.get_edited_tables("test_session") == []

    def test_dbt_model_accumulated(self, tmp_path, capsys):
        model_dir = tmp_path / "models"
        model_dir.mkdir()
        sql_file = model_dir / "orders.sql"
        sql_file.write_text("SELECT * FROM {{ ref('raw') }}")

        from post_edit_hook import main
        with patch("sys.stdin", StringIO(_make_stdin(str(sql_file)))):
            main()

        assert capsys.readouterr().out == ""  # Always silent
        assert cache.get_edited_tables("test_session") == ["orders"]

    def test_multiple_files_accumulated(self, tmp_path, capsys):
        model_dir = tmp_path / "models"
        model_dir.mkdir()
        for name in ["orders.sql", "customers.sql"]:
            f = model_dir / name
            f.write_text("SELECT * FROM {{ ref('x') }}")

        from post_edit_hook import main
        with patch("sys.stdin", StringIO(_make_stdin(str(model_dir / "orders.sql")))):
            main()
        with patch("sys.stdin", StringIO(_make_stdin(str(model_dir / "customers.sql")))):
            main()

        tables = cache.get_edited_tables("test_session")
        assert "orders" in tables
        assert "customers" in tables
