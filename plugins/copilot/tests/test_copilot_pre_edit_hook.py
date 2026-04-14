"""Copilot CLI adapter tests for pre_edit_hook — tests JSON format only."""
import json
from unittest.mock import patch
from io import StringIO

from lib.protocol import HookOutput


def _make_stdin(file_path, tool_name="edit"):
    return json.dumps({
        "timestamp": 1704614600000,
        "cwd": "/project",
        "toolName": tool_name,
        "toolArgs": json.dumps({"file_path": file_path}),
    })


class TestPreEditHookCopilotAdapter:
    def test_deny_output_format(self, capsys):
        """Deny result should produce flat permissionDecision JSON."""
        deny_result = HookOutput(action="deny", reason="blocked for testing")
        with patch("pre_edit_hook.evaluate_pre_edit", return_value=deny_result), \
             patch("sys.stdin", StringIO(_make_stdin("/project/models/orders.sql"))):
            from pre_edit_hook import main
            main()

        output = json.loads(capsys.readouterr().out)
        assert output["permissionDecision"] == "deny"
        assert output["permissionDecisionReason"] == "blocked for testing"
        assert "hookSpecificOutput" not in output

    def test_noop_output_silent(self, capsys):
        """Noop result should produce no output."""
        noop_result = HookOutput(action="noop")
        with patch("pre_edit_hook.evaluate_pre_edit", return_value=noop_result), \
             patch("sys.stdin", StringIO(_make_stdin("/project/models/orders.sql"))):
            from pre_edit_hook import main
            main()

        assert capsys.readouterr().out == ""

    def test_non_edit_tool_skipped(self, capsys):
        """Non-edit tools (e.g., view) should exit silently."""
        with patch("sys.stdin", StringIO(_make_stdin("/project/models/orders.sql", tool_name="view"))):
            from pre_edit_hook import main
            # Should exit(0) without calling evaluate_pre_edit
        assert capsys.readouterr().out == ""

    def test_tool_args_is_json_string(self):
        """Copilot CLI sends toolArgs as a JSON string, not an object."""
        raw = json.loads(_make_stdin("/project/models/orders.sql"))
        assert isinstance(raw["toolArgs"], str)
        parsed = json.loads(raw["toolArgs"])
        assert parsed["file_path"] == "/project/models/orders.sql"
