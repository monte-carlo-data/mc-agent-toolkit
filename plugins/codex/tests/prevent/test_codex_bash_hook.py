"""Codex adapter tests for bash_hook: commands that aren't patches.

apply_patch handling is tested in test_codex_apply_patch.py.
"""
import json
import pytest
from unittest.mock import patch
from io import StringIO

from lib.protocol import HookOutput


def _make_stdin(command, cwd="/project"):
    return json.dumps({
        "session_id": "test_session",
        "transcript_path": "/tmp/test_transcript.jsonl",
        "cwd": cwd,
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": command},
        "tool_use_id": "toolu_test123",
    })


class TestBashHookGitCommit:
    def test_context_output_format(self, capsys):
        """git commit should produce additionalContext format."""
        ctx_result = HookOutput(action="context", context="Run validation?")
        with patch("bash_hook.evaluate_pre_commit", return_value=ctx_result), \
             patch("sys.stdin", StringIO(_make_stdin("git commit -m 'test'"))):
            from bash_hook import main
            main()

        output = json.loads(capsys.readouterr().out)
        assert output["hookSpecificOutput"]["hookEventName"] == "PreToolUse"
        assert output["hookSpecificOutput"]["additionalContext"] == "Run validation?"

    def test_noop_silent(self, capsys):
        """Non-commit git command should be silent."""
        noop_result = HookOutput(action="noop")
        with patch("bash_hook.evaluate_pre_commit", return_value=noop_result), \
             patch("sys.stdin", StringIO(_make_stdin("git status"))):
            from bash_hook import main
            main()
        assert capsys.readouterr().out == ""


class TestBashHookOtherCommands:
    def test_pwd_silent(self, capsys):
        """Regular commands should be silent noop."""
        with patch("sys.stdin", StringIO(_make_stdin("pwd"))):
            from bash_hook import main
            main()
        assert capsys.readouterr().out == ""

    def test_ls_silent(self, capsys):
        """ls command should be silent noop."""
        with patch("sys.stdin", StringIO(_make_stdin("ls -la"))):
            from bash_hook import main
            main()
        assert capsys.readouterr().out == ""
