"""CC adapter tests for pre_commit_hook — tests JSON format only."""
import json
import pytest
from unittest.mock import patch
from io import StringIO

from lib.protocol import HookOutput


def _make_stdin(command="git commit -m 'test'"):
    return json.dumps({
        "session_id": "test_session",
        "cwd": "/project",
        "tool_input": {"command": command},
    })


class TestPreCommitHookCCAdapter:
    def test_context_output_format(self, capsys):
        """Context result should produce CC additionalContext format."""
        ctx_result = HookOutput(action="context", context="Run validation?")
        with patch("pre_commit_hook.evaluate_pre_commit", return_value=ctx_result), \
             patch("sys.stdin", StringIO(_make_stdin())):
            from pre_commit_hook import main
            main()

        output = json.loads(capsys.readouterr().out)
        assert output["hookSpecificOutput"]["hookEventName"] == "PreToolUse"
        assert output["hookSpecificOutput"]["additionalContext"] == "Run validation?"

    def test_noop_output_silent(self, capsys):
        """Noop result should produce no output."""
        noop_result = HookOutput(action="noop")
        with patch("pre_commit_hook.evaluate_pre_commit", return_value=noop_result), \
             patch("sys.stdin", StringIO(_make_stdin())):
            from pre_commit_hook import main
            main()
        assert capsys.readouterr().out == ""
