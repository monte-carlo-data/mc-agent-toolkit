"""Cursor adapter tests for pre_commit_hook — tests JSON format only."""
import json
import pytest
from unittest.mock import patch
from io import StringIO

from lib.protocol import HookOutput


def _make_stdin(command="git commit -m 'test'"):
    return json.dumps({
        "conversation_id": "test_conv",
        "command": command,
        "cwd": "/project",
        "hook_event_name": "beforeShellExecution",
    })


class TestPreCommitHookCursorAdapter:
    def test_context_output_format(self, capsys):
        """Context result should produce Cursor agent_message format."""
        ctx_result = HookOutput(action="context", context="Run validation?")
        with patch("pre_commit_hook.evaluate_pre_commit", return_value=ctx_result), \
             patch("sys.stdin", StringIO(_make_stdin())):
            from pre_commit_hook import main
            main()

        output = json.loads(capsys.readouterr().out)
        assert output["agent_message"] == "Run validation?"

    def test_noop_output_silent(self, capsys):
        """Noop result should produce no output."""
        noop_result = HookOutput(action="noop")
        with patch("pre_commit_hook.evaluate_pre_commit", return_value=noop_result), \
             patch("sys.stdin", StringIO(_make_stdin())):
            from pre_commit_hook import main
            main()
        assert capsys.readouterr().out == ""

    def test_command_at_top_level(self):
        """Cursor beforeShellExecution has command at top level, not in tool_input."""
        raw = json.loads(_make_stdin("git commit -m 'test'"))
        assert raw["command"] == "git commit -m 'test'"
        assert "tool_input" not in raw
