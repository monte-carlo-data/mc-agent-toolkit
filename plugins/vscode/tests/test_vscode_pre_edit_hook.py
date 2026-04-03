"""VS Code adapter tests for pre_edit_hook — tests JSON format only."""
import json
from unittest.mock import patch
from io import StringIO

from lib.protocol import HookOutput


def _make_stdin(file_path):
    return json.dumps({
        "sessionId": "test_session",
        "transcript_path": "/tmp/test_transcript.jsonl",
        "cwd": "/project",
        "hookEventName": "PreToolUse",
        "tool_name": "editFiles",
        "tool_input": {"filePath": file_path},
    })


class TestPreEditHookVSCodeAdapter:
    def test_deny_output_format(self, capsys):
        """Deny result should produce hookSpecificOutput JSON (same as Claude Code)."""
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

    def test_session_id_from_camel_case(self):
        """VS Code adapter should map sessionId (camelCase) to session_id."""
        raw = json.loads(_make_stdin("/project/models/orders.sql"))
        assert raw["sessionId"] == "test_session"
        assert "session_id" not in raw

    def test_file_path_from_camel_case(self):
        """VS Code adapter should read filePath (camelCase) from tool_input."""
        raw = json.loads(_make_stdin("/project/models/orders.sql"))
        assert raw["tool_input"]["filePath"] == "/project/models/orders.sql"
        assert "file_path" not in raw["tool_input"]
