"""Cursor adapter tests for pre_edit_hook — tests JSON format only."""
import json
import pytest
from unittest.mock import patch
from io import StringIO

from lib.protocol import HookOutput


def _make_stdin(file_path):
    return json.dumps({
        "conversation_id": "test_conv",
        "transcript_path": "/tmp/test_transcript.jsonl",
        "cwd": "/project",
        "hook_event_name": "preToolUse",
        "tool_name": "Write",
        "tool_input": {"file_path": file_path},
    })


class TestPreEditHookCursorAdapter:
    def test_deny_output_format(self, capsys):
        """Deny result should produce Cursor-formatted JSON."""
        deny_result = HookOutput(action="deny", reason="blocked for testing")
        with patch("pre_edit_hook.evaluate_pre_edit", return_value=deny_result), \
             patch("sys.stdin", StringIO(_make_stdin("/project/models/orders.sql"))):
            from pre_edit_hook import main
            main()

        output = json.loads(capsys.readouterr().out)
        assert output["permission"] == "deny"
        assert output["user_message"] == "blocked for testing"

    def test_noop_output_silent(self, capsys):
        """Noop result should produce no output."""
        noop_result = HookOutput(action="noop")
        with patch("pre_edit_hook.evaluate_pre_edit", return_value=noop_result), \
             patch("sys.stdin", StringIO(_make_stdin("/project/models/orders.sql"))):
            from pre_edit_hook import main
            main()

        assert capsys.readouterr().out == ""

    def test_conversation_id_used_as_session(self):
        """Cursor adapter should map conversation_id to session_id."""
        raw = json.loads(_make_stdin("/project/models/orders.sql"))
        assert raw["conversation_id"] == "test_conv"
        assert "session_id" not in raw
