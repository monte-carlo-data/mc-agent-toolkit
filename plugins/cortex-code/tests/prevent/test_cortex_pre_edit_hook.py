"""Cortex adapter tests for pre_edit_hook — JSON I/O plus the `.history.jsonl` sibling
rewrite and the assistant-text-only marker behavior, exercised through the adapter."""
import json
import pytest
from unittest.mock import patch
from io import StringIO

from lib.protocol import HookOutput
import lib.cache as cache


def _stdin(file_path, transcript_path):
    return json.dumps({
        "session_id": "test_session",
        "transcript_path": transcript_path,
        "cwd": "/project",
        "hook_event_name": "PreToolUse",
        "tool_name": "write",
        "tool_input": {"file_path": file_path},
        "tool_use_id": "toolu_test",
    })


class TestHistoryPath:
    def test_json_mapped_to_history_jsonl(self):
        from pre_edit_hook import _history_path
        assert _history_path("/c/sess.json") == "/c/sess.history.jsonl"

    def test_non_json_passthrough(self):
        from pre_edit_hook import _history_path
        assert _history_path("/c/sess.jsonl") == "/c/sess.jsonl"

    def test_empty_passthrough(self):
        from pre_edit_hook import _history_path
        assert _history_path("") == ""


class TestPreEditCortexAdapter:
    def test_passes_history_sibling_and_format(self):
        """Adapter must rewrite transcript_path to the .history.jsonl sibling and
        flag the Messages-style format for the shared scanner."""
        captured = {}

        def fake_eval(inp):
            captured["transcript_path"] = inp.transcript_path
            captured["transcript_format"] = inp.transcript_format
            return HookOutput(action="noop")

        with patch("pre_edit_hook.evaluate_pre_edit", side_effect=fake_eval), \
             patch("sys.stdin", StringIO(_stdin("/p/models/orders.sql", "/c/sess.json"))):
            from pre_edit_hook import main
            main()

        assert captured["transcript_path"] == "/c/sess.history.jsonl"
        assert captured["transcript_format"] == "messages_jsonl"

    def test_deny_output_format(self, capsys):
        with patch("pre_edit_hook.evaluate_pre_edit", return_value=HookOutput(action="deny", reason="blocked")), \
             patch("sys.stdin", StringIO(_stdin("/p/models/orders.sql", "/c/sess.json"))):
            from pre_edit_hook import main
            main()
        out = json.loads(capsys.readouterr().out)
        assert out["hookSpecificOutput"]["hookEventName"] == "PreToolUse"
        assert out["hookSpecificOutput"]["permissionDecision"] == "deny"
        assert out["hookSpecificOutput"]["permissionDecisionReason"] == "blocked"

    def test_noop_output_silent(self, capsys):
        with patch("pre_edit_hook.evaluate_pre_edit", return_value=HookOutput(action="noop")), \
             patch("sys.stdin", StringIO(_stdin("/p/models/orders.sql", "/c/sess.json"))):
            from pre_edit_hook import main
            main()
        assert capsys.readouterr().out == ""


class TestPreEditCortexIntegration:
    """End-to-end through the adapter (real protocol/cache, no logic patching):
    the genuine marker in assistant text unlocks; the same marker echoed in a
    tool_result (how Cortex persists the deny reason) does NOT."""

    def _model(self, tmp_path):
        models = tmp_path / "models"
        models.mkdir()
        sql = models / "orders.sql"
        sql.write_text("SELECT * FROM {{ ref('raw') }}")
        return str(sql)

    def _meta_with_history(self, tmp_path, message):
        meta = tmp_path / "sess.json"
        meta.write_text('{"session_id": "test_session"}')
        hist = tmp_path / "sess.history.jsonl"
        hist.write_text(json.dumps(message) + "\n")
        return str(meta)

    def test_marker_in_assistant_text_allows(self, tmp_path, capsys):
        sql = self._model(tmp_path)
        meta = self._meta_with_history(tmp_path, {
            "role": "assistant",
            "content": [{"type": "text", "text": "Done. <!-- MC_IMPACT_CHECK_COMPLETE: orders -->"}],
        })
        with patch("sys.stdin", StringIO(_stdin(sql, meta))):
            from pre_edit_hook import main
            main()
        assert capsys.readouterr().out == ""  # verified -> noop -> no deny
        assert cache.get_impact_check_state("test_session", "orders") == "verified"

    def test_marker_only_in_tool_result_denies(self, tmp_path, capsys):
        sql = self._model(tmp_path)
        meta = self._meta_with_history(tmp_path, {
            "role": "user",
            "content": [{"type": "tool_result", "tool_result": {"content": [
                {"type": "text", "text": "[Hook] ... MC_IMPACT_CHECK_COMPLETE: orders ..."}]}}],
        })
        with patch("sys.stdin", StringIO(_stdin(sql, meta))):
            from pre_edit_hook import main
            main()
        out = json.loads(capsys.readouterr().out)
        assert out["hookSpecificOutput"]["permissionDecision"] == "deny"
