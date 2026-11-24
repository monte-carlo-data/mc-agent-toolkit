"""CoCo Desktop `apply_patch` support: the pre-edit gate over every file a patch touches,
and post-edit tracking driven by the tool's result. The parser's own tests are in
plugins/shared/prevent/lib/tests/test_apply_patch.py.

Desktop gives GPT/OpenAI models `apply_patch` instead of edit/write. The hook payload
carries the patch in `tool_input.input`, the session directory in `cwd`, and (for
PostToolUse) the tool's result content as a JSON string in `tool_response`.
"""
import json
from io import StringIO
from unittest.mock import patch

import pytest

import lib.cache as cache
from lib.protocol import HookOutput, _compile_marker_patterns

SESSION = "test_session"
MODEL_SQL = "SELECT * FROM {{ ref('raw') }}\n"
MACRO_SQL = "{% macro internal_accounts() %} 1 {% endmacro %}\n"


def _patch(*body):
    return "\n".join(["*** Begin Patch", *body, "*** End Patch"]) + "\n"


def _update(path, old="a", new="b"):
    return [f"*** Update File: {path}", "@@", f"-{old}", f"+{new}"]


@pytest.fixture
def project(tmp_path):
    """A dbt project dir with two models, a macro and a non-dbt file."""
    root = tmp_path / "proj"
    (root / "models").mkdir(parents=True)
    (root / "macros").mkdir()
    (root / "models" / "orders.sql").write_text(MODEL_SQL)
    (root / "models" / "customers.sql").write_text(MODEL_SQL)
    (root / "macros" / "internal_accounts.sql").write_text(MACRO_SQL)
    (root / "README.md").write_text("hello\n")
    return root


def _session_files(tmp_path, *assistant_texts, tool_result_text=None):
    """Cortex metadata path plus a sibling .history.jsonl with the given messages."""
    meta = tmp_path / "sess.json"
    meta.write_text('{"session_id": "test_session"}')
    lines = [json.dumps({"role": "assistant", "content": [{"type": "text", "text": t}]})
             for t in assistant_texts]
    if tool_result_text is not None:
        lines.append(json.dumps({"role": "user", "content": [{"type": "tool_result", "tool_result": {
            "content": [{"type": "text", "text": tool_result_text}]}}]}))
    (tmp_path / "sess.history.jsonl").write_text("\n".join(lines) + "\n")
    return str(meta)


def _pre_stdin(patch_text, cwd, transcript="", tool_name="apply_patch", tool_input=None):
    return json.dumps({
        "session_id": SESSION,
        "transcript_path": transcript,
        "cwd": cwd,
        "hook_event_name": "PreToolUse",
        "tool_name": tool_name,
        "tool_input": tool_input if tool_input is not None else {"input": patch_text},
        "tool_use_id": "call_test",
    })


def _post_stdin(patch_text, cwd, response_text):
    return json.dumps({
        "session_id": SESSION,
        "transcript_path": "",
        "cwd": cwd,
        "hook_event_name": "PostToolUse",
        "tool_name": "apply_patch",
        "tool_input": {"input": patch_text},
        "tool_use_id": "call_test",
        "tool_response": json.dumps([{"kind": "text", "value": response_text}]),
    })


def _run_pre(stdin, capsys):
    with patch("sys.stdin", StringIO(stdin)):
        from pre_edit_hook import main
        main()
    out = capsys.readouterr().out
    return json.loads(out)["hookSpecificOutput"] if out else None


def _run_post(stdin):
    with patch("sys.stdin", StringIO(stdin)):
        from post_edit_hook import main
        main()


class TestAppliedOperations:
    def _ops(self):
        from lib.apply_patch import parse_operations
        return parse_operations(_patch(
            *_update("models/orders.sql"),
            "*** Update File: models/customers.sql", "*** Move to: models/clients.sql",
            "*** Delete File: README.md"))

    def _applied(self, response):
        from patch_result import applied_operations
        return [op.path for op in applied_operations(self._ops(), response)]

    def _resp(self, text):
        return json.dumps([{"kind": "text", "value": text}])

    def test_success_keeps_all(self):
        assert self._applied(self._resp("Applied 3 operation(s) (1 added, 1 removed) across 4 file(s).")) == [
            "models/orders.sql", "models/customers.sql", "README.md"]

    def test_parse_error_keeps_none(self):
        assert self._applied(self._resp("Error parsing apply_patch input: Patch must start with '*** Begin Patch'")) == []

    def test_partial_keeps_operations_before_the_failing_one(self):
        assert self._applied(self._resp(
            "Error: Patch partially applied through operation 3/3: file not found")) == [
            "models/orders.sql", "models/customers.sql"]

    def test_partial_keeps_failing_move(self):
        """A move writes its destination before deleting the source, so a move that
        failed may already have changed disk."""
        assert self._applied(self._resp(
            "Error: Patch partially applied through operation 2/3: delete failed")) == [
            "models/orders.sql", "models/customers.sql"]

    def test_partial_on_first_update_keeps_none(self):
        assert self._applied(self._resp(
            "Error: Patch partially applied through operation 1/3: context not found")) == []

    def test_unknown_result_keeps_all(self):
        assert len(self._applied(self._resp("The model wants to edit files outside the workspace."))) == 3

    def test_missing_or_malformed_response_keeps_all(self):
        assert len(self._applied(None)) == 3
        assert len(self._applied("not json")) == 3
        assert len(self._applied(json.dumps({"unexpected": True}))) == 3
        assert len(self._applied("null")) == 3
        assert len(self._applied("5")) == 3

    def test_failure_beyond_the_last_operation_keeps_all(self):
        assert len(self._applied(self._resp("Error: Patch partially applied through operation 9/3: x"))) == 3

    @pytest.mark.parametrize("text", [
        "apply_patch verification failed: Update file hunk for path 'models/orders.sql' is empty",
        "apply_patch received invalid input text",
        "apply_patch handler received non-apply_patch input",
        "Missing required parameter: input",
    ])
    def test_cli_errors_before_writing_keep_none(self, text):
        """Cortex Code CLI results returned before any file is written, as a plain string
        or as the CLI's result object."""
        assert self._applied(text) == []
        assert self._applied({"content": [{"type": "text", "text": text}], "status": "error"}) == []
        assert self._applied(json.dumps({"content": [{"type": "text", "text": text}], "status": "error"})) == []

    def test_cli_success_object_keeps_all(self):
        response = {"content": [{"type": "text", "text": "Applied patch successfully (3 file operation(s))."}],
                    "status": "success"}
        assert len(self._applied(response)) == 3

    def test_cli_error_during_operations_keeps_all(self):
        """A CLI failure partway through can follow earlier writes, so nothing is dropped."""
        response = {"content": [{"type": "text", "text": "Cannot update missing file: /p/README.md"}], "status": "error"}
        assert len(self._applied(response)) == 3


# --- Pre-edit gate ---

class TestPreEditApplyPatch:
    def test_patch_to_existing_model_denied(self, project, tmp_path, capsys):
        out = _run_pre(_pre_stdin(_patch(*_update("models/orders.sql")), str(project),
                                  _session_files(tmp_path)), capsys)
        assert out["permissionDecision"] == "deny"
        assert "orders" in out["permissionDecisionReason"]
        assert cache.get_impact_check_state(SESSION, "orders") == "injected"

    def test_marker_in_assistant_text_allows(self, project, tmp_path, capsys):
        meta = _session_files(tmp_path, "Assessment done.\nMC_IMPACT_CHECK_COMPLETE: orders")
        out = _run_pre(_pre_stdin(_patch(*_update("models/orders.sql")), str(project), meta), capsys)
        assert out is None
        assert cache.get_impact_check_state(SESSION, "orders") == "verified"

    def test_marker_only_in_tool_result_still_denied(self, project, tmp_path, capsys):
        meta = _session_files(tmp_path, tool_result_text="MC_IMPACT_CHECK_COMPLETE: orders")
        out = _run_pre(_pre_stdin(_patch(*_update("models/orders.sql")), str(project), meta), capsys)
        assert out["permissionDecision"] == "deny"

    @pytest.mark.parametrize("order", ["model_first", "other_first"])
    def test_model_and_other_file_denied_as_a_whole(self, project, tmp_path, capsys, order):
        parts = [_update("models/orders.sql"), _update("README.md")]
        if order == "other_first":
            parts.reverse()
        out = _run_pre(_pre_stdin(_patch(*parts[0], *parts[1]), str(project), _session_files(tmp_path)), capsys)
        assert out["permissionDecision"] == "deny"
        reason = out["permissionDecisionReason"]
        assert "orders" in reason
        assert "whole patch" in reason

    def test_two_unassessed_models_named_in_one_deny(self, project, tmp_path, capsys):
        text = _patch(*_update("models/orders.sql"), *_update("models/customers.sql"))
        out = _run_pre(_pre_stdin(text, str(project), _session_files(tmp_path)), capsys)
        reason = out["permissionDecisionReason"]
        assert "orders" in reason and "customers" in reason
        assert cache.get_impact_check_state(SESSION, "orders") == "injected"
        assert cache.get_impact_check_state(SESSION, "customers") == "injected"

    def test_one_marker_then_both(self, project, tmp_path, capsys):
        text = _patch(*_update("models/orders.sql"), *_update("models/customers.sql"))
        meta = _session_files(tmp_path, "MC_IMPACT_CHECK_COMPLETE: orders")
        out = _run_pre(_pre_stdin(text, str(project), meta), capsys)
        assert out["permissionDecision"] == "deny"
        assert "customers" in out["permissionDecisionReason"]
        assert cache.get_impact_check_state(SESSION, "orders") == "verified"

        meta = _session_files(tmp_path, "MC_IMPACT_CHECK_COMPLETE: orders", "MC_IMPACT_CHECK_COMPLETE: customers")
        assert _run_pre(_pre_stdin(text, str(project), meta), capsys) is None
        assert cache.get_impact_check_state(SESSION, "customers") == "verified"

    def test_model_and_macro_keep_their_own_wording(self, project, tmp_path, capsys):
        text = _patch(*_update("models/orders.sql"), *_update("macros/internal_accounts.sql"))
        reason = _run_pre(_pre_stdin(text, str(project), _session_files(tmp_path)), capsys)["permissionDecisionReason"]
        assert "macro:internal_accounts" in reason
        assert "inlined into models" in reason
        assert "run the change impact assessment for orders" in reason

    def test_combined_reason_does_not_satisfy_the_marker_scanner(self, project, tmp_path, capsys):
        text = _patch(*_update("models/orders.sql"), *_update("models/customers.sql"),
                      *_update("macros/internal_accounts.sql"))
        reason = _run_pre(_pre_stdin(text, str(project), _session_files(tmp_path)), capsys)["permissionDecisionReason"]
        for table in ("orders", "customers", "internal_accounts", "macro:internal_accounts"):
            ic, mg = _compile_marker_patterns(table)
            assert not ic.search(reason) and not mg.search(reason)

    def test_single_file_patch_keeps_the_plain_reason(self, project, tmp_path, capsys):
        reason = _run_pre(_pre_stdin(_patch(*_update("models/orders.sql")), str(project),
                                     _session_files(tmp_path)), capsys)["permissionDecisionReason"]
        assert reason.startswith("Monte Carlo Prevent: run the change impact assessment for orders")

    def test_rename_of_a_model_keeps_the_plain_reason(self, project, tmp_path, capsys):
        text = _patch("*** Update File: models/orders.sql", "*** Move to: models/orders_v2.sql")
        reason = _run_pre(_pre_stdin(text, str(project), _session_files(tmp_path)), capsys)["permissionDecisionReason"]
        assert reason.startswith("Monte Carlo Prevent: run the change impact assessment for orders")

    def test_same_file_twice_keeps_the_plain_reason(self, project, tmp_path, capsys):
        text = _patch(*_update("models/orders.sql"), *_update("./models/orders.sql", "c", "d"))
        reason = _run_pre(_pre_stdin(text, str(project), _session_files(tmp_path)), capsys)["permissionDecisionReason"]
        assert reason.startswith("Monte Carlo Prevent: run the change impact assessment for orders")

    def test_two_files_with_the_same_table_name_get_the_full_instructions(self, project, tmp_path, capsys):
        """The second file is inside the first one's grace period; its short reason must
        not replace the first file's instructions."""
        (project / "models" / "b").mkdir()
        (project / "models" / "b" / "orders.sql").write_text(MODEL_SQL)
        text = _patch(*_update("models/orders.sql"), *_update("models/b/orders.sql", "c", "d"))
        reason = _run_pre(_pre_stdin(text, str(project), _session_files(tmp_path)), capsys)["permissionDecisionReason"]
        assert reason.startswith("Monte Carlo Prevent: run the change impact assessment for orders")
        assert "has not completed yet" not in reason

    def test_split_hint_only_when_other_files_are_in_the_patch(self, project, tmp_path, capsys):
        models_only = _patch(*_update("models/orders.sql"), *_update("models/customers.sql"))
        reason = _run_pre(_pre_stdin(models_only, str(project), _session_files(tmp_path)), capsys)["permissionDecisionReason"]
        assert "this patch touches 2 files" in reason
        assert "split out" not in reason

        mixed = _patch(*_update("models/orders.sql"), *_update("README.md"))
        reason = _run_pre(_pre_stdin(mixed, str(project), _session_files(tmp_path)), capsys)["permissionDecisionReason"]
        assert "split out the changes to other files" in reason

    def test_indented_patch_still_gated(self, project, tmp_path, capsys):
        text = "  *** Begin Patch\n  *** Delete File: models/orders.sql\n  *** End Patch\n"
        assert _run_pre(_pre_stdin(text, str(project), _session_files(tmp_path)), capsys)["permissionDecision"] == "deny"

    def test_non_dbt_patch_allowed(self, project, tmp_path, capsys):
        assert _run_pre(_pre_stdin(_patch(*_update("README.md")), str(project), _session_files(tmp_path)), capsys) is None

    def test_relative_path_resolved_against_payload_cwd(self, project, tmp_path, capsys, monkeypatch):
        elsewhere = tmp_path / "elsewhere"
        elsewhere.mkdir()
        monkeypatch.chdir(elsewhere)
        out = _run_pre(_pre_stdin(_patch(*_update("models/orders.sql")), str(project),
                                  _session_files(tmp_path)), capsys)
        assert out["permissionDecision"] == "deny"

    def test_unnormalized_path_still_gated(self, project, tmp_path, capsys):
        """A seeds/ component is excluded from gating, so the path must be normalized first."""
        out = _run_pre(_pre_stdin(_patch(*_update("seeds/../models/./orders.sql")), str(project),
                                  _session_files(tmp_path)), capsys)
        assert out["permissionDecision"] == "deny"

    def test_absolute_path_gated(self, project, tmp_path, capsys):
        out = _run_pre(_pre_stdin(_patch(*_update(str(project / "models" / "orders.sql"))), str(tmp_path),
                                  _session_files(tmp_path)), capsys)
        assert out["permissionDecision"] == "deny"

    def test_path_through_linked_folder_gated(self, project, tmp_path, capsys):
        (project / "dbtlink").symlink_to(project / "models", target_is_directory=True)
        out = _run_pre(_pre_stdin(_patch(*_update("dbtlink/orders.sql")), str(project),
                                  _session_files(tmp_path)), capsys)
        assert out["permissionDecision"] == "deny"
        assert out["permissionDecisionReason"].startswith("Monte Carlo Prevent: run the change impact assessment for orders")

    def test_add_new_model_allowed(self, project, tmp_path, capsys):
        text = _patch("*** Add File: models/brand_new.sql", "+select 1")
        assert _run_pre(_pre_stdin(text, str(project), _session_files(tmp_path)), capsys) is None

    def test_add_over_existing_model_denied(self, project, tmp_path, capsys):
        text = _patch("*** Add File: models/orders.sql", "+select 1")
        assert _run_pre(_pre_stdin(text, str(project), _session_files(tmp_path)), capsys)["permissionDecision"] == "deny"

    def test_delete_existing_model_denied(self, project, tmp_path, capsys):
        text = _patch("*** Delete File: models/orders.sql")
        assert _run_pre(_pre_stdin(text, str(project), _session_files(tmp_path)), capsys)["permissionDecision"] == "deny"

    def test_move_existing_model_denied(self, project, tmp_path, capsys):
        text = _patch("*** Update File: models/orders.sql", "*** Move to: models/orders_v2.sql")
        assert _run_pre(_pre_stdin(text, str(project), _session_files(tmp_path)), capsys)["permissionDecision"] == "deny"

    def test_move_onto_existing_model_denied(self, project, tmp_path, capsys):
        text = _patch("*** Update File: README.md", "*** Move to: models/orders.sql")
        out = _run_pre(_pre_stdin(text, str(project), _session_files(tmp_path)), capsys)
        assert out["permissionDecision"] == "deny"
        assert "orders" in out["permissionDecisionReason"]

    def test_deny_does_not_track_an_edit(self, project, tmp_path, capsys):
        _run_pre(_pre_stdin(_patch(*_update("models/orders.sql")), str(project), _session_files(tmp_path)), capsys)
        assert cache.get_edited_tables(SESSION) == []

    def test_error_on_a_later_file_keeps_earlier_deny(self, project, tmp_path, capsys):
        import pre_edit_hook
        real = pre_edit_hook.evaluate_pre_edit
        calls = []

        def flaky(inp):
            calls.append(inp.file_path)
            if inp.file_path.endswith("README.md"):
                raise RuntimeError("boom")
            return real(inp)

        text = _patch(*_update("models/orders.sql"), *_update("README.md"), *_update("models/customers.sql"))
        with patch.object(pre_edit_hook, "evaluate_pre_edit", side_effect=flaky):
            out = _run_pre(_pre_stdin(text, str(project), _session_files(tmp_path)), capsys)
        assert len(calls) == 3
        assert out["permissionDecision"] == "deny"
        assert "orders" in out["permissionDecisionReason"]
        assert "customers" in out["permissionDecisionReason"]

    def test_edit_tool_uses_file_path_even_with_input(self, project, tmp_path, capsys):
        """Dispatch is on tool_name: an edit call is gated by its file_path."""
        out = _run_pre(_pre_stdin(None, str(project), _session_files(tmp_path), tool_name="edit",
                                  tool_input={"file_path": str(project / "models" / "orders.sql"),
                                              "input": _patch(*_update("README.md"))}), capsys)
        assert out["permissionDecision"] == "deny"

    def test_edit_tool_ignores_patch_input(self, project, tmp_path, capsys):
        out = _run_pre(_pre_stdin(None, str(project), _session_files(tmp_path), tool_name="edit",
                                  tool_input={"file_path": str(project / "README.md"),
                                              "input": _patch(*_update("models/orders.sql"))}), capsys)
        assert out is None

    def test_disable_switch(self, project, tmp_path, capsys, monkeypatch):
        monkeypatch.setenv("MC_PREVENT_HOOKS_DISABLED", "1")
        assert _run_pre(_pre_stdin(_patch(*_update("models/orders.sql")), str(project),
                                   _session_files(tmp_path)), capsys) is None


# --- Post-edit tracking ---

class TestPostEditApplyPatch:
    def _patch(self):
        return _patch(*_update("models/orders.sql"),
                      "*** Update File: models/customers.sql", "*** Move to: models/clients.sql",
                      *_update("models/schema.yml"), *_update("README.md"))

    def test_success_tracks_every_dbt_file(self, project, tmp_path, capsys):
        cache.mark_impact_check_verified(SESSION, "orders")
        cache.mark_impact_check_verified(SESSION, "customers")
        (project / "models" / "schema.yml").write_text("version: 2\n")
        assert _run_pre(_pre_stdin(self._patch(), str(project), _session_files(tmp_path)), capsys) is None
        (project / "models" / "customers.sql").rename(project / "models" / "clients.sql")
        _run_post(_post_stdin(self._patch(), str(project), "Applied 4 operation(s) (3 added, 3 removed) across 5 file(s)."))
        assert sorted(cache.get_edited_tables(SESSION)) == ["clients", "customers", "orders", "schema"]

    def test_parse_error_tracks_nothing(self, project):
        _run_post(_post_stdin(self._patch(), str(project), "Error parsing apply_patch input: bad hunk"))
        assert cache.get_edited_tables(SESSION) == []

    def test_added_model_tracked(self, project):
        (project / "models" / "brand_new.sql").write_text(MODEL_SQL)
        _run_post(_post_stdin(_patch("*** Add File: models/brand_new.sql", "+select 1"), str(project),
                              "Applied 1 operation(s)."))
        assert cache.get_edited_tables(SESSION) == ["brand_new"]

    def test_deleted_model_tracked(self, project, tmp_path, capsys):
        cache.mark_impact_check_verified(SESSION, "orders")
        text = _patch("*** Delete File: models/orders.sql")
        assert _run_pre(_pre_stdin(text, str(project), _session_files(tmp_path)), capsys) is None
        (project / "models" / "orders.sql").unlink()
        _run_post(_post_stdin(text, str(project), "Applied 1 operation(s)."))
        assert cache.get_edited_tables(SESSION) == ["orders"]

    def test_deleted_model_without_a_pre_record_tracked_by_its_assessment(self, project):
        """Without the pre hook's record, a gone file whose table was assessed this session
        was gated as a model, so it still counts."""
        cache.mark_impact_check_verified(SESSION, "orders")
        (project / "models" / "orders.sql").unlink()
        _run_post(_post_stdin(_patch("*** Delete File: models/orders.sql"), str(project), "Applied 1 operation(s)."))
        assert cache.get_edited_tables(SESSION) == ["orders"]

    def test_moved_model_with_an_unmatched_call_id_tracked_by_its_assessment(self, project, tmp_path, capsys):
        cache.mark_impact_check_verified(SESSION, "orders")
        text = _patch("*** Update File: models/orders.sql", "*** Move to: models/orders_v2.sql")
        assert _run_pre(_pre_stdin(text, str(project), _session_files(tmp_path)), capsys) is None
        (project / "models" / "orders.sql").rename(project / "models" / "orders_v2.sql")
        stdin = json.loads(_post_stdin(text, str(project), "Applied 1 operation(s)."))
        stdin["tool_use_id"] = "call_other"
        _run_post(json.dumps(stdin))
        assert sorted(cache.get_edited_tables(SESSION)) == ["orders", "orders_v2"]

    def test_deleted_model_without_a_pre_record_or_assessment_not_tracked(self, project):
        """Without the record or an assessment, a file that is gone can't be told from plain SQL."""
        (project / "models" / "orders.sql").unlink()
        _run_post(_post_stdin(_patch("*** Delete File: models/orders.sql"), str(project), "Applied 1 operation(s)."))
        assert cache.get_edited_tables(SESSION) == []

    def test_deleted_non_model_with_an_assessed_stem_not_tracked(self, project):
        cache.mark_impact_check_verified(SESSION, "orders")
        _run_post(_post_stdin(_patch("*** Delete File: docs/orders.sql"), str(project), "Applied 1 operation(s)."))
        assert cache.get_edited_tables(SESSION) == []

    def test_plain_sql_written_over_a_model_tracked(self, project, tmp_path, capsys):
        cache.mark_impact_check_verified(SESSION, "orders")
        text = _patch("*** Add File: models/orders.sql", "+select 1")
        assert _run_pre(_pre_stdin(text, str(project), _session_files(tmp_path)), capsys) is None
        (project / "models" / "orders.sql").write_text("select 1\n")
        _run_post(_post_stdin(text, str(project), "Applied 1 operation(s)."))
        assert cache.get_edited_tables(SESSION) == ["orders"]

    def test_same_stem_file_with_old_state_not_tracked(self, project, tmp_path, capsys):
        """Impact state is per table name; a non-model file sharing the stem doesn't count."""
        cache.mark_impact_check_verified(SESSION, "orders")
        (project / "docs").mkdir()
        text = _patch("*** Add File: docs/orders.sql", "+select 1")
        assert _run_pre(_pre_stdin(text, str(project), _session_files(tmp_path)), capsys) is None
        (project / "docs" / "orders.sql").write_text("select 1\n")
        _run_post(_post_stdin(text, str(project), "Applied 1 operation(s)."))
        assert cache.get_edited_tables(SESSION) == []

    def test_deleted_schema_yaml_tracked(self, project, tmp_path, capsys):
        (project / "models" / "schema.yml").write_text("version: 2\n")
        text = _patch("*** Delete File: models/schema.yml")
        assert _run_pre(_pre_stdin(text, str(project), _session_files(tmp_path)), capsys) is None
        (project / "models" / "schema.yml").unlink()
        _run_post(_post_stdin(text, str(project), "Applied 1 operation(s)."))
        assert cache.get_edited_tables(SESSION) == ["schema"]

    def test_deleted_plain_sql_not_tracked(self, project):
        """A .sql file with no dbt constructs isn't gated; once it's gone it must not be
        tracked as a changed model."""
        (project / "models" / "plain.sql").write_text("select 1\n")
        (project / "models" / "plain.sql").unlink()
        _run_post(_post_stdin(_patch("*** Delete File: models/plain.sql"), str(project), "Applied 1 operation(s)."))
        assert cache.get_edited_tables(SESSION) == []

    def test_moved_away_plain_sql_not_tracked(self, project):
        (project / "models" / "plain.sql").write_text("select 1\n")
        (project / "models" / "plain.sql").rename(project / "models" / "plain2.sql")
        _run_post(_post_stdin(_patch("*** Update File: models/plain.sql", "*** Move to: models/plain2.sql"),
                              str(project), "Applied 1 operation(s)."))
        assert cache.get_edited_tables(SESSION) == []

    def test_partial_failure_tracks_completed_operations(self, project, tmp_path, capsys):
        cache.mark_impact_check_verified(SESSION, "orders")
        cache.mark_impact_check_verified(SESSION, "customers")
        assert _run_pre(_pre_stdin(self._patch(), str(project), _session_files(tmp_path)), capsys) is None
        (project / "models" / "customers.sql").rename(project / "models" / "clients.sql")
        _run_post(_post_stdin(self._patch(), str(project),
                              "Error: Patch partially applied through operation 3/4: context not found"))
        assert sorted(cache.get_edited_tables(SESSION)) == ["clients", "customers", "orders"]

    def test_relative_paths_resolved_against_cwd(self, project, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _run_post(_post_stdin(_patch(*_update("models/orders.sql")), str(project), "Applied 1 operation(s)."))
        assert cache.get_edited_tables(SESSION) == ["orders"]

    def test_edit_tool_still_tracks_file_path(self, project):
        stdin = json.dumps({"session_id": SESSION, "hook_event_name": "PostToolUse", "tool_name": "edit",
                            "tool_input": {"file_path": str(project / "models" / "orders.sql"),
                                           "input": _patch(*_update("models/customers.sql"))}})
        _run_post(stdin)
        assert cache.get_edited_tables(SESSION) == ["orders"]
