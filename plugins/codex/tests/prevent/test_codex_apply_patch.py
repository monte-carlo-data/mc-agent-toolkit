"""Codex `apply_patch` gating, against a real dbt project and the real gate.

Codex sends a patch two ways:
  - through the shell: PreToolUse `Bash`, `tool_input.command` is the shell command
    (`apply_patch <<'EOF' ... EOF`, maybe after `cd <dir> &&`), `cwd` is the command's
    working directory. No PostToolUse follows an intercepted patch, so the hook tracks the
    files itself once the whole command is allowed.
  - with its own tool (0.124.0+): PreToolUse and PostToolUse `apply_patch`,
    `tool_input.command` is the raw patch. PostToolUse is sent only on success.
"""
import json
import os
from io import StringIO
from unittest.mock import patch

import pytest

import lib.cache as cache

SESSION = "test_session"
MODEL_SQL = "SELECT * FROM {{ ref('raw') }}\n"


def _patch(*body):
    return "\n".join(["*** Begin Patch", *body, "*** End Patch"])


def _update(path, old="SELECT * FROM {{ ref('raw') }}", new="SELECT 1 FROM {{ ref('raw') }}"):
    return [f"*** Update File: {path}", "@@", f"-{old}", f"+{new}"]


def _shell(patch_text, prefix="", delim="'EOF'"):
    bare = delim.strip("'\"")
    return f"{prefix}apply_patch <<{delim}\n{patch_text}\n{bare}\n"


@pytest.fixture
def project(tmp_path):
    """A dbt project with two models, a macro, a plain SQL file and a README."""
    root = tmp_path / "proj"
    (root / "models").mkdir(parents=True)
    (root / "macros").mkdir()
    (root / "models" / "orders.sql").write_text(MODEL_SQL)
    (root / "models" / "customers.sql").write_text(MODEL_SQL)
    (root / "models" / "plain.sql").write_text("select 1\n")
    (root / "macros" / "internal_accounts.sql").write_text("{% macro internal_accounts() %} 1 {% endmacro %}\n")
    (root / "README.md").write_text("hello\n")
    return root


@pytest.fixture(autouse=True)
def elsewhere(tmp_path, monkeypatch):
    """Run the hook from a directory other than the payload cwd."""
    other = tmp_path / "elsewhere"
    other.mkdir()
    monkeypatch.chdir(other)
    return other


def _stdin(command, cwd, tool_name="Bash", event="PreToolUse", call_id="call_1"):
    return json.dumps({
        "session_id": SESSION,
        "transcript_path": "",
        "cwd": str(cwd),
        "hook_event_name": event,
        "tool_name": tool_name,
        "tool_input": {"command": command},
        "tool_use_id": call_id,
    })


def _run_pre(command, cwd, capsys, tool_name="Bash", call_id="call_1"):
    with patch("sys.stdin", StringIO(_stdin(command, cwd, tool_name, call_id=call_id))):
        from bash_hook import main
        main()
    out = capsys.readouterr().out
    return json.loads(out)["hookSpecificOutput"] if out else None


def _run_post(command, cwd, call_id="call_1"):
    with patch("sys.stdin", StringIO(_stdin(command, cwd, "apply_patch", "PostToolUse", call_id))):
        from post_edit_hook import main
        main()


def _denied(out):
    return out is not None and out.get("permissionDecision") == "deny"


def _edited():
    return sorted(cache.get_edited_tables(SESSION))


def _checked_paths(command, cwd, capsys, tool_name="Bash"):
    """The paths the hook hands to the gate, in order."""
    import bash_hook
    seen = []
    real = bash_hook.evaluate_pre_edit

    def spy(inp):
        seen.append(inp.file_path)
        return real(inp)

    with patch.object(bash_hook, "evaluate_pre_edit", side_effect=spy):
        _run_pre(command, cwd, capsys, tool_name)
    return seen


# --- Shell: each operation on its own ---

class TestShellOperations:
    def test_update_existing_model_denied(self, project, capsys):
        out = _run_pre(_shell(_patch(*_update("models/orders.sql"))), project, capsys)
        assert _denied(out) and "orders" in out["permissionDecisionReason"]

    def test_add_over_existing_model_denied(self, project, capsys):
        out = _run_pre(_shell(_patch("*** Add File: models/orders.sql", "+select 1")), project, capsys)
        assert _denied(out) and "orders" in out["permissionDecisionReason"]

    def test_delete_existing_model_denied(self, project, capsys):
        out = _run_pre(_shell(_patch("*** Delete File: models/orders.sql")), project, capsys)
        assert _denied(out) and "orders" in out["permissionDecisionReason"]

    def test_move_model_to_free_name_denied(self, project, capsys):
        text = _patch("*** Update File: models/orders.sql", "*** Move to: models/orders_v2.sql",
                      *_update("models/orders.sql")[1:])
        out = _run_pre(_shell(text), project, capsys)
        assert _denied(out) and "orders" in out["permissionDecisionReason"]

    def test_move_plain_file_onto_existing_model_denied(self, project, capsys):
        text = _patch("*** Update File: README.md", "*** Move to: models/customers.sql", "@@", "-hello", "+hi")
        out = _run_pre(_shell(text), project, capsys)
        assert _denied(out) and "customers" in out["permissionDecisionReason"]

    def test_add_new_model_allowed_and_tracked(self, project, capsys):
        out = _run_pre(_shell(_patch("*** Add File: models/brand_new.sql", "+select 1")), project, capsys)
        assert out is None
        assert _edited() == ["brand_new"]

    def test_non_dbt_patch_allowed_and_not_tracked(self, project, capsys):
        out = _run_pre(_shell(_patch("*** Update File: README.md", "@@", "-hello", "+hi")), project, capsys)
        assert out is None
        assert _edited() == []

    def test_applypatch_spelling(self, project, capsys):
        cmd = _shell(_patch(*_update("models/orders.sql"))).replace("apply_patch", "applypatch", 1)
        assert _denied(_run_pre(cmd, project, capsys))

    def test_unquoted_delimiter_without_expansions(self, project, capsys):
        assert _denied(_run_pre(_shell(_patch("*** Delete File: models/orders.sql"), delim="EOF"), project, capsys))

    def test_dash_heredoc_with_tabs(self, project, capsys):
        body = "\n".join("\t" + line for line in _patch("*** Delete File: models/orders.sql").split("\n"))
        cmd = f"apply_patch <<-'EOF'\n{body}\n\tEOF\n"
        assert _denied(_run_pre(cmd, project, capsys))


# --- Shell: the whole patch is one decision ---

class TestShellWholePatch:
    def test_second_file_denied_tracks_nothing(self, project, capsys):
        cache.add_edited_table(SESSION, "unrelated")
        text = _patch("*** Add File: models/brand_new.sql", "+select 1", *_update("models/orders.sql"))
        out = _run_pre(_shell(text), project, capsys)
        assert _denied(out)
        assert _edited() == ["unrelated"]

    def test_two_unassessed_models_one_deny(self, project, capsys):
        text = _patch(*_update("models/orders.sql"), *_update("models/customers.sql"))
        out = _run_pre(_shell(text), project, capsys)
        reason = out["permissionDecisionReason"]
        assert "orders" in reason and "customers" in reason
        assert cache.get_impact_check_state(SESSION, "orders") == "injected"
        assert cache.get_impact_check_state(SESSION, "customers") == "injected"
        assert _edited() == []

    def test_two_invocations_second_denied_tracks_nothing(self, project, capsys):
        first = _shell(_patch("*** Add File: models/brand_new.sql", "+select 1"))
        second = _shell(_patch(*_update("models/orders.sql")))
        out = _run_pre(first + second, project, capsys)
        assert _denied(out) and "orders" in out["permissionDecisionReason"]
        assert _edited() == []

    def test_allowed_patch_tracks_every_dbt_path(self, project, capsys):
        cache.mark_impact_check_verified(SESSION, "orders")
        cache.mark_impact_check_verified(SESSION, "customers")
        (project / "models" / "schema.yml").write_text("version: 2\n")
        text = _patch(*_update("models/orders.sql"),
                      "*** Update File: models/customers.sql", "*** Move to: models/clients.sql",
                      *_update("models/customers.sql")[1:],
                      "*** Update File: models/schema.yml", "@@", "-version: 2", "+version: 2 ",
                      "*** Update File: README.md", "@@", "-hello", "+hi")
        assert _run_pre(_shell(text), project, capsys) is None
        assert _edited() == ["clients", "customers", "orders", "schema"]

    def test_header_text_inside_a_hunk_is_not_a_header(self, project, capsys):
        text = _patch("*** Update File: README.md", "@@", "-hello", "+ *** Delete File: models/orders.sql")
        paths = _checked_paths(_shell(text), project, capsys)
        assert paths == [str(project / "README.md")]


# --- Shell: which directory a patch applies in ---

class TestShellDirectory:
    @pytest.fixture
    def nested(self, project, tmp_path):
        """A second dbt project under the payload cwd, holding a same-named model."""
        outer = tmp_path / "outer"
        (outer / "my dbt" / "models").mkdir(parents=True)
        (outer / "my dbt" / "models" / "orders.sql").write_text(MODEL_SQL)
        (outer / "dbt" / "models").mkdir(parents=True)
        (outer / "dbt" / "models" / "orders.sql").write_text(MODEL_SQL)
        return outer

    def test_no_cd_uses_payload_cwd(self, project, capsys):
        paths = _checked_paths(_shell(_patch(*_update("models/orders.sql"))), project, capsys)
        assert paths == [str(project / "models" / "orders.sql")]

    @pytest.mark.parametrize("arg,sub", [("dbt", "dbt"), ('"my dbt"', "my dbt"), ("'my dbt'", "my dbt")])
    def test_cd_prefix_resolved(self, nested, capsys, arg, sub):
        cmd = _shell(_patch(*_update("models/orders.sql")), prefix=f"cd {arg} && ")
        assert _checked_paths(cmd, nested, capsys) == [str(nested / sub / "models" / "orders.sql")]

    def test_absolute_cd(self, project, nested, capsys):
        cmd = _shell(_patch(*_update("models/orders.sql")), prefix=f"cd {project} && ")
        assert _checked_paths(cmd, nested, capsys) == [str(project / "models" / "orders.sql")]

    def test_absolute_patch_path_kept(self, project, nested, capsys):
        cmd = _shell(_patch(*_update(str(project / "models" / "orders.sql"))), prefix="cd dbt && ")
        assert _checked_paths(cmd, nested, capsys) == [str(project / "models" / "orders.sql")]


# --- Paths through symlinks ---

class TestSymlinks:
    """The dbt classifier reads folder names in the path, so a path through a link is
    also checked as the file it reaches."""

    @pytest.fixture
    def linked(self, project):
        (project / "dbtlink").symlink_to(project / "models", target_is_directory=True)
        (project / "notes").mkdir()
        (project / "notes" / "orders.sql").symlink_to(project / "models" / "orders.sql")
        return project

    def test_update_through_linked_folder_denied(self, linked, capsys):
        out = _run_pre(_shell(_patch(*_update("dbtlink/orders.sql"))), linked, capsys)
        assert _denied(out) and "orders" in out["permissionDecisionReason"]

    def test_update_through_linked_file_denied(self, linked, capsys):
        out = _run_pre(_shell(_patch(*_update("notes/orders.sql"))), linked, capsys)
        assert _denied(out) and "orders" in out["permissionDecisionReason"]

    def test_one_linked_file_keeps_the_plain_reason(self, linked, capsys):
        reason = _run_pre(_shell(_patch(*_update("dbtlink/orders.sql"))), linked, capsys)["permissionDecisionReason"]
        assert reason.startswith("Monte Carlo Prevent: run the change impact assessment for orders")

    def test_native_update_through_linked_folder_denied(self, linked, capsys):
        out = _run_pre(_patch(*_update("dbtlink/orders.sql")), linked, capsys, tool_name="apply_patch")
        assert _denied(out)

    def test_new_model_through_linked_folder_tracked(self, linked, capsys):
        assert _run_pre(_shell(_patch("*** Add File: dbtlink/brand_new.sql", "+select 1")), linked, capsys) is None
        assert _edited() == ["brand_new"]

    def test_native_post_tracks_new_model_through_linked_folder(self, linked, capsys):
        text = _patch("*** Add File: dbtlink/brand_new.sql", "+SELECT * FROM {{ ref('raw') }}")
        assert _run_pre(text, linked, capsys, tool_name="apply_patch") is None
        (linked / "models" / "brand_new.sql").write_text(MODEL_SQL)
        _run_post(text, linked)
        assert _edited() == ["brand_new"]

    def test_native_post_tracks_through_linked_folder(self, linked, capsys):
        cache.mark_impact_check_verified(SESSION, "orders")
        text = _patch("*** Delete File: dbtlink/orders.sql")
        assert _run_pre(text, linked, capsys, tool_name="apply_patch") is None
        (linked / "models" / "orders.sql").unlink()
        _run_post(text, linked)
        assert _edited() == ["orders"]


# --- Shell: forms the hook can't resolve (D5) ---

class TestShellUnresolved:
    @pytest.mark.parametrize("prefix", [
        "cd dbt; ",
        "cd dbt && cd models && ",
        "false && cd dbt; ",
        'cd "$DBT_DIR" && ',
        'cd "a"$B && ',
        "cd ~/dbt && ",
        "cd - && ",
        "pushd dbt && ",
    ])
    def test_unknown_directory_with_sql_denied(self, project, capsys, prefix):
        out = _run_pre(_shell(_patch(*_update("models/orders.sql")), prefix=prefix), project, capsys)
        assert _denied(out)
        assert "couldn't check" in out["permissionDecisionReason"]

    def test_subshell_cd_denied(self, project, capsys):
        cmd = "(cd dbt && " + _shell(_patch(*_update("models/orders.sql"))).rstrip("\n") + "\n)"
        assert _denied(_run_pre(cmd, project, capsys))

    def test_unknown_directory_yaml_denied(self, project, capsys):
        text = _patch("*** Update File: models/schema.YML", "@@", "-a", "+b")
        assert _denied(_run_pre(_shell(text, prefix="cd dbt; "), project, capsys))

    def test_unknown_directory_move_to_sql_denied(self, project, capsys):
        text = _patch("*** Update File: notes.md", "*** Move to: models/orders.sql", "@@", "-a", "+b")
        assert _denied(_run_pre(_shell(text, prefix="cd dbt; "), project, capsys))

    def test_unknown_directory_markdown_only_allowed(self, project, capsys):
        text = _patch("*** Update File: README.md", "@@", "-hello", "+hi")
        assert _run_pre(_shell(text, prefix="cd dbt; "), project, capsys) is None
        assert _edited() == []

    @pytest.mark.parametrize("cmd", [
        "apply_patch < /tmp/p.diff",
        'apply_patch "$(cat /tmp/p.diff)"',
        "cat /tmp/p.diff | apply_patch",
        "apply_patch <<EOF\n*** Begin Patch\n*** Update File: $F\n@@\n-a\n+b\n*** End Patch\nEOF\n",
    ])
    def test_opaque_body_denied(self, project, capsys, cmd):
        out = _run_pre(cmd, project, capsys)
        assert _denied(out)
        assert "couldn't check" in out["permissionDecisionReason"]

    def test_disable_switch_suppresses_unresolved_deny(self, project, capsys, monkeypatch):
        monkeypatch.setenv("MC_PREVENT_HOOKS_DISABLED", "1")
        assert _run_pre("apply_patch < /tmp/p.diff", project, capsys) is None


# --- Shell: recognising an invocation ---

class TestShellRecognition:
    @pytest.mark.parametrize("prefix", ["FOO=1 ", "/usr/local/bin/", "command ", "exec "])
    def test_prefixed_invocation_gated(self, project, capsys, prefix):
        cmd = _shell(_patch(*_update("models/orders.sql")), prefix=prefix)
        assert _denied(_run_pre(cmd, project, capsys))

    @pytest.mark.parametrize("cmd", [
        "grep -rn apply_patch .",
        "echo 'run apply_patch <<EOF later'",
        "# apply_patch < x\nls",
        "cat > notes.md <<'EOF'\napply_patch <<'X'\n*** Begin Patch\n*** Delete File: models/orders.sql\n*** End Patch\nX\nEOF\n",
    ])
    def test_not_an_invocation(self, project, capsys, cmd):
        assert _run_pre(cmd, project, capsys) is None

    def test_git_commit_still_checked(self, project, capsys):
        from lib.protocol import HookOutput
        with patch("bash_hook.evaluate_pre_commit", return_value=HookOutput(action="context", context="ctx")):
            out = _run_pre("git commit -m 'x'", project, capsys)
        assert out["additionalContext"] == "ctx"


# --- Codex's own apply_patch tool ---

class TestNativeTool:
    def test_update_denied(self, project, capsys):
        out = _run_pre(_patch(*_update("models/orders.sql")), project, capsys, tool_name="apply_patch")
        assert _denied(out) and "orders" in out["permissionDecisionReason"]

    def test_both_move_endpoints_checked(self, project, capsys):
        text = _patch("*** Update File: README.md", "*** Move to: models/customers.sql", "@@", "-hello", "+hi")
        paths = _checked_paths(text, project, capsys, tool_name="apply_patch")
        assert paths == [str(project / "README.md"), str(project / "models" / "customers.sql")]

    def test_eof_wrapper(self, project, capsys):
        text = "<<'EOF'\n" + _patch("*** Delete File: models/orders.sql") + "\nEOF"
        assert _denied(_run_pre(text, project, capsys, tool_name="apply_patch"))

    def test_shell_text_in_hunk_does_not_change_directory(self, project, capsys):
        text = _patch("*** Update File: README.md", "@@", "-hello", "+cd /elsewhere && apply_patch <<'EOF'")
        assert _checked_paths(text, project, capsys, tool_name="apply_patch") == [str(project / "README.md")]

    def test_allowed_pre_tracks_nothing_until_post(self, project, capsys):
        text = _patch("*** Add File: models/brand_new.sql", "+select 1")
        assert _run_pre(text, project, capsys, tool_name="apply_patch") is None
        assert _edited() == []

    def test_post_tracks_applied_files(self, project, capsys):
        cache.mark_impact_check_verified(SESSION, "orders")
        cache.mark_impact_check_verified(SESSION, "customers")
        text = _patch(*_update("models/orders.sql"),
                      "*** Update File: models/customers.sql", "*** Move to: models/clients.sql",
                      *_update("models/customers.sql")[1:],
                      "*** Add File: models/brand_new.sql", "+SELECT * FROM {{ ref('raw') }}",
                      "*** Add File: models/new_plain.sql", "+select 1",
                      "*** Update File: README.md", "@@", "-hello", "+hi")
        assert _run_pre(text, project, capsys, tool_name="apply_patch") is None
        models = project / "models"
        (models / "customers.sql").rename(models / "clients.sql")
        (models / "brand_new.sql").write_text(MODEL_SQL)
        (models / "new_plain.sql").write_text("select 1\n")
        _run_post(text, project)
        assert _edited() == ["brand_new", "clients", "customers", "orders"]

    def test_post_tracks_deleted_model(self, project, capsys):
        cache.mark_impact_check_verified(SESSION, "orders")
        text = _patch("*** Delete File: models/orders.sql")
        assert _run_pre(text, project, capsys, tool_name="apply_patch") is None
        (project / "models" / "orders.sql").unlink()
        _run_post(text, project)
        assert _edited() == ["orders"]

    def test_post_tracks_plain_sql_written_over_model(self, project, capsys):
        cache.mark_impact_check_verified(SESSION, "orders")
        text = _patch("*** Add File: models/orders.sql", "+select 1")
        assert _run_pre(text, project, capsys, tool_name="apply_patch") is None
        (project / "models" / "orders.sql").write_text("select 1\n")
        _run_post(text, project)
        assert _edited() == ["orders"]

    def test_post_ignores_same_stem_file_with_old_state(self, project, capsys):
        """Impact state is per table name; a non-model file sharing the stem must not count."""
        cache.mark_impact_check_verified(SESSION, "orders")
        (project / "docs").mkdir()
        text = _patch("*** Add File: docs/orders.sql", "+select 1")
        assert _run_pre(text, project, capsys, tool_name="apply_patch") is None
        (project / "docs" / "orders.sql").write_text("select 1\n")
        _run_post(text, project)
        assert _edited() == []

    def test_post_tracks_deleted_schema_yaml(self, project, capsys):
        (project / "models" / "schema.yml").write_text("version: 2\n")
        text = _patch("*** Delete File: models/schema.yml")
        assert _run_pre(text, project, capsys, tool_name="apply_patch") is None
        (project / "models" / "schema.yml").unlink()
        _run_post(text, project)
        assert _edited() == ["schema"]

    def test_post_without_pre_record_tracks_existing_models_only(self, project):
        text = _patch(*_update("models/orders.sql"), "*** Delete File: models/customers.sql")
        (project / "models" / "customers.sql").unlink()
        _run_post(text, project)
        assert _edited() == ["orders"]

    def test_interleaved_calls_keep_their_own_records(self, project, capsys):
        cache.mark_impact_check_verified(SESSION, "orders")
        cache.mark_impact_check_verified(SESSION, "customers")
        a = _patch("*** Delete File: models/orders.sql")
        b = _patch("*** Delete File: models/customers.sql")
        assert _run_pre(a, project, capsys, tool_name="apply_patch", call_id="call_a") is None
        assert _run_pre(b, project, capsys, tool_name="apply_patch", call_id="call_b") is None
        (project / "models" / "customers.sql").unlink()
        _run_post(b, project, call_id="call_b")
        assert _edited() == ["customers"]
        # call_b's record is gone; replaying it doesn't add anything.
        (project / "models" / "orders.sql").unlink()
        _run_post(a, project, call_id="call_b")
        assert _edited() == ["customers"]
        _run_post(a, project, call_id="call_a")
        assert _edited() == ["customers", "orders"]

    def test_denied_pre_leaves_no_record(self, project, capsys):
        text = _patch("*** Delete File: models/orders.sql")
        assert _denied(_run_pre(text, project, capsys, tool_name="apply_patch"))
        assert not [n for n in os.listdir(cache.CACHE_DIR) if n.startswith(cache.PATCH_PREFIX)]

    def test_abandoned_record_is_swept(self, project, capsys, monkeypatch):
        cache.mark_impact_check_verified(SESSION, "orders")
        text = _patch("*** Delete File: models/orders.sql")
        assert _run_pre(text, project, capsys, tool_name="apply_patch") is None
        records = [n for n in os.listdir(cache.CACHE_DIR) if n.startswith(cache.PATCH_PREFIX)]
        assert len(records) == 1
        old = os.path.getmtime(os.path.join(cache.CACHE_DIR, records[0])) - cache.STALE_THRESHOLD_SECONDS - 10
        os.utime(os.path.join(cache.CACHE_DIR, records[0]), (old, old))
        os.remove(os.path.join(cache.CACHE_DIR, cache.CLEANUP_MARKER))  # the gate's own sweep just ran
        cache.cleanup_stale_cache()
        assert not [n for n in os.listdir(cache.CACHE_DIR) if n.startswith(cache.PATCH_PREFIX)]
