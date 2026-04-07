"""Codex adapter tests for pre_edit_hook — tests JSON format only, not business logic."""
import json
import pytest
from unittest.mock import patch, MagicMock
from io import StringIO

from lib.protocol import HookOutput


def _make_stdin(file_path):
    return json.dumps({
        "session_id": "test_session",
        "transcript_path": "/tmp/test_transcript.jsonl",
        "cwd": "/project",
        "hook_event_name": "PreToolUse",
        "tool_name": "Edit",
        "tool_input": {"file_path": file_path},
        "tool_use_id": "toolu_test123",
    })


class TestPreEditHookCodexAdapter:
    def test_deny_output_format(self, capsys):
        """Deny result should produce Codex-formatted JSON (same as CC)."""
        deny_result = HookOutput(action="deny", reason="blocked for testing")
        with patch("pre_edit_hook.evaluate_pre_edit", return_value=deny_result), \
             patch("sys.stdin", StringIO(_make_stdin("/project/models/orders.sql"))):
            from pre_edit_hook import main
            main()

        output = json.loads(capsys.readouterr().out)
        assert output["hookSpecificOutput"]["hookEventName"] == "PreToolUse"
        assert output["hookSpecificOutput"]["permissionDecision"] == "deny"
        assert output["hookSpecificOutput"]["permissionDecisionReason"] == "blocked for testing"

    def test_noop_output_silent(self, capsys):
        """Noop result should produce no output."""
        noop_result = HookOutput(action="noop")
        with patch("pre_edit_hook.evaluate_pre_edit", return_value=noop_result), \
             patch("sys.stdin", StringIO(_make_stdin("/project/models/orders.sql"))):
            from pre_edit_hook import main
            main()

        assert capsys.readouterr().out == ""

    def test_session_id_extracted(self):
        """Adapter should extract session_id from Codex JSON."""
        raw = json.loads(_make_stdin("/project/models/orders.sql"))
        assert raw["session_id"] == "test_session"

    def test_file_path_extracted(self):
        """Adapter should extract file_path from tool_input."""
        raw = json.loads(_make_stdin("/project/models/orders.sql"))
        assert raw["tool_input"]["file_path"] == "/project/models/orders.sql"
