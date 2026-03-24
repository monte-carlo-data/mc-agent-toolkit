import json
import pytest
from unittest.mock import patch
from io import StringIO

import lib.cache as cache


def _make_stdin(session_id="test_session"):
    return json.dumps({
        "session_id": session_id,
        "transcript_path": "/tmp/test_transcript.jsonl",
        "cwd": "/project",
        "hook_event_name": "PreToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": "/mc-validate"},
        "tool_use_id": "toolu_test123",
    })


class TestValidateCommand:
    def test_no_tables_shows_message(self, capsys):
        from validate_command import main
        with patch("sys.stdin", StringIO(_make_stdin())):
            main()
        output = capsys.readouterr().out
        parsed = json.loads(output)
        assert "No dbt model changes" in parsed["hookSpecificOutput"]["additionalContext"]

    def test_pending_tables_with_w4_generates_instruction(self, capsys):
        cache.add_edited_table("test_session", "orders")
        cache.move_to_pending_validation("test_session")
        cache.mark_impact_check_injected("orders")
        cache.mark_impact_check_verified("orders")

        from validate_command import main
        with patch("sys.stdin", StringIO(_make_stdin())):
            main()
        output = capsys.readouterr().out
        parsed = json.loads(output)
        assert "orders" in parsed["hookSpecificOutput"]["additionalContext"]
        assert "Workflow 5" in parsed["hookSpecificOutput"]["additionalContext"]

    def test_current_turn_tables_used_as_fallback(self, capsys):
        cache.add_edited_table("test_session", "customers")

        from validate_command import main
        with patch("sys.stdin", StringIO(_make_stdin())):
            main()
        output = capsys.readouterr().out
        parsed = json.loads(output)
        assert "customers" in parsed["hookSpecificOutput"]["additionalContext"]
