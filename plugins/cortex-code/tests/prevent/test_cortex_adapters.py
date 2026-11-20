"""Cortex adapter tests for post_edit, pre_commit, turn_end — JSON I/O format only
(business logic is covered by plugins/shared/prevent/lib/tests)."""
import json
import os
import subprocess
import sys

import pytest
from unittest.mock import patch
from io import StringIO

import lib.cache as cache
import lib.protocol as protocol


def _stdin(**kw):
    base = {"session_id": "test_session"}
    base.update(kw)
    return json.dumps(base)


class TestPostEditCortexAdapter:
    def test_tracks_dbt_model(self, tmp_path):
        models = tmp_path / "models"
        models.mkdir()
        sql = models / "orders.sql"
        sql.write_text("SELECT * FROM {{ ref('raw') }}")
        stdin = _stdin(tool_input={"file_path": str(sql)},
                       hook_event_name="PostToolUse", tool_name="write")
        with patch("sys.stdin", StringIO(stdin)):
            from post_edit_hook import main
            main()
        assert cache.get_edited_tables("test_session") == ["orders"]


DBT_SQL = "select * from {{ ref('raw_orders') }}\n"
HOOKS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "hooks", "prevent"))


def _git(repo, *args):
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


@pytest.fixture
def staged_repo(tmp_path):
    """A repo with models/orders.sql staged and `orders` verified for test_session."""
    repo = tmp_path / "repo"
    (repo / "models").mkdir(parents=True)
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.name", "Test")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "commit.gpgsign", "false")
    (repo / "README.md").write_text("hi\n")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-q", "-m", "init")
    (repo / "models" / "orders.sql").write_text(DBT_SQL)
    _git(repo, "add", "models/orders.sql")
    cache.mark_impact_check_injected("test_session", "orders")
    cache.mark_impact_check_verified("test_session", "orders")
    return repo


class TestPreCommitCortexAdapter:
    """Both CoCo Desktop and the CLI drop a PreToolUse hook's additionalContext,
    so the checkpoint is delivered as a one-time deny on both."""

    def _run(self, capsys, stdin):
        with patch("sys.stdin", StringIO(stdin)):
            from pre_commit_hook import main
            main()
        return capsys.readouterr().out

    @pytest.mark.parametrize("tool_name", ["bash", "Bash"])
    def test_first_commit_is_denied_with_the_checkpoint(self, capsys, staged_repo, tool_name):
        out = self._run(capsys, _stdin(
            tool_input={"command": "git commit -m x"}, cwd=str(staged_repo),
            hook_event_name="PreToolUse", tool_name=tool_name,
        ))
        payload = json.loads(out)
        reason = payload["hookSpecificOutput"]["permissionDecisionReason"]
        assert payload == {"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }}
        assert reason.startswith("Monte Carlo Prevent paused this commit once.")
        assert "orders" in reason

    def test_retry_prints_nothing(self, capsys, staged_repo):
        stdin = _stdin(tool_input={"command": "git commit -m x"}, cwd=str(staged_repo),
                       hook_event_name="PreToolUse", tool_name="bash")
        assert self._run(capsys, stdin)
        import sys
        sys.modules.pop("pre_commit_hook", None)
        assert self._run(capsys, stdin) == ""

    @pytest.mark.parametrize("session", [None, ""])
    def test_missing_session_id_prints_nothing(self, capsys, staged_repo, session):
        # A shared fallback ID would mix state across sessions; even if that
        # state says verified, a missing ID must stay silent.
        cache.mark_impact_check_verified("unknown", "orders")
        raw = {"tool_input": {"command": "git commit -m x"}, "cwd": str(staged_repo),
               "hook_event_name": "PreToolUse", "tool_name": "bash"}
        if session is not None:
            raw["session_id"] = session
        assert self._run(capsys, json.dumps(raw)) == ""
        assert not [f for f in os.listdir(cache.CACHE_DIR) if f.startswith(cache.COMMITCP_PREFIX)]

    def test_non_commit_prints_nothing(self, capsys, staged_repo):
        assert self._run(capsys, _stdin(
            tool_input={"command": "git status"}, cwd=str(staged_repo),
            hook_event_name="PreToolUse", tool_name="bash",
        )) == ""

    def test_published_hook_as_a_process(self, staged_repo):
        """Run the hook file the way Cortex does: a separate python3 reading stdin."""
        runner = (
            "import runpy, sys\n"
            f"sys.path.insert(0, {HOOKS_DIR!r})\n"
            "import lib.cache\n"
            f"lib.cache.CACHE_DIR = {cache.CACHE_DIR!r}\n"
            f"runpy.run_path({os.path.join(HOOKS_DIR, 'pre_commit_hook.py')!r}, run_name='__main__')\n"
        )
        stdin = _stdin(tool_input={"command": "git commit -m x"}, cwd=str(staged_repo),
                       hook_event_name="PreToolUse", tool_name="bash")

        def run():
            return subprocess.run([sys.executable, "-c", runner], input=stdin,
                                  capture_output=True, text=True, timeout=30)

        first, second = run(), run()
        assert first.returncode == 0 and second.returncode == 0
        assert json.loads(first.stdout)["hookSpecificOutput"]["permissionDecision"] == "deny"
        assert second.stdout == ""


class TestTurnEndCortexAdapter:
    def test_block_output_format(self, capsys):
        cache.add_edited_table("test_session", "orders")
        cache.mark_impact_check_verified("test_session", "orders")
        stdin = _stdin(stop_hook_active=False, hook_event_name="Stop")
        with patch("sys.stdin", StringIO(stdin)):
            from turn_end_hook import main
            main()
        out = json.loads(capsys.readouterr().out)
        assert out["decision"] == "block"
        assert "orders" in out["reason"]

    def test_stop_hook_active_is_silent(self, capsys):
        cache.add_edited_table("test_session", "orders")
        cache.mark_impact_check_verified("test_session", "orders")
        stdin = _stdin(stop_hook_active=True, hook_event_name="Stop")
        with patch("sys.stdin", StringIO(stdin)):
            from turn_end_hook import main
            main()
        assert capsys.readouterr().out == ""
