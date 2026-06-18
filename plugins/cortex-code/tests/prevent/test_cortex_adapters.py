"""Cortex adapter tests for post_edit, pre_commit, turn_end — JSON I/O format only
(business logic is covered by plugins/shared/prevent/lib/tests)."""
import json
import pytest
from unittest.mock import patch
from io import StringIO

import lib.cache as cache
import lib.protocol as protocol


def _stdin(**kw):
    base = {"session_id": "test_session"}
    base.update(kw)
    return json.dumps(base)


class TestPostEditCortexAdapter:
    def test_tracks_dbt_model(self, tmp_path):
        models = tmp_path / "models"
        models.mkdir()
        sql = models / "orders.sql"
        sql.write_text("SELECT * FROM {{ ref('raw') }}")
        stdin = _stdin(tool_input={"file_path": str(sql)},
                       hook_event_name="PostToolUse", tool_name="write")
        with patch("sys.stdin", StringIO(stdin)):
            from post_edit_hook import main
            main()
        assert cache.get_edited_tables("test_session") == ["orders"]


class TestPreCommitCortexAdapter:
    def test_context_output_format(self, capsys):
        cache.mark_impact_check_verified("test_session", "orders")
        stdin = _stdin(tool_input={"command": "git commit -m x"}, cwd="/project",
                       hook_event_name="PreToolUse", tool_name="bash")
        with patch.object(protocol, "_get_staged_model_tables", return_value=["orders"]), \
             patch("sys.stdin", StringIO(stdin)):
            from pre_commit_hook import main
            main()
        out = json.loads(capsys.readouterr().out)
        assert "additionalContext" in out["hookSpecificOutput"]
        assert "orders" in out["hookSpecificOutput"]["additionalContext"]


class TestTurnEndCortexAdapter:
    def test_block_output_format(self, capsys):
        cache.add_edited_table("test_session", "orders")
        cache.mark_impact_check_verified("test_session", "orders")
        stdin = _stdin(stop_hook_active=False, hook_event_name="Stop")
        with patch("sys.stdin", StringIO(stdin)):
            from turn_end_hook import main
            main()
        out = json.loads(capsys.readouterr().out)
        assert out["decision"] == "block"
        assert "orders" in out["reason"]

    def test_stop_hook_active_is_silent(self, capsys):
        cache.add_edited_table("test_session", "orders")
        cache.mark_impact_check_verified("test_session", "orders")
        stdin = _stdin(stop_hook_active=True, hook_event_name="Stop")
        with patch("sys.stdin", StringIO(stdin)):
            from turn_end_hook import main
            main()
        assert capsys.readouterr().out == ""
