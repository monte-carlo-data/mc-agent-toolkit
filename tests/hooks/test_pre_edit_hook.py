import os
import json
import pytest
from unittest.mock import patch
from io import StringIO

import lib.cache as cache


def _make_stdin(file_path, tool_name="Edit", transcript_path="/tmp/test_transcript.jsonl"):
    """Build a mock stdin JSON payload for PreToolUse."""
    return json.dumps({
        "session_id": "test_session",
        "transcript_path": transcript_path,
        "cwd": "/project",
        "hook_event_name": "PreToolUse",
        "tool_name": tool_name,
        "tool_input": {"file_path": file_path},
        "tool_use_id": "toolu_test123",
    })


class TestPreEditHook:
    def test_non_dbt_file_exits_silently(self, capsys):
        """Non-dbt files should produce no output."""
        from pre_edit_hook import main
        with patch("sys.stdin", StringIO(_make_stdin("/project/scripts/hello.py"))):
            main()
        assert capsys.readouterr().out == ""

    def test_dbt_model_first_edit_injects(self, tmp_path, capsys):
        """First edit to a dbt model should inject Workflow 4 instruction."""
        model_dir = tmp_path / "models"
        model_dir.mkdir()
        sql_file = model_dir / "orders.sql"
        sql_file.write_text("SELECT * FROM {{ ref('raw') }}")

        from pre_edit_hook import main
        with patch("sys.stdin", StringIO(_make_stdin(str(sql_file)))):
            main()

        output = capsys.readouterr().out
        parsed = json.loads(output)
        assert "MANDATORY" in parsed["hookSpecificOutput"]["additionalContext"]
        assert "orders" in parsed["hookSpecificOutput"]["additionalContext"]

    def test_dbt_model_second_edit_within_120s_silent(self, tmp_path, capsys):
        """Second edit within 120s should be silent (injected state, still fresh)."""
        model_dir = tmp_path / "models"
        model_dir.mkdir()
        sql_file = model_dir / "orders.sql"
        sql_file.write_text("SELECT * FROM {{ ref('raw') }}")

        cache.mark_workflow4_injected("orders")

        from pre_edit_hook import main
        with patch("sys.stdin", StringIO(_make_stdin(str(sql_file)))):
            main()

        assert capsys.readouterr().out == ""

    def test_dbt_model_verified_state_silent(self, tmp_path, capsys):
        """Verified state should always be silent."""
        model_dir = tmp_path / "models"
        model_dir.mkdir()
        sql_file = model_dir / "orders.sql"
        sql_file.write_text("SELECT * FROM {{ ref('raw') }}")

        cache.mark_workflow4_injected("orders")
        cache.mark_workflow4_verified("orders")

        from pre_edit_hook import main
        with patch("sys.stdin", StringIO(_make_stdin(str(sql_file)))):
            main()

        assert capsys.readouterr().out == ""

    def test_grace_period_expired_marker_in_transcript_verifies(self, tmp_path, capsys):
        """After 120s, if transcript has marker, should verify and go silent."""
        model_dir = tmp_path / "models"
        model_dir.mkdir()
        sql_file = model_dir / "orders.sql"
        sql_file.write_text("SELECT * FROM {{ ref('raw') }}")

        cache.mark_workflow4_injected("orders")

        # Create transcript with the completion marker
        transcript = tmp_path / "transcript.jsonl"
        transcript.write_text('{"content": "<!-- MC_WORKFLOW4_COMPLETE: orders -->"}\n')

        # Age the marker past grace period
        marker_path = "/tmp/mc_safe_change_w4_orders"
        with open(marker_path, "r") as f:
            data = json.load(f)
        data["timestamp"] = data["timestamp"] - 200  # 200 seconds ago
        with open(marker_path, "w") as f:
            json.dump(data, f)

        from pre_edit_hook import main
        with patch("sys.stdin", StringIO(_make_stdin(str(sql_file), transcript_path=str(transcript)))):
            main()

        assert capsys.readouterr().out == ""
        assert cache.get_workflow4_state("orders") == "verified"

    def test_grace_period_expired_no_marker_in_transcript_reinjects(self, tmp_path, capsys):
        """After 120s, if transcript lacks marker, should re-inject."""
        model_dir = tmp_path / "models"
        model_dir.mkdir()
        sql_file = model_dir / "orders.sql"
        sql_file.write_text("SELECT * FROM {{ ref('raw') }}")

        cache.mark_workflow4_injected("orders")

        # Create transcript WITHOUT the completion marker
        transcript = tmp_path / "transcript.jsonl"
        transcript.write_text('{"content": "some other message"}\n')

        # Age the marker past grace period
        marker_path = "/tmp/mc_safe_change_w4_orders"
        with open(marker_path, "r") as f:
            data = json.load(f)
        data["timestamp"] = data["timestamp"] - 200
        with open(marker_path, "w") as f:
            json.dump(data, f)

        from pre_edit_hook import main
        with patch("sys.stdin", StringIO(_make_stdin(str(sql_file), transcript_path=str(transcript)))):
            main()

        output = capsys.readouterr().out
        parsed = json.loads(output)
        assert "MANDATORY" in parsed["hookSpecificOutput"]["additionalContext"]


class TestScanTranscript:
    def test_marker_found(self, tmp_path):
        from pre_edit_hook import _scan_transcript_for_marker
        transcript = tmp_path / "transcript.jsonl"
        transcript.write_text('line1\n<!-- MC_WORKFLOW4_COMPLETE: orders -->\nline3\n')
        assert _scan_transcript_for_marker(str(transcript), "orders") is True

    def test_marker_not_found(self, tmp_path):
        from pre_edit_hook import _scan_transcript_for_marker
        transcript = tmp_path / "transcript.jsonl"
        transcript.write_text('line1\nline2\n')
        assert _scan_transcript_for_marker(str(transcript), "orders") is False

    def test_file_not_found(self):
        from pre_edit_hook import _scan_transcript_for_marker
        assert _scan_transcript_for_marker("/nonexistent/path", "orders") is False
