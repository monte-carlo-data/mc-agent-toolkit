"""Copilot CLI adapter tests for pre_commit_hook — tests JSON format only."""
import json
from unittest.mock import patch
from io import StringIO

from lib.protocol import HookOutput


def _make_stdin(command="git commit -m 'test'", tool_name="bash"):
    return json.dumps({
        "timestamp": 1704614600000,
        "cwd": "/project",
        "toolName": tool_name,
        "toolArgs": json.dumps({"command": command}),
    })


class TestPreCommitHookCopilotAdapter:
    def test_context_becomes_deny(self, capsys):
        """Context result should produce permissionDecision deny (no additionalContext in Copilot CLI)."""
        ctx_result = HookOutput(action="context", context="Run validation?")
        with patch("pre_commit_hook.evaluate_pre_commit", return_value=ctx_result), \
             patch("sys.stdin", StringIO(_make_stdin())):
            from pre_commit_hook import main
            main()

        output = json.loads(capsys.readouterr().out)
        assert output["permissionDecision"] == "deny"
        assert output["permissionDecisionReason"] == "Run validation?"

    def test_noop_output_silent(self, capsys):
        """Noop result should produce no output."""
        noop_result = HookOutput(action="noop")
        with patch("pre_commit_hook.evaluate_pre_commit", return_value=noop_result), \
             patch("sys.stdin", StringIO(_make_stdin())):
            from pre_commit_hook import main
            main()
        assert capsys.readouterr().out == ""

    def test_non_bash_tool_skipped(self, capsys):
        """Non-bash tools should exit silently."""
        with patch("sys.stdin", StringIO(_make_stdin(tool_name="edit"))):
            from pre_commit_hook import main
        assert capsys.readouterr().out == ""

    def test_command_in_tool_args(self):
        """Copilot CLI sends command inside toolArgs JSON string."""
        raw = json.loads(_make_stdin("git commit -m 'test'"))
        tool_args = json.loads(raw["toolArgs"])
        assert tool_args["command"] == "git commit -m 'test'"
