import json
import pytest
from unittest.mock import patch
from io import StringIO

import lib.cache as cache


def _make_stdin(session_id="test_session", stop_hook_active=False):
    return json.dumps({
        "session_id": session_id,
        "transcript_path": "/tmp/test_transcript.jsonl",
        "cwd": "/project",
        "hook_event_name": "Stop",
        "stop_hook_active": stop_hook_active,
        "last_assistant_message": "Done editing.",
    })


class TestTurnEndHook:
    def test_no_edits_silent(self, capsys):
        from turn_end_hook import main
        with patch("sys.stdin", StringIO(_make_stdin())):
            main()
        assert capsys.readouterr().out == ""

    def test_edits_without_impact_check_silent(self, capsys):
        """Edits without impact assessment should not prompt."""
        cache.add_edited_table("test_session", "orders")

        from turn_end_hook import main
        with patch("sys.stdin", StringIO(_make_stdin())):
            main()
        assert capsys.readouterr().out == ""

    def test_edits_with_impact_check_prompts(self, capsys):
        """Edits + impact assessment verified should produce validation prompt."""
        cache.add_edited_table("test_session", "orders")
        cache.mark_impact_check_injected("orders")
        cache.mark_impact_check_verified("orders")

        from turn_end_hook import main
        with patch("sys.stdin", StringIO(_make_stdin())):
            main()

        output = capsys.readouterr().out
        parsed = json.loads(output)
        assert parsed["decision"] == "block"
        assert "orders" in parsed["reason"]
        assert "validation" in parsed["reason"].lower()

    def test_stop_hook_active_exits_silently(self, capsys):
        """If stop_hook_active is true, exit silently to prevent infinite loop."""
        cache.add_edited_table("test_session", "orders")
        cache.mark_impact_check_injected("orders")
        cache.mark_impact_check_verified("orders")

        from turn_end_hook import main
        with patch("sys.stdin", StringIO(_make_stdin(stop_hook_active=True))):
            main()

        assert capsys.readouterr().out == ""

    def test_moves_to_pending_validation(self, capsys):
        """After prompting, tables should move to pending validation."""
        cache.add_edited_table("test_session", "orders")
        cache.mark_impact_check_injected("orders")
        cache.mark_impact_check_verified("orders")

        from turn_end_hook import main
        with patch("sys.stdin", StringIO(_make_stdin())):
            main()

        assert cache.get_edited_tables("test_session") == []
        assert "orders" in cache.get_pending_validation_tables("test_session")

    def test_multiple_tables_in_prompt(self, capsys):
        cache.add_edited_table("test_session", "orders")
        cache.add_edited_table("test_session", "customers")
        cache.mark_impact_check_injected("orders")
        cache.mark_impact_check_verified("orders")

        from turn_end_hook import main
        with patch("sys.stdin", StringIO(_make_stdin())):
            main()

        output = capsys.readouterr().out
        parsed = json.loads(output)
        assert "2" in parsed["reason"]  # "2 dbt model(s)"
        assert "orders" in parsed["reason"]
        assert "customers" in parsed["reason"]

    def test_edits_with_only_injected_state_prompts(self, capsys):
        """Edits with 'injected' state should prompt (assessment was triggered)."""
        cache.add_edited_table("test_session", "orders")
        cache.mark_impact_check_injected("orders")

        from turn_end_hook import main
        with patch("sys.stdin", StringIO(_make_stdin())):
            main()

        output = capsys.readouterr().out
        parsed = json.loads(output)
        assert parsed["decision"] == "block"
        assert "orders" in parsed["reason"]
