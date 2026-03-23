import json
import pytest
from unittest.mock import patch
from io import StringIO

import lib.cache as cache


def _make_stdin(command="git commit -m 'test'", session_id="test_session"):
    return json.dumps({
        "session_id": session_id,
        "transcript_path": "/tmp/test_transcript.jsonl",
        "cwd": "/project",
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": command},
        "tool_use_id": "toolu_test123",
    })


class TestPreCommitHook:
    def test_non_commit_command_silent(self, capsys):
        from pre_commit_hook import main
        with patch("sys.stdin", StringIO(_make_stdin("ls -la"))):
            main()
        assert capsys.readouterr().out == ""

    def test_commit_no_staged_sql_silent(self, capsys):
        """git commit with no staged .sql models should be silent."""
        from pre_commit_hook import main
        with patch("sys.stdin", StringIO(_make_stdin())), \
             patch("pre_commit_hook._get_staged_model_tables") as mock_staged:
            mock_staged.return_value = []
            main()
        assert capsys.readouterr().out == ""

    def test_commit_with_staged_sql_and_w4_prompts(self, capsys):
        """git commit with staged dbt models + W4 should prompt."""
        cache.mark_workflow4_injected("orders")
        cache.mark_workflow4_verified("orders")

        from pre_commit_hook import main
        with patch("sys.stdin", StringIO(_make_stdin())), \
             patch("pre_commit_hook._get_staged_model_tables") as mock_staged:
            mock_staged.return_value = ["orders"]
            main()

        output = capsys.readouterr().out
        parsed = json.loads(output)
        assert "orders" in parsed["hookSpecificOutput"]["additionalContext"]
        assert "validation" in parsed["hookSpecificOutput"]["additionalContext"].lower()

    def test_commit_staged_sql_without_w4_silent(self, capsys):
        """git commit with staged dbt models but no W4 should be silent."""
        from pre_commit_hook import main
        with patch("sys.stdin", StringIO(_make_stdin())), \
             patch("pre_commit_hook._get_staged_model_tables") as mock_staged:
            mock_staged.return_value = ["orders"]
            main()
        assert capsys.readouterr().out == ""

    def test_git_commit_amend_also_caught(self, capsys):
        """git commit --amend should also trigger."""
        cache.mark_workflow4_injected("orders")
        cache.mark_workflow4_verified("orders")

        from pre_commit_hook import main
        with patch("sys.stdin", StringIO(_make_stdin("git commit --amend"))), \
             patch("pre_commit_hook._get_staged_model_tables") as mock_staged:
            mock_staged.return_value = ["orders"]
            main()

        output = capsys.readouterr().out
        assert output != ""  # Should produce output
