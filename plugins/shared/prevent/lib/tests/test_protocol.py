import os
import json
import subprocess

import pytest

import lib.cache as cache
from lib.protocol import (
    HookInput,
    HookOutput,
    evaluate_pre_edit,
    evaluate_post_edit,
    evaluate_pre_commit,
    evaluate_post_commit,
    record_pre_commit_head,
    evaluate_turn_end,
    evaluate_validate_command,
    scan_transcript_for_markers,
    scan_history_jsonl_for_markers,
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


class TestDenyReasonSelfBypass:
    """The pre-edit deny reason must never contain a marker that its own
    scanner would match. Harnesses that persist hook output back into the
    transcript (e.g. Cortex records it as a tool_result) would otherwise let
    the gate falsely unlock itself after the first deny. This is the
    source-side guard and protects every harness's scanner.
    """

    def _deny_reason(self, tmp_path, dirname, filename, body):
        d = tmp_path / dirname
        d.mkdir()
        sql_file = d / filename
        sql_file.write_text(body)
        result = evaluate_pre_edit(
            HookInput(session_id="s1", file_path=str(sql_file), transcript_path="")
        )
        assert result.action == "deny"
        return result.reason

    def test_model_deny_reason_does_not_self_unlock_raw_line(self, tmp_path):
        reason = self._deny_reason(tmp_path, "models", "orders.sql",
                                   "SELECT * FROM {{ ref('raw') }}")
        transcript = tmp_path / "t.jsonl"
        transcript.write_text(reason + "\n")
        result = scan_transcript_for_markers(str(transcript), "orders")
        assert result["impact_check"] is False, \
            "deny reason must not satisfy the raw-line scanner (CC/Codex/Cursor/Copilot)"

    def test_macro_deny_reason_does_not_self_unlock_raw_line(self, tmp_path):
        reason = self._deny_reason(tmp_path, "macros", "helper.sql",
                                   "{% macro helper() %} SELECT 1 {% endmacro %}")
        transcript = tmp_path / "t.jsonl"
        transcript.write_text(reason + "\n")
        result = scan_transcript_for_markers(str(transcript), "macro:helper")
        assert result["impact_check"] is False

    def test_model_deny_reason_does_not_self_unlock_history_jsonl(self, tmp_path):
        """The same invariant for the Cortex JSONL scanner (the path this work added)."""
        reason = self._deny_reason(tmp_path, "models", "orders.sql",
                                   "SELECT * FROM {{ ref('raw') }}")
        # As Cortex actually persists it — a tool_result under role "user" (ignored).
        tr = tmp_path / "tr.history.jsonl"
        tr.write_text(_user_tool_result(reason) + "\n")
        assert scan_history_jsonl_for_markers(str(tr), "orders")["impact_check"] is False
        # And even if it somehow landed in an assistant text block, the wording must not match.
        at = tmp_path / "at.history.jsonl"
        at.write_text(_assistant_text(reason) + "\n")
        assert scan_history_jsonl_for_markers(str(at), "orders")["impact_check"] is False

    def test_macro_deny_reason_does_not_self_unlock_history_jsonl(self, tmp_path):
        reason = self._deny_reason(tmp_path, "macros", "helper.sql",
                                   "{% macro helper() %} SELECT 1 {% endmacro %}")
        at = tmp_path / "at.history.jsonl"
        at.write_text(_assistant_text(reason) + "\n")
        assert scan_history_jsonl_for_markers(str(at), "macro:helper")["impact_check"] is False


class TestDenyReasonMarkerPlacement:
    """The deny reason says where and when to write the completion marker.

    CoCo Desktop saves an assistant message only after its edit's PreToolUse hook
    has run, so a marker in the same message as the retried edit isn't on disk when
    the gate scans. And a marker kept in the model's reasoning or inside a tool call
    is never scanned. The reason must steer the model to visible reply text, written
    only once the edit is going ahead, with the retry in a later step.
    """

    CASES = [
        ("models", "orders.sql", "SELECT * FROM {{ ref('raw') }}"),
        ("macros", "helper.sql", "{% macro helper() %} SELECT 1 {% endmacro %}"),
    ]

    def _reason(self, tmp_path, dirname, filename, body):
        d = tmp_path / dirname
        d.mkdir()
        sql_file = d / filename
        sql_file.write_text(body)
        result = evaluate_pre_edit(
            HookInput(session_id="s1", file_path=str(sql_file), transcript_path="")
        )
        assert result.action == "deny"
        return result.reason

    @pytest.mark.parametrize("dirname,filename,body", CASES)
    def test_marker_only_once_the_edit_goes_ahead(self, tmp_path, dirname, filename, body):
        reason = self._reason(tmp_path, dirname, filename, body)
        assert "only once the edit is going ahead" in reason
        assert "only after they say yes" in reason

    @pytest.mark.parametrize("dirname,filename,body", CASES)
    def test_denied_retry_checks_the_marker_is_in_reply_text(self, tmp_path, dirname, filename, body):
        reason = self._reason(tmp_path, dirname, filename, body)
        assert "check that the marker line is in your reply text" in reason
        # An editor-timing excuse gave a model a reason to retry blindly.
        assert "save a message only after" not in reason

    @pytest.mark.parametrize("dirname,filename,body", CASES)
    def test_workflow_note_names_the_asset_health_skill(self, tmp_path, dirname, filename, body):
        reason = self._reason(tmp_path, dirname, filename, body)
        assert "`monte-carlo-asset-health` skill" in reason

    @pytest.mark.parametrize("dirname,filename,body", CASES)
    def test_marker_in_visible_reply_text(self, tmp_path, dirname, filename, body):
        reason = self._reason(tmp_path, dirname, filename, body)
        assert "visible reply text" in reason
        assert "not only in your reasoning" in reason
        assert "not inside a tool call" in reason

    @pytest.mark.parametrize("dirname,filename,body", CASES)
    def test_retry_in_a_later_step_after_a_reread(self, tmp_path, dirname, filename, body):
        reason = self._reason(tmp_path, dirname, filename, body)
        assert "re-read the file" in reason
        assert "in a later step, not in the same batch" in reason

    def test_model_reason_keeps_the_explicit_ask(self, tmp_path):
        reason = self._reason(tmp_path, *self.CASES[0])
        assert "ask the user whether to proceed before retrying the edit" in reason


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


def _history_line(role, blocks):
    """Build one Anthropic Messages-style .history.jsonl line."""
    return json.dumps({"role": role, "content": blocks})


def _assistant_text(text):
    return _history_line("assistant", [{"type": "text", "text": text}])


def _user_tool_result(text):
    """A tool_result delivered under role 'user' — how Cortex persists hook output."""
    return _history_line("user", [{
        "type": "tool_result",
        "tool_result": {"content": [{"type": "text", "text": text}]},
    }])


class TestScanHistoryJsonl:
    """Cortex scans only assistant-authored text blocks of <id>.history.jsonl."""

    def test_marker_in_assistant_text_found(self, tmp_path):
        h = tmp_path / "s.history.jsonl"
        h.write_text(
            _assistant_text("Assessment complete. <!-- MC_IMPACT_CHECK_COMPLETE: orders -->\n") + "\n"
        )
        result = scan_history_jsonl_for_markers(str(h), "orders")
        assert result["impact_check"] is True

    def test_marker_in_tool_result_not_found(self, tmp_path):
        """The persisted hook deny reason lives in a tool_result (role user) and
        must NOT unlock the gate, even if it contains a verbatim marker."""
        h = tmp_path / "s.history.jsonl"
        h.write_text(_user_tool_result("[Hook] ... MC_IMPACT_CHECK_COMPLETE: orders ...") + "\n")
        result = scan_history_jsonl_for_markers(str(h), "orders")
        assert result["impact_check"] is False

    def test_monitor_gap_in_assistant_text_found(self, tmp_path):
        h = tmp_path / "s.history.jsonl"
        h.write_text(
            _assistant_text("<!-- MC_MONITOR_GAP: orders --> <!-- MC_IMPACT_CHECK_COMPLETE: orders -->") + "\n"
        )
        result = scan_history_jsonl_for_markers(str(h), "orders")
        assert result["impact_check"] is True
        assert result["monitor_gap"] is True

    def test_string_content_assistant_found(self, tmp_path):
        h = tmp_path / "s.history.jsonl"
        h.write_text(_history_line("assistant", "inline MC_IMPACT_CHECK_COMPLETE: orders here") + "\n")
        result = scan_history_jsonl_for_markers(str(h), "orders")
        assert result["impact_check"] is True

    def test_partial_table_name_no_match(self, tmp_path):
        h = tmp_path / "s.history.jsonl"
        h.write_text(_assistant_text("<!-- MC_IMPACT_CHECK_COMPLETE: client_hub -->") + "\n")
        result = scan_history_jsonl_for_markers(str(h), "client_hub_master")
        assert result["impact_check"] is False

    # --- robustness: must fail closed, never raise ---

    def test_missing_file_not_found(self):
        result = scan_history_jsonl_for_markers("/nonexistent/s.history.jsonl", "orders")
        assert result == {"impact_check": False, "monitor_gap": False}

    def test_malformed_line_skipped_valid_line_still_found(self, tmp_path):
        h = tmp_path / "s.history.jsonl"
        h.write_text(
            "this is not json\n"
            + _assistant_text("<!-- MC_IMPACT_CHECK_COMPLETE: orders -->") + "\n"
            + "{also not valid\n"
        )
        result = scan_history_jsonl_for_markers(str(h), "orders")
        assert result["impact_check"] is True

    def test_lines_missing_role_or_content_skipped(self, tmp_path):
        h = tmp_path / "s.history.jsonl"
        h.write_text(
            json.dumps({"foo": "bar"}) + "\n"
            + json.dumps({"role": "assistant"}) + "\n"            # no content key
            + json.dumps({"role": "user", "content": None}) + "\n"
            + json.dumps(["not", "a", "dict"]) + "\n"
        )
        result = scan_history_jsonl_for_markers(str(h), "orders")
        assert result == {"impact_check": False, "monitor_gap": False}


class TestEvaluatePreEditCortex:
    """evaluate_pre_edit honors transcript_format='messages_jsonl' for Cortex."""

    def _model(self, tmp_path):
        model_dir = tmp_path / "models"
        model_dir.mkdir()
        sql_file = model_dir / "orders.sql"
        sql_file.write_text("SELECT * FROM {{ ref('raw') }}")
        return sql_file

    def test_injected_with_marker_in_history_verifies(self, tmp_path):
        sql_file = self._model(tmp_path)
        cache.mark_impact_check_injected("s1", "orders")
        h = tmp_path / "s.history.jsonl"
        h.write_text(_assistant_text("<!-- MC_IMPACT_CHECK_COMPLETE: orders -->") + "\n")

        inp = HookInput(session_id="s1", file_path=str(sql_file),
                        transcript_path=str(h), transcript_format="messages_jsonl")
        result = evaluate_pre_edit(inp)
        assert result.action == "noop"
        assert cache.get_impact_check_state("s1", "orders") == "verified"

    def test_state_none_with_marker_in_history_verifies(self, tmp_path):
        sql_file = self._model(tmp_path)
        h = tmp_path / "s.history.jsonl"
        h.write_text(_assistant_text("<!-- MC_IMPACT_CHECK_COMPLETE: orders -->") + "\n")

        inp = HookInput(session_id="s1", file_path=str(sql_file),
                        transcript_path=str(h), transcript_format="messages_jsonl")
        result = evaluate_pre_edit(inp)
        assert result.action == "noop"
        assert cache.get_impact_check_state("s1", "orders") == "verified"

    def test_marker_only_in_tool_result_does_not_unlock(self, tmp_path):
        """End-to-end: a marker the gate itself emitted (persisted as a tool_result)
        must not unlock the gate — the edit stays denied within the grace period."""
        sql_file = self._model(tmp_path)
        cache.mark_impact_check_injected("s1", "orders")
        h = tmp_path / "s.history.jsonl"
        h.write_text(_user_tool_result("[Hook] ... MC_IMPACT_CHECK_COMPLETE: orders ...") + "\n")

        inp = HookInput(session_id="s1", file_path=str(sql_file),
                        transcript_path=str(h), transcript_format="messages_jsonl")
        result = evaluate_pre_edit(inp)
        assert result.action == "deny"
        assert cache.get_impact_check_state("s1", "orders") == "injected"

    def test_empty_transcript_path_denies(self, tmp_path):
        """Cortex format with no transcript yet (e.g. first turn) -> fail closed."""
        sql_file = self._model(tmp_path)
        inp = HookInput(session_id="s1", file_path=str(sql_file),
                        transcript_path="", transcript_format="messages_jsonl")
        assert evaluate_pre_edit(inp).action == "deny"

    def test_unknown_transcript_format_fails_closed(self, tmp_path):
        """A misspelled/unknown format must not unlock via the wrong scanner."""
        sql_file = self._model(tmp_path)
        cache.mark_impact_check_injected("s1", "orders")
        h = tmp_path / "s.history.jsonl"
        h.write_text(_assistant_text("<!-- MC_IMPACT_CHECK_COMPLETE: orders -->") + "\n")
        inp = HookInput(session_id="s1", file_path=str(sql_file),
                        transcript_path=str(h), transcript_format="messages-jsonl")  # typo
        assert evaluate_pre_edit(inp).action == "deny"


# --- Post-commit Bayes follow-up offer ---

_MODEL_SQL = "select * from {{ ref('raw_orders') }}\n"


def _git(repo, *args):
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false", *args],
        cwd=repo, check=True, capture_output=True,
    )


@pytest.fixture
def dbt_repo(tmp_path):
    """A git repo holding a dbt project, with one commit."""
    repo = tmp_path / "repo"
    (repo / "models").mkdir(parents=True)
    (repo / "macros").mkdir()
    (repo / "dbt_project.yml").write_text("name: demo\n")
    (repo / "README.md").write_text("demo\n")
    _git(repo, "init", "-q")
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", "init")
    return repo


def _commit(repo, files, message="change"):
    for rel, content in files.items():
        path = repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    _git(repo, "add", ".")
    _git(repo, "commit", "-q", "-m", message)


def _pre(repo, session="s1", command="git commit -m change"):
    inp = HookInput(session_id=session, command=command, cwd=str(repo))
    record_pre_commit_head(inp)
    return evaluate_pre_commit(inp)


def _post(session="s1", command="git commit -m change"):
    return evaluate_post_commit(HookInput(session_id=session, command=command))


class TestEvaluatePostCommit:
    def test_model_commit_offers_follow_up(self, dbt_repo):
        _pre(dbt_repo)
        _commit(dbt_repo, {"models/orders.sql": _MODEL_SQL})
        result = _post()
        assert result.action == "context"
        assert "orders" in result.context
        assert "schedule_agent_task" in result.context
        assert "Do NOT call `schedule_agent_task` unless the user says yes" in result.context

    def test_offer_lets_user_pick_where_answer_goes(self, dbt_repo):
        # schedule_agent_task takes deliver="dm"|"channel" and says never pick for the user.
        _pre(dbt_repo)
        _commit(dbt_repo, {"models/orders.sql": _MODEL_SQL})
        result = _post()
        assert result.action == "context"
        assert "direct message" not in result.context.lower()
        assert "let the user pick" in result.context

    def test_failed_commit_noop(self, dbt_repo):
        (dbt_repo / "models").joinpath("orders.sql").write_text(_MODEL_SQL)
        _git(dbt_repo, "add", ".")
        _git(dbt_repo, "commit", "-q", "-m", "orders")
        _pre(dbt_repo)
        # The commit fails: HEAD stays where it was, even though HEAD changes a model.
        assert _post().action == "noop"

    def test_no_snapshot_noop(self, dbt_repo):
        _commit(dbt_repo, {"models/orders.sql": _MODEL_SQL})
        assert _post().action == "noop"

    def test_non_commit_command_noop(self, dbt_repo):
        _pre(dbt_repo)
        _commit(dbt_repo, {"models/orders.sql": _MODEL_SQL})
        assert _post(command="git status").action == "noop"

    def test_non_model_files_noop(self, dbt_repo):
        _pre(dbt_repo)
        _commit(dbt_repo, {"README.md": "changed\n", "scripts/load.py": "print(1)\n"})
        assert _post().action == "noop"

    def test_macro_only_noop(self, dbt_repo):
        _pre(dbt_repo)
        _commit(dbt_repo, {"macros/cents.sql": "{% macro cents(x) %}{{ x }}*100{% endmacro %}\n"})
        assert _post().action == "noop"

    def test_commit_all_flag_is_seen(self, dbt_repo):
        """`git commit -a` stages at commit time, so nothing is staged when pre-commit runs."""
        _commit(dbt_repo, {"models/orders.sql": _MODEL_SQL})
        (dbt_repo / "models" / "orders.sql").write_text(_MODEL_SQL + "-- edited\n")
        _pre(dbt_repo, command="git commit -am edit")
        _git(dbt_repo, "commit", "-q", "-am", "edit")
        result = _post(command="git commit -am edit")
        assert result.action == "context"
        assert "orders" in result.context

    def test_same_table_offered_once_per_session(self, dbt_repo):
        _pre(dbt_repo)
        _commit(dbt_repo, {"models/orders.sql": _MODEL_SQL})
        assert _post().action == "context"

        _pre(dbt_repo)
        _commit(dbt_repo, {"models/orders.sql": _MODEL_SQL + "-- again\n"})
        assert _post().action == "noop"

    def test_new_table_offered_alone(self, dbt_repo):
        _pre(dbt_repo)
        _commit(dbt_repo, {"models/orders.sql": _MODEL_SQL})
        _post()

        _pre(dbt_repo)
        _commit(dbt_repo, {
            "models/orders.sql": _MODEL_SQL + "-- again\n",
            "models/customers.sql": _MODEL_SQL,
        })
        result = _post()
        assert result.action == "context"
        assert "customers" in result.context
        assert "orders" not in result.context

    def test_other_session_offered_again(self, dbt_repo):
        _pre(dbt_repo, session="s1")
        _commit(dbt_repo, {"models/orders.sql": _MODEL_SQL})
        _post(session="s1")

        _pre(dbt_repo, session="s2")
        _commit(dbt_repo, {"models/orders.sql": _MODEL_SQL + "-- again\n"})
        assert _post(session="s2").action == "context"

    @pytest.mark.parametrize("env_var", ["MC_BAYES_FOLLOWUP_DISABLED", "MC_PREVENT_HOOKS_DISABLED"])
    def test_off_switch_after_snapshot(self, dbt_repo, monkeypatch, env_var):
        _pre(dbt_repo)
        _commit(dbt_repo, {"models/orders.sql": _MODEL_SQL})
        monkeypatch.setenv(env_var, "1")
        assert _post().action == "noop"

    @pytest.mark.parametrize("env_var", ["MC_BAYES_FOLLOWUP_DISABLED", "MC_PREVENT_HOOKS_DISABLED"])
    def test_off_switch_takes_no_snapshot(self, dbt_repo, monkeypatch, env_var):
        monkeypatch.setenv(env_var, "1")
        record_pre_commit_head(
            HookInput(session_id="s1", command="git commit -m change", cwd=str(dbt_repo))
        )
        assert cache.get_head_snapshot("s1") is None

    def test_subdirectory_cwd_offers_follow_up(self, dbt_repo):
        _pre(dbt_repo / "models")
        _commit(dbt_repo, {"models/orders.sql": _MODEL_SQL})
        result = _post()
        assert result.action == "context"
        assert "orders" in result.context

    def test_nested_dbt_project_offers_follow_up(self, dbt_repo):
        (dbt_repo / "dbt").mkdir()
        (dbt_repo / "dbt" / "dbt_project.yml").write_text("name: nested\n")
        _pre(dbt_repo / "dbt")
        _commit(dbt_repo, {"dbt/models/customers.sql": _MODEL_SQL})
        result = _post()
        assert result.action == "context"
        assert "customers" in result.context

    def test_first_commit_in_empty_repo_offers_follow_up(self, tmp_path):
        repo = tmp_path / "fresh"
        (repo / "models").mkdir(parents=True)
        (repo / "dbt_project.yml").write_text("name: demo\n")
        (repo / "models" / "orders.sql").write_text(_MODEL_SQL)
        _git(repo, "init", "-q")
        _pre(repo)
        assert cache.get_head_snapshot("s1")["sha"] == ""
        _git(repo, "add", ".")
        _git(repo, "commit", "-q", "-m", "first")
        result = _post()
        assert result.action == "context"
        assert "orders" in result.context

    @staticmethod
    def _offered_tables(context):
        return set(context.split("changed dbt model(s): ")[1].split(". ")[0].split(", "))

    def test_deleted_model_is_offered(self, dbt_repo):
        _commit(dbt_repo, {"models/orders.sql": _MODEL_SQL})
        _pre(dbt_repo)
        _git(dbt_repo, "rm", "-q", "models/orders.sql")
        _git(dbt_repo, "commit", "-q", "-m", "drop orders")
        result = _post()
        assert result.action == "context"
        assert "orders" in result.context

    def test_renamed_model_offers_old_and_new_names(self, dbt_repo):
        _commit(dbt_repo, {"models/orders.sql": _MODEL_SQL})
        _pre(dbt_repo)
        _git(dbt_repo, "mv", "models/orders.sql", "models/fct_orders.sql")
        _git(dbt_repo, "commit", "-q", "-m", "rename")
        result = _post()
        assert result.action == "context"
        assert "changed dbt model(s): " in result.context
        assert self._offered_tables(result.context) == {"orders", "fct_orders"}

    def test_non_ascii_model_name_is_offered(self, dbt_repo):
        _pre(dbt_repo)
        _commit(dbt_repo, {"models/é.sql": _MODEL_SQL})
        result = _post()
        assert result.action == "context"
        assert "é" in result.context

    def test_model_name_with_space_is_not_offered(self, dbt_repo):
        _pre(dbt_repo)
        _commit(dbt_repo, {"models/bad name.sql": _MODEL_SQL})
        assert _post().action == "noop"

    def test_off_switch_keeps_pre_commit_prompt(self, dbt_repo, monkeypatch):
        """MC_BAYES_FOLLOWUP_DISABLED turns off the offer only, not the validation prompt."""
        from unittest.mock import patch
        monkeypatch.setenv("MC_BAYES_FOLLOWUP_DISABLED", "1")
        cache.mark_impact_check_verified("s1", "orders")
        with patch("lib.protocol._get_staged_model_tables", return_value=["orders"]):
            result = _pre(dbt_repo)
        assert result.action == "context"
        assert "validation" in result.context.lower()


class TestEvaluatePreCommitOutputIsUnchanged:
    """Claude Code, Codex, Cursor and Copilot show this text verbatim."""

    def test_exact_text_without_gap(self, monkeypatch):
        import lib.protocol as protocol
        cache.mark_impact_check_verified("s1", "orders")
        cache.mark_impact_check_verified("s1", "customers")
        monkeypatch.setattr(protocol, "_get_staged_model_tables", lambda cwd: ["orders", "customers"])
        result = evaluate_pre_commit(HookInput(session_id="s1", command="git commit -m x", cwd="."))
        assert result.action == "context"
        assert result.context == (
            "Committing changes to orders, customers. "
            "Run validation queries before committing? (yes / no)"
        )

    def test_exact_text_with_gap(self, monkeypatch):
        import lib.protocol as protocol
        cache.mark_impact_check_verified("s1", "orders")
        cache.mark_impact_check_verified("s1", "customers")
        cache.mark_monitor_gap("s1", "customers")
        monkeypatch.setattr(protocol, "_get_staged_model_tables", lambda cwd: ["orders", "customers"])
        result = evaluate_pre_commit(HookInput(session_id="s1", command="git commit -m x", cwd="."))
        assert result.context == (
            "Committing changes to orders, customers. "
            "Run validation queries before committing? (yes / no)"
            "\n\nMonitor coverage: the impact assessment found no custom monitors "
            "on customers. Generate monitor definitions before committing? (yes / no)"
        )
        assert cache.has_monitor_gap("s1", "customers") is False

    def test_duplicate_names_are_listed_as_before(self, monkeypatch):
        import lib.protocol as protocol
        cache.mark_impact_check_verified("s1", "orders")
        monkeypatch.setattr(protocol, "_get_staged_model_tables", lambda cwd: ["orders", "orders"])
        result = evaluate_pre_commit(HookInput(session_id="s1", command="git commit -m x", cwd="."))
        assert result.context.startswith("Committing changes to orders, orders. ")
