"""Codex adapter tests for bash_hook — unified Bash PreToolUse handler."""
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


APPLY_PATCH_CMD = (
    "apply_patch <<'PATCH'\n"
    "*** Begin Patch\n"
    "*** Update File: analytics/models/clients/client_hub.sql\n"
    "@@\n"
    " SELECT accounts.created_on\n"
    "+       ,TRUE AS is_active_client\n"
    "*** End Patch"
)

APPLY_PATCH_WITH_CD = (
    "cd /Users/achen/src/dbt && apply_patch <<'PATCH'\n"
    "*** Begin Patch\n"
    "*** Update File: analytics/models/clients/client_hub.sql\n"
    "@@\n"
    " SELECT accounts.created_on\n"
    "+       ,TRUE AS is_active_client\n"
    "*** End Patch"
)

APPLY_PATCH_MULTI = (
    "apply_patch <<'PATCH'\n"
    "*** Begin Patch\n"
    "*** Update File: analytics/models/clients/client_hub.sql\n"
    "@@\n"
    "+  ,TRUE AS is_active_client\n"
    "*** Update File: analytics/models/clients/schema.yml\n"
    "@@\n"
    "+      - name: is_active_client\n"
    "*** End Patch"
)


class TestBashHookApplyPatch:
    def test_deny_blocks_patch(self, capsys):
        """apply_patch with a dbt model should deny if no impact assessment."""
        deny_result = HookOutput(action="deny", reason="Run impact assessment first")
        noop_result = HookOutput(action="noop")
        with patch("bash_hook.evaluate_pre_edit", return_value=deny_result), \
             patch("bash_hook.evaluate_post_edit", return_value=noop_result), \
             patch("sys.stdin", StringIO(_make_stdin(APPLY_PATCH_CMD))):
            from bash_hook import main
            main()

        output = json.loads(capsys.readouterr().out)
        assert output["hookSpecificOutput"]["permissionDecision"] == "deny"
        assert "impact assessment" in output["hookSpecificOutput"]["permissionDecisionReason"]

    def test_noop_tracks_edit(self, capsys):
        """apply_patch allowed by pre_edit should track via post_edit."""
        noop_result = HookOutput(action="noop")
        with patch("bash_hook.evaluate_pre_edit", return_value=noop_result) as mock_pre, \
             patch("bash_hook.evaluate_post_edit") as mock_post, \
             patch("sys.stdin", StringIO(_make_stdin(APPLY_PATCH_CMD))):
            from bash_hook import main
            main()

        # pre_edit and post_edit both called
        assert mock_pre.called
        assert mock_post.called
        # Silent output
        assert capsys.readouterr().out == ""

    def test_multi_file_patch_extracts_both(self, capsys):
        """apply_patch with multiple files should check each one."""
        noop_result = HookOutput(action="noop")
        with patch("bash_hook.evaluate_pre_edit", return_value=noop_result) as mock_pre, \
             patch("bash_hook.evaluate_post_edit") as mock_post, \
             patch("sys.stdin", StringIO(_make_stdin(APPLY_PATCH_MULTI))):
            from bash_hook import main
            main()

        assert mock_pre.call_count == 2
        assert mock_post.call_count == 2

    def test_deny_on_second_file_blocks(self, capsys):
        """If second file in multi-file patch is denied, the whole patch is blocked."""
        noop_result = HookOutput(action="noop")
        deny_result = HookOutput(action="deny", reason="blocked")
        results = [noop_result, deny_result]
        with patch("bash_hook.evaluate_pre_edit", side_effect=results), \
             patch("bash_hook.evaluate_post_edit"), \
             patch("sys.stdin", StringIO(_make_stdin(APPLY_PATCH_MULTI))):
            from bash_hook import main
            main()

        output = json.loads(capsys.readouterr().out)
        assert output["hookSpecificOutput"]["permissionDecision"] == "deny"


    def test_cd_prefixed_apply_patch(self, capsys):
        """apply_patch prefixed with cd should still be detected."""
        deny_result = HookOutput(action="deny", reason="Run impact assessment first")
        with patch("bash_hook.evaluate_pre_edit", return_value=deny_result), \
             patch("bash_hook.evaluate_post_edit"), \
             patch("sys.stdin", StringIO(_make_stdin(APPLY_PATCH_WITH_CD))):
            from bash_hook import main
            main()

        output = json.loads(capsys.readouterr().out)
        assert output["hookSpecificOutput"]["permissionDecision"] == "deny"


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


class TestExtractPatchFiles:
    def test_single_file(self):
        from bash_hook import _extract_patch_files
        files = _extract_patch_files(APPLY_PATCH_CMD)
        assert files == ["analytics/models/clients/client_hub.sql"]

    def test_multi_file(self):
        from bash_hook import _extract_patch_files
        files = _extract_patch_files(APPLY_PATCH_MULTI)
        assert files == [
            "analytics/models/clients/client_hub.sql",
            "analytics/models/clients/schema.yml",
        ]

    def test_no_patch(self):
        from bash_hook import _extract_patch_files
        files = _extract_patch_files("git commit -m 'test'")
        assert files == []
