"""CC adapter tests for pre_edit_hook — tests JSON format, plus one end-to-end gating case."""
import json
import os
import pytest
from unittest.mock import patch, MagicMock
from io import StringIO

from lib.protocol import HookOutput


def _make_stdin(file_path):
    return json.dumps({
        "session_id": "test_session",
        "transcript_path": "/tmp/test_transcript.jsonl",
        "cwd": "/project",
        "hook_event_name": "PreToolUse",
        "tool_name": "Edit",
        "tool_input": {"file_path": file_path},
        "tool_use_id": "toolu_test123",
    })


class TestPreEditHookCCAdapter:
    def test_deny_output_format(self, capsys):
        """Deny result should produce CC-formatted JSON."""
        deny_result = HookOutput(action="deny", reason="blocked for testing")
        with patch("pre_edit_hook.evaluate_pre_edit", return_value=deny_result), \
             patch("sys.stdin", StringIO(_make_stdin("/project/models/orders.sql"))):
            from pre_edit_hook import main
            main()

        output = json.loads(capsys.readouterr().out)
        assert output["hookSpecificOutput"]["hookEventName"] == "PreToolUse"
        assert output["hookSpecificOutput"]["permissionDecision"] == "deny"
        assert output["hookSpecificOutput"]["permissionDecisionReason"] == "blocked for testing"

    def test_noop_output_silent(self, capsys):
        """Noop result should produce no output."""
        noop_result = HookOutput(action="noop")
        with patch("pre_edit_hook.evaluate_pre_edit", return_value=noop_result), \
             patch("sys.stdin", StringIO(_make_stdin("/project/models/orders.sql"))):
            from pre_edit_hook import main
            main()

        assert capsys.readouterr().out == ""

    def test_session_id_extracted(self):
        """Adapter should extract session_id from CC JSON."""
        raw = json.loads(_make_stdin("/project/models/orders.sql"))
        assert raw["session_id"] == "test_session"

    def test_file_path_extracted(self):
        """Adapter should extract file_path from tool_input."""
        raw = json.loads(_make_stdin("/project/models/orders.sql"))
        assert raw["tool_input"]["file_path"] == "/project/models/orders.sql"


class TestPreEditHookNestedDbtProjects:
    """End to end through the adapter: a stray dbt_project.yml inside models/ must not
    let an edit to an outer project's model through."""

    @pytest.mark.parametrize("rel", [("top.sql",), ("staging", "stg.sql")])
    def test_model_below_a_stray_inner_project_is_denied(self, tmp_path, capsys, monkeypatch, rel):
        monkeypatch.delenv("MC_PREVENT_HOOKS_DISABLED", raising=False)
        outer = tmp_path / "outer"
        (outer / "models").mkdir(parents=True)
        (outer / "dbt_project.yml").write_text("name: outer\n")
        (outer / "models" / "dbt_project.yml").write_text("name: inner\n")
        model = outer.joinpath("models", *rel)
        model.parent.mkdir(parents=True, exist_ok=True)
        model.write_text("SELECT * FROM {{ ref('raw') }}")

        with patch("sys.stdin", StringIO(_make_stdin(str(model)))):
            from pre_edit_hook import main
            main()

        output = json.loads(capsys.readouterr().out)
        assert output["hookSpecificOutput"]["permissionDecision"] == "deny"
        name = os.path.splitext(rel[-1])[0]
        assert f"for {name} before editing" in output["hookSpecificOutput"]["permissionDecisionReason"]
