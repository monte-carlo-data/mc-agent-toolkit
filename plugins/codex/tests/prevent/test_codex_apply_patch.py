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


def _stdin(command, cwd, tool_name="Bash", event="PreToolUse", call_id="call_1", transcript_path=""):
    return json.dumps({
        "session_id": SESSION,
        "transcript_path": transcript_path,
        "cwd": str(cwd),
        "hook_event_name": event,
        "tool_name": tool_name,
        "tool_input": {"command": command},
        "tool_use_id": call_id,
    })


def _run_pre(command, cwd, capsys, tool_name="Bash", call_id="call_1", transcript_path=""):
    with patch("sys.stdin", StringIO(_stdin(command, cwd, tool_name, call_id=call_id,
                                            transcript_path=transcript_path))):
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


# --- Shell: forms the hook can't resolve ---

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

    def test_unknown_directory_names_one_reason(self, project, capsys):
        reason = _run_pre(_shell(_DELETE_ORDERS, prefix="cd dbt; "), project, capsys)["permissionDecisionReason"]
        assert "can't be known" in reason and "doesn't recognise" not in reason

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

    # Codex applies an intercepted heredoc as written, even with an unquoted delimiter, so
    # `$`, backticks and backslashes in hunk lines don't make it unreadable.
    def test_intercepted_unquoted_expansions_in_hunk_allowed(self, project, capsys):
        text = _patch("*** Update File: src/app.js", "@@", "-const s = 'a';",
                      "+const s = `${name}`;", "+print(\"a\\n\")")
        assert _run_pre(_shell(text, delim="EOF"), project, capsys) is None

    def test_intercepted_unquoted_expansions_in_hunk_still_gate_models(self, project, capsys):
        text = _patch(*_update("models/orders.sql", new="SELECT '$1' FROM {{ ref('raw') }}"))
        out = _run_pre(_shell(text, prefix="cd . && ", delim="EOF"), project, capsys)
        assert _denied(out)
        assert "orders" in out["permissionDecisionReason"]
        assert "couldn't check" not in out["permissionDecisionReason"]

    # Outside Codex's two forms a real shell expands the body: a backslash can only join
    # lines, but `$(...)` or `$VAR` could write new header lines.
    def test_shell_unquoted_backslash_only_allowed(self, project, capsys):
        text = _patch("*** Update File: src/app.py", "@@", "-x", "+print(\"a\\n\")")
        assert _run_pre(_shell(text, prefix="FOO=1 ", delim="EOF"), project, capsys) is None

    def test_shell_unquoted_dollar_in_hunk_denied(self, project, capsys):
        text = _patch("*** Update File: src/app.js", "@@", "-x", "+$(printf 'y')")
        out = _run_pre(_shell(text, prefix="FOO=1 ", delim="EOF"), project, capsys)
        assert _denied(out)
        assert "couldn't check" in out["permissionDecisionReason"]

    def test_shell_unquoted_backslash_joining_a_header_denied(self, project, capsys):
        # The shell joins these two lines into `*** Delete File: models/orders.sql`.
        text = _patch("**\\", "* Delete File: models/orders.sql")
        out = _run_pre(_shell(text, prefix="FOO=1 ", delim="EOF"), project, capsys)
        assert _denied(out)

    def test_disable_switch_suppresses_unresolved_deny(self, project, capsys, monkeypatch):
        monkeypatch.setenv("MC_PREVENT_HOOKS_DISABLED", "1")
        assert _run_pre("apply_patch < /tmp/p.diff", project, capsys) is None

    @pytest.mark.parametrize("cmd", [
        "env apply_patch <<'EOF'\n*** Begin Patch\n*** Delete File: models/orders.sql\n*** End Patch\nEOF\n",
        "bash -lc 'apply_patch <<EOF\n*** Begin Patch\n*** Delete File: models/orders.sql\n*** End Patch\nEOF'",
    ])
    def test_disable_switch_suppresses_unrecognised_call_deny(self, project, capsys, monkeypatch, cmd):
        monkeypatch.setenv("MC_PREVENT_HOOKS_DISABLED", "1")
        assert _run_pre(cmd, project, capsys) is None


# --- Shell: recognising an invocation ---

class TestShellRecognition:
    @pytest.mark.parametrize("prefix", ["FOO=1 ", "/usr/local/bin/", "command ", "exec "])
    def test_prefixed_invocation_gated(self, project, capsys, prefix):
        cmd = _shell(_patch(*_update("models/orders.sql")), prefix=prefix)
        out = _run_pre(cmd, project, capsys)
        assert _denied(out)
        assert "orders" in out["permissionDecisionReason"]
        assert "couldn't check" not in out["permissionDecisionReason"]

    def test_scanned_add_allowed_and_tracked(self, project, capsys):
        text = _patch("*** Add File: models/brand_new.sql", "+SELECT * FROM {{ ref('raw') }}")
        assert _run_pre(_shell(text, prefix="FOO=1 "), project, capsys) is None
        assert _edited() == ["brand_new"]

    @pytest.mark.parametrize("cmd", [
        "grep -rn apply_patch .",
        "echo 'run apply_patch <<EOF later'",
        "# apply_patch < x\nls",
        "cat > notes.md <<'EOF'\napply_patch <<'X'\n*** Begin Patch\n*** Update File: docs/a.md\n*** End Patch\nX\nEOF\n",
    ])
    def test_not_an_invocation(self, project, capsys, cmd):
        assert _run_pre(cmd, project, capsys) is None

    def test_model_patch_in_another_commands_heredoc_denied(self, project, capsys):
        """Text fed to another command may still run (`sh notes.md` later), so a patch in
        it that may change models is checked by path."""
        cmd = f"cat > notes.md <<'EOF'\napply_patch <<'X'\n{_patch('*** Delete File: models/orders.sql')}\nX\nEOF\n"
        out = _run_pre(cmd, project, capsys)
        assert _denied(out) and "couldn't check" in out["permissionDecisionReason"]

    def test_git_commit_still_checked(self, project, capsys):
        from lib.protocol import HookOutput
        with patch("bash_hook.evaluate_pre_commit", return_value=HookOutput(action="context", context="ctx")):
            out = _run_pre("git commit -m 'x'", project, capsys)
        assert out["additionalContext"] == "ctx"


# --- Shell: forms the scanner doesn't find, or resolves against the wrong folder ---

_DELETE_ORDERS = _patch("*** Delete File: models/orders.sql")
_DOCS_ONLY = _patch("*** Update File: docs/readme.md", "@@", "-a", "+b")


class TestShellFormsNotRecognised:
    def test_backslash_continuation_after_cd(self, project, capsys):
        text = _patch("*** Delete File: orders.sql")
        cmd = "cd models && \\\n" + _shell(text)
        out = _run_pre(cmd, project, capsys)
        assert _denied(out)
        assert "orders" in out["permissionDecisionReason"]
        assert "couldn't check" not in out["permissionDecisionReason"]

    def test_assignment_with_expansion(self, project, capsys):
        cmd = _shell(_DELETE_ORDERS, prefix='FOO="$(pwd)" ')
        out = _run_pre(cmd, project, capsys)
        assert _denied(out)
        assert "orders" in out["permissionDecisionReason"]
        assert "couldn't check" not in out["permissionDecisionReason"]

    @pytest.mark.parametrize("prefix", ["env ", "env FOO=1 ", "timeout 30 ", "nice -n 5 ", "nohup "])
    def test_wrapper_commands(self, project, capsys, prefix):
        assert _denied(_run_pre(_shell(_DELETE_ORDERS, prefix=prefix), project, capsys))

    def test_command_substitution(self, project, capsys):
        cmd = "out=$(" + _shell(_DELETE_ORDERS) + ")"
        assert _denied(_run_pre(cmd, project, capsys))

    @pytest.mark.parametrize("shell", ["bash -lc", "zsh -c"])
    def test_shell_argv_form(self, project, capsys, shell):
        script = f"apply_patch <<EOF\n{_DELETE_ORDERS}\nEOF"
        assert _denied(_run_pre(f"{shell} '{script}'", project, capsys))

    def test_heredoc_with_argument(self, project, capsys):
        cmd = _shell(_DOCS_ONLY).replace("apply_patch", 'apply_patch "$P"', 1)
        assert _denied(_run_pre(cmd, project, capsys))

    def test_heredoc_then_file_redirection(self, project, capsys):
        cmd = _shell(_DOCS_ONLY).replace("<<'EOF'", "<<'EOF' < other.patch", 1)
        assert _denied(_run_pre(cmd, project, capsys))

    def test_builtin_cd(self, project, capsys):
        text = _patch("*** Delete File: orders.sql")
        assert _denied(_run_pre(_shell(text, prefix="builtin cd models && "), project, capsys))

    @pytest.mark.parametrize("prefix", ["source env.sh && ", ". env.sh && "])
    def test_sourced_script(self, project, capsys, prefix):
        text = _patch("*** Delete File: orders.sql")
        assert _denied(_run_pre(_shell(text, prefix=prefix), project, capsys))

    def test_env_wrapper_docs_only_allowed(self, project, capsys):
        assert _run_pre(_shell(_DOCS_ONLY, prefix="env "), project, capsys) is None

    def test_mention_in_echo_allowed(self, project, capsys):
        assert _run_pre("echo apply_patch is a tool", project, capsys) is None


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

    def test_post_without_pre_record_tracks_deleted_assessed_model(self, project):
        cache.mark_impact_check_verified(SESSION, "orders")
        (project / "models" / "orders.sql").unlink()
        _run_post(_patch("*** Delete File: models/orders.sql"), project)
        assert _edited() == ["orders"]

    def test_post_with_unmatched_call_id_tracks_moved_assessed_model(self, project, capsys):
        cache.mark_impact_check_verified(SESSION, "orders")
        text = _patch("*** Update File: models/orders.sql", "*** Move to: models/orders_v2.sql")
        assert _run_pre(text, project, capsys, tool_name="apply_patch", call_id="call_a") is None
        (project / "models" / "orders.sql").rename(project / "models" / "orders_v2.sql")
        _run_post(text, project, call_id="call_b")
        assert _edited() == ["orders", "orders_v2"]

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
        # Only call_b's record was consumed.
        assert len([n for n in os.listdir(cache.CACHE_DIR) if n.startswith(cache.PATCH_PREFIX)]) == 1
        (project / "models" / "orders.sql").unlink()
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


# --- Shell: forms the scanner must not let slip past the gate ---

_ADD_NOTES = _patch("*** Add File: notes.txt", "+hi")


class TestShellScannerBypasses:
    @staticmethod
    def _denies_orders(command, project, capsys):
        out = _run_pre(command, project, capsys)
        assert _denied(out) and "orders" in out["permissionDecisionReason"]
        return out["permissionDecisionReason"]

    def test_recognised_call_then_env_call(self, project, capsys):
        """`env apply_patch` runs the tool, so it is gated even after a plain call."""
        cmd = (
            f"apply_patch <<'A'\n{_ADD_NOTES}\nA\n"
            f"env apply_patch <<'B'\n{_DELETE_ORDERS}\nB\n"
        )
        self._denies_orders(cmd, project, capsys)

    def test_two_env_calls(self, project, capsys):
        """Every `env apply_patch` heredoc is gated, not only the first."""
        cmd = (
            f"env apply_patch <<'A'\n{_ADD_NOTES}\nA\n"
            f"env apply_patch <<'B'\n{_DELETE_ORDERS}\nB\n"
        )
        self._denies_orders(cmd, project, capsys)

    def test_apply_patch_inside_bash_heredoc(self, project, capsys):
        """A heredoc fed to `bash` is a script that runs apply_patch."""
        cmd = f"bash <<'EOF'\napply_patch <<'P'\n{_DELETE_ORDERS}\nP\nEOF\n"
        self._denies_orders(cmd, project, capsys)

    def test_cat_heredoc_piped_to_env_apply_patch(self, project, capsys):
        """A patch piped into `env apply_patch` is applied."""
        cmd = f"cat <<'EOF' | env apply_patch\n{_DELETE_ORDERS}\nEOF\n"
        self._denies_orders(cmd, project, capsys)

    def test_patch_file_redirected_into_env_apply_patch(self, project, capsys):
        """A patch written to a file and redirected into `env apply_patch` is applied."""
        cmd = f"cat > /tmp/p <<'EOF'\n{_DELETE_ORDERS}\nEOF\nenv apply_patch < /tmp/p\n"
        self._denies_orders(cmd, project, capsys)

    def test_backslash_at_end_of_unquoted_heredoc_line(self, project, capsys):
        """In an unquoted heredoc a trailing backslash joins the next line, so the
        `EOF` after it is body text and the heredoc runs on to the final `EOF`."""
        text = "\n".join([
            "*** Begin Patch", "*** Add File: notes.txt", "+hi\\", "EOF",
            "*** Delete File: models/orders.sql", "*** End Patch",
        ])
        assert "+hi\\\nEOF\n" in text
        reason = self._denies_orders(f"apply_patch <<EOF\n{text}\nEOF\n", project, capsys)
        assert "couldn't check" not in reason

    def test_heredoc_delimiter_containing_dollar(self, project, capsys):
        """`$+x` is a valid unquoted delimiter word; the body ends only at that line."""
        text = _patch("*** Add File: notes.txt", "+x", "*** Delete File: models/orders.sql")
        reason = self._denies_orders(f"apply_patch <<$+x\n{text}\n$+x\n", project, capsys)
        assert "couldn't check" not in reason

    def test_ansi_quoted_delimiter_is_not_guessed(self, project, capsys):
        """Shells differ on what `$'EOF'` quotes to, so the body isn't read."""
        out = _run_pre(f"apply_patch <<$'EOF'\n{_DELETE_ORDERS}\nEOF\n", project, capsys)
        assert _denied(out) and "isn't written out" in out["permissionDecisionReason"]

    @pytest.mark.parametrize("prefix", [
        "chdir models && ",
        "C=cd; $C models && ",
        "trap 'cd models' DEBUG; ",
    ])
    def test_directory_change_the_scanner_misses(self, project, capsys, prefix):
        """The shell may run apply_patch from `models`, so the patch's relative path
        cannot be resolved against the payload cwd."""
        cmd = _shell(_patch("*** Delete File: orders.sql"), prefix=prefix)
        assert _denied(_run_pre(cmd, project, capsys))

    def test_continuation_inside_command_name(self, project, capsys):
        out = _run_pre(_shell(_DELETE_ORDERS).replace("apply_patch", "apply\\\n_patch", 1), project, capsys)
        assert _denied(out) and "orders" in out["permissionDecisionReason"]
        assert "couldn't check" not in out["permissionDecisionReason"]

    def test_continuation_in_delimiter_leaves_it_unquoted(self, project, capsys):
        """The shell drops the backslash-newline first, so `<<E\\⏎OF` is a plain `<<EOF`
        whose body it expands."""
        text = _patch("*** Update File: src/app.js", "@@", "-x", "+$(printf 'y')")
        out = _run_pre(f"apply_patch <<E\\\nOF\n{text}\nEOF\n", project, capsys)
        assert _denied(out) and "couldn't check" in out["permissionDecisionReason"]

    def test_continuation_hiding_end_of_patch(self, project, capsys):
        """The shell joins `+hi\\` and `*** End Patch`, so the patch goes on to the next header."""
        text = _patch("*** Add File: notes.txt", "+hi\\", "*** End Patch", "*** Delete File: models/orders.sql")
        out = _run_pre(_shell(text, prefix="FOO=1 ", delim="EOF"), project, capsys)
        assert _denied(out)

    @pytest.mark.parametrize("prefix", ["f() { :; }; ", "function f { :; }; ", "alias x=y; "])
    def test_definitions_make_the_directory_unknown(self, project, capsys, prefix):
        cmd = _shell(_patch("*** Delete File: orders.sql"), prefix=prefix)
        out = _run_pre(cmd, project, capsys)
        assert _denied(out) and "can't be known" in out["permissionDecisionReason"]

    def test_array_assignment_keeps_the_directory(self, project, capsys):
        out = _run_pre(_shell(_DELETE_ORDERS, prefix="a=(x y); "), project, capsys)
        assert _denied(out) and "couldn't check" not in out["permissionDecisionReason"]

    def test_process_substitution_keeps_the_directory(self, project, capsys):
        out = _run_pre(_shell(_DELETE_ORDERS, prefix="diff <(ls) x; "), project, capsys)
        assert _denied(out) and "couldn't check" not in out["permissionDecisionReason"]


# --- Shell: the general scan's continuations and fd 0 ---

class TestShellScanDetails:
    def test_continuation_after_assignment(self, project, capsys):
        out = _run_pre(_shell(_DELETE_ORDERS, prefix="FOO=1 \\\n"), project, capsys)
        assert _denied(out) and "orders" in out["permissionDecisionReason"]

    def test_continuation_inside_cd(self, project, capsys):
        cmd = _shell(_patch("*** Delete File: orders.sql"), prefix="c\\\nd models && ")
        assert _denied(_run_pre(cmd, project, capsys))

    def test_heredoc_on_another_fd_is_not_the_patch(self, project, capsys):
        out = _run_pre(_shell(_DOCS_ONLY).replace("<<'EOF'", "3<<'EOF'", 1), project, capsys)
        assert _denied(out) and "isn't written out" in out["permissionDecisionReason"]

    def test_continuation_before_dash(self, project, capsys):
        """`<<\\⏎-EOF` is `<<-EOF`, so the heredoc ends at the tab-indented `EOF` and the
        call after it is gated too."""
        body = "\n".join("\t" + line for line in _DELETE_ORDERS.split("\n"))
        second = _patch("*** Delete File: models/customers.sql")
        cmd = f"apply_patch <<\\\n-EOF\n{body}\n\tEOF\napply_patch '{second}'\n"
        out = _run_pre(cmd, project, capsys)
        assert _denied(out) and "customers" in out["permissionDecisionReason"]
        assert "couldn't check" not in out["permissionDecisionReason"]

    def test_last_stdin_redirection_wins(self, project, capsys):
        cmd = _shell(_DELETE_ORDERS).replace("<<'EOF'", "< other.patch <<'EOF'", 1)
        out = _run_pre(cmd, project, capsys)
        assert _denied(out) and "orders" in out["permissionDecisionReason"]
        assert "couldn't check" not in out["permissionDecisionReason"]


# --- Patch text no recognised call gates ---

class TestUncheckedPatchPaths:
    @staticmethod
    def _unchecked(command):
        from shell_patch import find_invocations, unchecked_patch_paths
        return unchecked_patch_paths(command, find_invocations(command))

    def test_body_of_call_with_known_base_is_checked(self):
        assert self._unchecked(_shell(_DELETE_ORDERS)) == []

    def test_patch_text_further_into_a_body_is_checked_again(self):
        text = _patch("*** Update File: docs/a.md", "@@", "-x", "+*** Begin Patch",
                      "*** Delete File: models/orders.sql")
        assert self._unchecked(_shell(text)) == ["models/orders.sql"]

    def test_patch_after_leading_blank_lines(self):
        assert self._unchecked(_shell("\n\t" + _DELETE_ORDERS)) == []

    def test_body_of_call_with_unknown_base(self):
        assert self._unchecked(_shell(_DELETE_ORDERS, prefix="cd dbt; ")) == ["models/orders.sql"]

    def test_single_quoted_argument_is_checked(self):
        assert self._unchecked(f"apply_patch '{_DELETE_ORDERS}'") == []

    def test_unrecognised_call(self):
        assert self._unchecked(_shell(_DELETE_ORDERS, prefix="env ")) == ["models/orders.sql"]

    def test_every_patch_counts(self):
        cmd = _shell(_DOCS_ONLY, prefix="env ") + _shell(_DELETE_ORDERS, prefix="env ")
        assert self._unchecked(cmd) == ["models/orders.sql"]

    def test_patch_running_past_the_body(self):
        cmd = "apply_patch '*** Begin Patch\n*** Add File: a.md\n+x'\n*** Delete File: models/orders.sql\n"
        assert self._unchecked(cmd) == ["models/orders.sql"]

    def test_non_dbt_paths_left_out(self):
        assert self._unchecked(_shell(_DOCS_ONLY, prefix="env ")) == []

    def test_no_apply_patch_name(self):
        assert self._unchecked(f"cat <<'EOF'\n{_DELETE_ORDERS}\nEOF\n") == []

    def test_header_split_by_continuation(self):
        """The shell joins the header in an unquoted body."""
        text = _patch("*** Delete File: models/or\\", "ders.sql")
        assert self._unchecked(_shell(text, prefix="env ", delim="EOF")) == ["models/orders.sql"]

    def test_header_after_continuation_in_quoted_body(self):
        """A quoted body keeps its backslash-newlines, so the header stands on its own line."""
        text = _patch("*** Add File: a.md", "+x\\", "*** Delete File: models/orders.sql")
        assert self._unchecked(_shell(text, prefix="env ")) == ["models/orders.sql"]


# --- Shell: a command the scanner can't read ---

def _deeply_nested(levels):
    inner = "true"
    for _ in range(levels):
        inner = f'"$({inner})"'
    return f"echo {inner}"


class TestShellUnreadable:
    def test_deep_nesting_after_a_model_patch_denied(self, project, capsys):
        cmd = _shell(_patch(*_update("models/orders.sql"))) + _deeply_nested(600) + "\n"
        out = _run_pre(cmd, project, capsys)
        assert _denied(out) and "couldn't check" in out["permissionDecisionReason"]

    def test_deep_nesting_denied_even_after_assessment(self, project, capsys):
        cache.mark_impact_check_verified(SESSION, "orders")
        cmd = _shell(_patch(*_update("models/orders.sql"))) + _deeply_nested(600) + "\n"
        assert _denied(_run_pre(cmd, project, capsys))
        assert _edited() == []

    def test_deep_nesting_is_reported_not_raised_as_recursion(self):
        from shell_patch import UnreadableCommand, find_invocations
        cmd = _shell(_patch(*_update("models/orders.sql"))) + _deeply_nested(600) + "\n"
        with pytest.raises(UnreadableCommand):
            find_invocations(cmd)

    def test_moderate_nesting_still_read(self, project, capsys):
        cmd = _shell(_patch(*_update("models/orders.sql"))) + _deeply_nested(20) + "\n"
        out = _run_pre(cmd, project, capsys)
        assert _denied(out) and "couldn't check" not in out["permissionDecisionReason"]

    def test_deep_nesting_without_apply_patch_allowed(self, project, capsys):
        assert _run_pre(_deeply_nested(600), project, capsys) is None

    def test_any_scan_error_on_an_apply_patch_command_denied(self, project, capsys):
        with patch("bash_hook.find_invocations", side_effect=ValueError("boom")):
            out = _run_pre(_shell(_DOCS_ONLY), project, capsys)
        assert _denied(out) and "couldn't check" in out["permissionDecisionReason"]
        assert "boom" not in out["permissionDecisionReason"]

    def test_scan_error_respects_the_disable_switch(self, project, capsys, monkeypatch):
        monkeypatch.setenv("MC_PREVENT_HOOKS_DISABLED", "1")
        with patch("bash_hook.find_invocations", side_effect=ValueError("boom")):
            assert _run_pre(_shell(_DOCS_ONLY), project, capsys) is None


# --- Shell: a command name the shell unquotes ---

class TestShellQuotedName:
    @pytest.mark.parametrize("name", ["ap''ply_patch", 'ap""ply_patch', "apply\\_patch", "'apply_patch'",
                                      '"apply"_patch'])
    def test_quoted_name_gated(self, project, capsys, name):
        cmd = _shell(_patch(*_update("models/orders.sql")), delim="'PATCH'").replace("apply_patch", name, 1)
        out = _run_pre(cmd, project, capsys)
        assert _denied(out) and "orders" in out["permissionDecisionReason"]

    def test_quoted_name_with_patch_in_a_pipe_denied(self, project, capsys):
        cmd = f"cat <<'EOF' | env ap''ply_patch\n{_DELETE_ORDERS}\nEOF\n"
        out = _run_pre(cmd, project, capsys)
        assert _denied(out) and "orders" in out["permissionDecisionReason"]


# --- Shell: words that keep the next word in command position ---

class TestShellPrefixWordOptions:
    @pytest.mark.parametrize("prefix", [
        "command -p cd models && ",
        "command -- cd models && ",
        "command -p -- cd models && ",
        "builtin -- cd models && ",
        "exec -c cd models && ",
        "exec -a name cd models && ",
        "time -p cd models && ",
        "noglob cd models && ",
        "nocorrect cd models && ",
        "- cd models && ",
        "command -x cd models && ",
    ])
    def test_directory_change_behind_a_prefix_denied(self, project, capsys, prefix):
        out = _run_pre(_shell(_patch(*_update("orders.sql")), prefix=prefix), project, capsys)
        assert _denied(out) and "can't be known" in out["permissionDecisionReason"]

    @pytest.mark.parametrize("prefix", ["command -p ", "command -- ", "noglob ", "nocorrect ", "- ",
                                        "time -p ", "exec -c ", "exec -a name ", "builtin -- "])
    def test_call_behind_a_prefix_gated(self, project, capsys, prefix):
        out = _run_pre(_shell(_patch(*_update("models/orders.sql")), prefix=prefix), project, capsys)
        assert _denied(out) and "orders" in out["permissionDecisionReason"]
        assert "couldn't check" not in out["permissionDecisionReason"]

    @pytest.mark.parametrize("cmd", ["command -v apply_patch", "command -V apply_patch"])
    def test_lookup_is_not_a_call(self, project, capsys, cmd):
        assert _run_pre(cmd, project, capsys) is None


# --- Paths with a trailing slash ---

class TestTrailingSlashPaths:
    @pytest.mark.parametrize("path", ["models/orders.sql/", "models/orders.sql/."])
    def test_unrecognised_call_denied(self, project, capsys, path):
        out = _run_pre(_shell(_patch(*_update(path)), prefix="env "), project, capsys)
        assert _denied(out) and "couldn't check" in out["permissionDecisionReason"]

    @pytest.mark.parametrize("path", ["models/orders.sql/", "models/orders.sql/."])
    def test_unknown_directory_denied(self, project, capsys, path):
        out = _run_pre(_shell(_patch(*_update(path)), prefix="cd dbt; "), project, capsys)
        assert _denied(out) and "can't be known" in out["permissionDecisionReason"]

    @pytest.mark.parametrize("path", ["models/orders.sql/", "models/orders.sql/."])
    def test_recognised_call_gates_the_model(self, project, capsys, path):
        assert _checked_paths(_shell(_patch(*_update(path))), project, capsys) == [
            str(project / "models" / "orders.sql")
        ]

    @pytest.mark.parametrize("path", ["models/orders.sql/", "models/orders.sql/."])
    def test_native_call_gates_the_model(self, project, capsys, path):
        out = _run_pre(_patch(*_update(path)), project, capsys, tool_name="apply_patch")
        assert _denied(out) and "orders" in out["permissionDecisionReason"]

    def test_native_post_tracks_the_model(self, project, capsys):
        cache.mark_impact_check_verified(SESSION, "orders")
        text = _patch(*_update("models/orders.sql/"))
        assert _run_pre(text, project, capsys, tool_name="apply_patch") is None
        _run_post(text, project)
        assert _edited() == ["orders"]

    @pytest.mark.parametrize("path", ["models/", "notes.md", "notes.md/"])
    def test_non_dbt_paths_allowed(self, project, capsys, path):
        assert _run_pre(_shell(_patch(*_update(path)), prefix="env "), project, capsys) is None


# --- A patch inside Codex's `<<EOF` wrapper ---

def _wrapped(text, delim="EOF"):
    return f"<<{delim}\n{text}\nEOF"


class TestCodexWrapperInShell:
    @pytest.mark.parametrize("delim", ["EOF", '"EOF"'])
    def test_argument_allowed_after_assessment(self, project, capsys, delim):
        cache.mark_impact_check_verified(SESSION, "orders")
        cmd = f"apply_patch '{_wrapped(_patch(*_update('models/orders.sql', 'a', 'b')), delim)}'"
        assert _run_pre(cmd, project, capsys) is None
        assert _edited() == ["orders"]

    def test_argument_denied_before_assessment(self, project, capsys):
        cmd = f"apply_patch '{_wrapped(_patch(*_update('models/orders.sql', 'a', 'b')))}'"
        out = _run_pre(cmd, project, capsys)
        assert _denied(out) and "orders" in out["permissionDecisionReason"]
        assert "couldn't check" not in out["permissionDecisionReason"]

    @pytest.mark.parametrize("delim", ["EOF", "'EOF'", '"EOF"'])
    def test_heredoc_allowed_after_assessment(self, project, capsys, delim):
        cache.mark_impact_check_verified(SESSION, "orders")
        cmd = f"apply_patch <<'X'\n{_wrapped(_patch(*_update('models/orders.sql')), delim)}\nX\n"
        assert _run_pre(cmd, project, capsys) is None
        assert _edited() == ["orders"]

    def test_scanned_heredoc_allowed_after_assessment(self, project, capsys):
        cache.mark_impact_check_verified(SESSION, "orders")
        cmd = f"FOO=1 apply_patch <<'X'\n{_wrapped(_patch(*_update('models/orders.sql')))}\nX\n"
        assert _run_pre(cmd, project, capsys) is None
        assert _edited() == ["orders"]

    def test_heredoc_denied_before_assessment(self, project, capsys):
        cmd = f"apply_patch <<'X'\n{_wrapped(_patch(*_update('models/orders.sql')))}\nX\n"
        out = _run_pre(cmd, project, capsys)
        assert _denied(out) and "orders" in out["permissionDecisionReason"]
        assert "couldn't check" not in out["permissionDecisionReason"]

    def test_text_other_than_the_wrapper_before_the_patch_still_unchecked(self):
        from shell_patch import find_invocations, unchecked_patch_paths
        cmd = f"apply_patch '<<END\n{_DELETE_ORDERS}\nEND'"
        assert unchecked_patch_paths(cmd, find_invocations(cmd)) == ["models/orders.sql"]


# --- Behaviours of the shell gate as a whole ---

class TestShellGateContract:
    def test_mixed_command_blocked_and_nothing_tracked(self, project, capsys):
        cache.mark_impact_check_verified(SESSION, "orders")
        cmd = _shell(_patch(*_update("models/orders.sql"))) + "apply_patch < f.patch\n"
        out = _run_pre(cmd, project, capsys)
        assert _denied(out) and "couldn't check" in out["permissionDecisionReason"]
        assert _edited() == []

    def test_mixed_command_keeps_the_assessment_instructions(self, project, capsys):
        cmd = _shell(_patch(*_update("models/orders.sql"))) + "apply_patch < f.patch\n"
        reason = _run_pre(cmd, project, capsys)["permissionDecisionReason"]
        assert "couldn't check" in reason
        assert "run the change impact assessment for orders" in reason

    @pytest.mark.parametrize("prefix", [
        "eval cd models; ",
        "if cd models; then :; fi; ",
        "while cd models; do break; done; ",
        "if true; then cd models; fi; ",
        "if false; then :; else cd models; fi; ",
        "if false; then :; elif cd models; then :; fi; ",
        "while true; do cd models; break; done; ",
        "until cd models; do :; done; ",
        "{ cd models; }; ",
        "! cd models; ",
        "time cd models; ",
    ])
    def test_directory_change_in_a_compound_command(self, project, capsys, prefix):
        out = _run_pre(_shell(_patch(*_update("orders.sql")), prefix=prefix), project, capsys)
        assert _denied(out) and "can't be known" in out["permissionDecisionReason"]

    @pytest.mark.parametrize("tool_name,command", [
        ("Bash", _shell(_patch(*_update("models/orders.sql")))),
        ("apply_patch", _patch(*_update("models/orders.sql"))),
    ])
    def test_transcript_path_reaches_the_gate(self, project, capsys, tool_name, command):
        import bash_hook
        seen = []
        real = bash_hook.evaluate_pre_edit

        def spy(inp):
            seen.append(inp.transcript_path)
            return real(inp)

        with patch.object(bash_hook, "evaluate_pre_edit", side_effect=spy):
            _run_pre(command, project, capsys, tool_name, transcript_path="/tmp/rollout.jsonl")
        assert seen and set(seen) == {"/tmp/rollout.jsonl"}

    def test_commit_message_naming_apply_patch_gets_the_commit_check(self, project, capsys):
        from lib.protocol import HookOutput
        with patch("bash_hook.evaluate_pre_commit", return_value=HookOutput(action="context", context="ctx")):
            out = _run_pre('git commit -m "use apply_patch"', project, capsys)
        assert out == {"hookEventName": "PreToolUse", "additionalContext": "ctx"}

    @pytest.mark.parametrize("cmd", [
        _shell(_patch(*_update("models/orders.sql"))),
        "apply_patch < f.patch",
    ])
    def test_deny_names_the_event(self, project, capsys, cmd):
        out = _run_pre(cmd, project, capsys)
        assert _denied(out) and out["hookEventName"] == "PreToolUse"

    def test_native_deny_names_the_event(self, project, capsys):
        out = _run_pre(_patch(*_update("models/orders.sql")), project, capsys, tool_name="apply_patch")
        assert _denied(out) and out["hookEventName"] == "PreToolUse"

    def test_here_string_is_not_a_heredoc(self, project, capsys):
        """A `<<<` word doesn't start a heredoc, so the lines after it are still commands."""
        out = _run_pre("cat <<< hi\n" + _shell(_DELETE_ORDERS), project, capsys)
        assert _denied(out) and "orders" in out["permissionDecisionReason"]
        assert "couldn't check" not in out["permissionDecisionReason"]

    def test_here_string_body_is_not_read(self, project, capsys):
        out = _run_pre(f"apply_patch <<< '{_DOCS_ONLY}'", project, capsys)
        assert _denied(out) and "isn't written out" in out["permissionDecisionReason"]
