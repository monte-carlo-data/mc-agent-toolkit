import os
import json
import pytest

import lib.cache as cache
from lib.protocol import (
    HookInput,
    HookOutput,
    evaluate_pre_edit,
    evaluate_post_edit,
    evaluate_pre_commit,
    evaluate_turn_end,
    evaluate_validate_command,
    scan_transcript_for_markers,
)


class TestScanTranscriptForMarkers:
    def test_marker_found(self, tmp_path):
        transcript = tmp_path / "transcript.jsonl"
        transcript.write_text('line1\n<!-- MC_IMPACT_CHECK_COMPLETE: orders -->\nline3\n')
        result = scan_transcript_for_markers(str(transcript), "orders")
        assert result["impact_check"] is True

    def test_marker_not_found(self, tmp_path):
        transcript = tmp_path / "transcript.jsonl"
        transcript.write_text('line1\nline2\n')
        result = scan_transcript_for_markers(str(transcript), "orders")
        assert result["impact_check"] is False

    def test_file_not_found(self):
        result = scan_transcript_for_markers("/nonexistent/path", "orders")
        assert result["impact_check"] is False

    def test_monitor_gap_marker(self, tmp_path):
        transcript = tmp_path / "transcript.jsonl"
        transcript.write_text('<!-- MC_MONITOR_GAP: orders -->\n<!-- MC_IMPACT_CHECK_COMPLETE: orders -->\n')
        result = scan_transcript_for_markers(str(transcript), "orders")
        assert result["impact_check"] is True
        assert result["monitor_gap"] is True

    def test_partial_table_name_no_match(self, tmp_path):
        """client_hub should not match client_hub_master."""
        transcript = tmp_path / "transcript.jsonl"
        transcript.write_text('<!-- MC_IMPACT_CHECK_COMPLETE: client_hub -->\n')
        result = scan_transcript_for_markers(str(transcript), "client_hub_master")
        assert result["impact_check"] is False


class TestEvaluatePreEdit:
    def test_non_dbt_file_noop(self):
        inp = HookInput(session_id="s1", file_path="/project/scripts/hello.py")
        result = evaluate_pre_edit(inp)
        assert result.action == "noop"

    def test_dbt_model_first_edit_denies(self, tmp_path):
        model_dir = tmp_path / "models"
        model_dir.mkdir()
        sql_file = model_dir / "orders.sql"
        sql_file.write_text("SELECT * FROM {{ ref('raw') }}")

        inp = HookInput(session_id="s1", file_path=str(sql_file), transcript_path="")
        result = evaluate_pre_edit(inp)
        assert result.action == "deny"
        assert "impact assessment" in result.reason
        assert "orders" in result.reason

    def test_verified_state_noop(self, tmp_path):
        model_dir = tmp_path / "models"
        model_dir.mkdir()
        sql_file = model_dir / "orders.sql"
        sql_file.write_text("SELECT * FROM {{ ref('raw') }}")

        cache.mark_impact_check_injected("s1", "orders")
        cache.mark_impact_check_verified("s1", "orders")

        inp = HookInput(session_id="s1", file_path=str(sql_file))
        result = evaluate_pre_edit(inp)
        assert result.action == "noop"

    def test_injected_within_grace_no_marker_denies(self, tmp_path):
        model_dir = tmp_path / "models"
        model_dir.mkdir()
        sql_file = model_dir / "orders.sql"
        sql_file.write_text("SELECT * FROM {{ ref('raw') }}")

        cache.mark_impact_check_injected("s1", "orders")
        transcript = tmp_path / "transcript.jsonl"
        transcript.write_text('{"content": "some other message"}\n')

        inp = HookInput(session_id="s1", file_path=str(sql_file), transcript_path=str(transcript))
        result = evaluate_pre_edit(inp)
        assert result.action == "deny"
        assert "not completed yet" in result.reason

    def test_injected_with_marker_noop(self, tmp_path):
        model_dir = tmp_path / "models"
        model_dir.mkdir()
        sql_file = model_dir / "orders.sql"
        sql_file.write_text("SELECT * FROM {{ ref('raw') }}")

        cache.mark_impact_check_injected("s1", "orders")
        transcript = tmp_path / "transcript.jsonl"
        transcript.write_text('<!-- MC_IMPACT_CHECK_COMPLETE: orders -->\n')

        inp = HookInput(session_id="s1", file_path=str(sql_file), transcript_path=str(transcript))
        result = evaluate_pre_edit(inp)
        assert result.action == "noop"
        assert cache.get_impact_check_state("s1", "orders") == "verified"

    def test_new_file_noop(self, tmp_path):
        """Non-existent file (new model) should not be blocked."""
        inp = HookInput(session_id="s1", file_path=str(tmp_path / "models" / "new.sql"))
        result = evaluate_pre_edit(inp)
        assert result.action == "noop"

    def test_macro_file_denies_with_macro_message(self, tmp_path):
        macro_dir = tmp_path / "macros"
        macro_dir.mkdir()
        sql_file = macro_dir / "helper.sql"
        sql_file.write_text("{% macro helper() %} SELECT 1 {% endmacro %}")

        inp = HookInput(session_id="s1", file_path=str(sql_file), transcript_path="")
        result = evaluate_pre_edit(inp)
        assert result.action == "deny"
        assert "macro" in result.reason.lower()
        assert "helper" in result.reason


class TestEvaluatePostEdit:
    def test_non_dbt_file_noop(self):
        inp = HookInput(session_id="s1", file_path="/project/readme.md")
        result = evaluate_post_edit(inp)
        assert result.action == "noop"
        assert cache.get_edited_tables("s1") == []

    def test_dbt_model_tracked(self, tmp_path):
        model_dir = tmp_path / "models"
        model_dir.mkdir()
        sql_file = model_dir / "orders.sql"
        sql_file.write_text("SELECT * FROM {{ ref('raw') }}")

        inp = HookInput(session_id="s1", file_path=str(sql_file))
        evaluate_post_edit(inp)
        assert cache.get_edited_tables("s1") == ["orders"]


class TestEvaluatePreCommit:
    def test_non_commit_noop(self):
        inp = HookInput(session_id="s1", command="ls -la")
        result = evaluate_pre_commit(inp)
        assert result.action == "noop"

    def test_commit_with_w4_tables_adds_context(self):
        cache.mark_impact_check_injected("s1", "orders")
        cache.mark_impact_check_verified("s1", "orders")

        from unittest.mock import patch
        inp = HookInput(session_id="s1", command="git commit -m 'test'", cwd="/project")
        with patch("lib.protocol._get_staged_model_tables", return_value=["orders"]):
            result = evaluate_pre_commit(inp)
        assert result.action == "context"
        assert "orders" in result.context
        assert "validation" in result.context.lower()

    def test_commit_no_staged_sql_noop(self):
        from unittest.mock import patch
        inp = HookInput(session_id="s1", command="git commit -m 'test'", cwd="/project")
        with patch("lib.protocol._get_staged_model_tables", return_value=[]):
            result = evaluate_pre_commit(inp)
        assert result.action == "noop"


class TestEvaluateTurnEnd:
    def test_no_edits_noop(self):
        inp = HookInput(session_id="s1")
        result = evaluate_turn_end(inp)
        assert result.action == "noop"

    def test_stop_hook_active_noop(self):
        cache.add_edited_table("s1", "orders")
        cache.mark_impact_check_injected("s1", "orders")
        inp = HookInput(session_id="s1", stop_hook_active=True)
        result = evaluate_turn_end(inp)
        assert result.action == "noop"

    def test_edits_with_w4_blocks(self):
        cache.add_edited_table("s1", "orders")
        cache.mark_impact_check_injected("s1", "orders")
        cache.mark_impact_check_verified("s1", "orders")

        inp = HookInput(session_id="s1")
        result = evaluate_turn_end(inp)
        assert result.action == "block"
        assert "orders" in result.reason
        assert "validation" in result.reason.lower()

    def test_moves_to_pending(self):
        cache.add_edited_table("s1", "orders")
        cache.mark_impact_check_injected("s1", "orders")
        cache.mark_impact_check_verified("s1", "orders")

        inp = HookInput(session_id="s1")
        evaluate_turn_end(inp)
        assert cache.get_edited_tables("s1") == []
        assert "orders" in cache.get_pending_validation_tables("s1")

    def test_pending_exists_merges_silently(self):
        cache.add_edited_table("s1", "orders")
        cache.move_to_pending_validation("s1")
        cache.add_edited_table("s1", "customers")
        cache.mark_impact_check_injected("s1", "customers")

        inp = HookInput(session_id="s1")
        result = evaluate_turn_end(inp)
        assert result.action == "noop"
        pending = cache.get_pending_validation_tables("s1")
        assert "orders" in pending
        assert "customers" in pending

    def test_edits_without_w4_noop(self):
        cache.add_edited_table("s1", "orders")
        inp = HookInput(session_id="s1")
        result = evaluate_turn_end(inp)
        assert result.action == "noop"


class TestMonitorGapCleared:
    def test_turn_end_clears_gap_after_prompting(self):
        session_id = "test_clear_turnend"
        cache.mark_impact_check_injected(session_id, "orders")
        cache.mark_monitor_gap(session_id, "orders")
        cache.add_edited_table(session_id, "orders")

        result = evaluate_turn_end(HookInput(session_id=session_id, validate_command="/mc-validate"))

        assert "monitor coverage" in result.reason.lower()
        assert cache.has_monitor_gap(session_id, "orders") is False, \
            "gap should be cleared after the prompt is delivered"

    def test_pre_commit_clears_gap_after_prompting(self, monkeypatch):
        import lib.protocol as protocol
        session_id = "test_clear_precommit"
        cache.mark_impact_check_verified(session_id, "orders")
        cache.mark_monitor_gap(session_id, "orders")

        monkeypatch.setattr(protocol, "_get_staged_model_tables", lambda cwd: ["orders"])

        result = evaluate_pre_commit(HookInput(
            session_id=session_id,
            command="git commit -m test",
            cwd=".",
        ))

        assert "monitor coverage" in result.context.lower()
        assert cache.has_monitor_gap(session_id, "orders") is False, \
            "gap should be cleared after the pre-commit prompt is delivered"

    def test_turn_end_does_not_clear_when_no_gap(self):
        session_id = "test_no_clear"
        cache.mark_impact_check_injected(session_id, "orders")
        cache.add_edited_table(session_id, "orders")

        # No gap marked
        result = evaluate_turn_end(HookInput(session_id=session_id, validate_command="/mc-validate"))

        # Should still prompt for validation (the main turn_end behavior)
        assert result.action == "block"
        # And no gap was created as a side-effect
        assert cache.has_monitor_gap(session_id, "orders") is False


class TestEvaluateValidateCommand:
    def test_no_tables_returns_context(self):
        inp = HookInput(session_id="s1")
        result = evaluate_validate_command(inp)
        assert result.action == "context"
        assert "No dbt model changes" in result.context

    def test_pending_tables_returns_instruction(self):
        cache.add_edited_table("s1", "orders")
        cache.move_to_pending_validation("s1")
        cache.mark_impact_check_injected("s1", "orders")
        cache.mark_impact_check_verified("s1", "orders")

        inp = HookInput(session_id="s1")
        result = evaluate_validate_command(inp)
        assert result.action == "context"
        assert "orders" in result.context
        assert "validation query workflow" in result.context
