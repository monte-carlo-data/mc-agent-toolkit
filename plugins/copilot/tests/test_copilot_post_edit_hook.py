"""Copilot CLI adapter tests for post_edit_hook — tests JSON format only."""
import json
from unittest.mock import patch
from io import StringIO

from lib.protocol import HookOutput


def _make_stdin(file_path, tool_name="edit"):
    return json.dumps({
        "timestamp": 1704614700000,
        "cwd": "/project",
        "toolName": tool_name,
        "toolArgs": json.dumps({"file_path": file_path}),
    })


class TestPostEditHookCopilotAdapter:
    def test_silent_output(self, capsys):
        """Post-edit hook should always produce no output."""
        noop_result = HookOutput(action="noop")
        with patch("post_edit_hook.evaluate_post_edit", return_value=noop_result), \
             patch("sys.stdin", StringIO(_make_stdin("/project/models/orders.sql"))):
            from post_edit_hook import main
            main()
        assert capsys.readouterr().out == ""

    def test_non_edit_tool_skipped(self, capsys):
        """Non-edit tools should exit silently."""
        with patch("sys.stdin", StringIO(_make_stdin("/project/models/orders.sql", tool_name="bash"))):
            from post_edit_hook import main
        assert capsys.readouterr().out == ""
