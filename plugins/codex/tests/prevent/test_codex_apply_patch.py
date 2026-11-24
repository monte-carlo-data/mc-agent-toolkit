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



# --- Shell: forms Codex doesn't apply itself ---
#
# Only `apply_patch <<'EOF'` and `cd <dir> && apply_patch <<'EOF'` are gated against a
# folder. Any other command naming apply_patch is denied as unchecked when its patch may
# change a dbt file, and allowed otherwise. The forms below each run a model patch in a
# folder, or from text, that the hook can't know before the shell runs it.

_DELETE_ORDERS = _patch("*** Delete File: models/orders.sql")
_DOCS_ONLY = _patch("*** Update File: docs/readme.md", "@@", "-a", "+b")
_ADD_NOTES = _patch("*** Add File: notes.txt", "+hi")


def _unchecked_deny(out, *paths):
    """Assert a couldn't-check deny naming `paths`; return its reason."""
    assert _denied(out)
    reason = out["permissionDecisionReason"]
    assert reason.startswith("Monte Carlo Prevent: couldn't check this apply_patch command")
    for path in paths:
        assert path in reason
    return reason


class TestShellOtherForms:
    @pytest.mark.parametrize("prefix", [
        "cd dbt; ",
        "cd dbt && cd models && ",
        "false && cd dbt; ",
        'cd "$DBT_DIR" && ',
        'cd "a"$B && ',
        "cd ~/dbt && ",
        "cd - && ",
        "pushd dbt && ",
        "chdir models && ",
        "C=cd; $C models && ",
        "trap 'cd models' DEBUG; ",
        "builtin cd models && ",
        "source env.sh && ",
        ". env.sh && ",
        "c\\\nd models && ",
        "f() { :; }; ",
        "function f { :; }; ",
        "alias x=y; ",
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
    def test_directory_change_before_the_call(self, project, capsys, prefix):
        """The shell may run apply_patch from `models`, so `orders.sql` may be a model."""
        out = _run_pre(_shell(_patch(*_update("orders.sql")), prefix=prefix), project, capsys)
        _unchecked_deny(out, "orders.sql")

    @pytest.mark.parametrize("prefix", [
        "FOO=1 ",
        'FOO="$(pwd)" ',
        "FOO=1 \\\n",
        "/usr/local/bin/",
        "command ",
        "command -p ",
        "command -- ",
        "exec ",
        "exec -c ",
        "exec -a name ",
        "builtin -- ",
        "noglob ",
        "nocorrect ",
        "- ",
        "time -p ",
        "env ",
        "env FOO=1 ",
        "timeout 30 ",
        "nice -n 5 ",
        "nohup ",
        "a=(x y); ",
        "diff <(ls) x; ",
        "cat <<< hi\n",
    ])
    def test_prefix_before_the_call(self, project, capsys, prefix):
        out = _run_pre(_shell(_DELETE_ORDERS, prefix=prefix), project, capsys)
        _unchecked_deny(out, "models/orders.sql")

    @pytest.mark.parametrize("cmd", [
        pytest.param("(cd dbt && " + _shell(_DELETE_ORDERS).rstrip("\n") + "\n)", id="subshell"),
        pytest.param("out=$(" + _shell(_DELETE_ORDERS) + ")", id="command-substitution"),
        pytest.param(f"bash -lc 'apply_patch <<EOF\n{_DELETE_ORDERS}\nEOF'", id="bash-lc"),
        pytest.param(f"zsh -c 'apply_patch <<EOF\n{_DELETE_ORDERS}\nEOF'", id="zsh-c"),
        pytest.param(f"apply_patch <<'A'\n{_ADD_NOTES}\nA\nenv apply_patch <<'B'\n{_DELETE_ORDERS}\nB\n",
                     id="recognised-call-then-env-call"),
        pytest.param(f"env apply_patch <<'A'\n{_ADD_NOTES}\nA\nenv apply_patch <<'B'\n{_DELETE_ORDERS}\nB\n",
                     id="two-env-calls"),
        pytest.param(f"bash <<'EOF'\napply_patch <<'P'\n{_DELETE_ORDERS}\nP\nEOF\n", id="inside-bash-heredoc"),
        pytest.param(f"cat <<'EOF' | env apply_patch\n{_DELETE_ORDERS}\nEOF\n", id="piped-to-env-call"),
        pytest.param(f"cat > /tmp/p <<'EOF'\n{_DELETE_ORDERS}\nEOF\nenv apply_patch < /tmp/p\n",
                     id="file-redirected-into-env-call"),
        pytest.param(f"cat > notes.md <<'EOF'\napply_patch <<'X'\n{_DELETE_ORDERS}\nX\nEOF\n",
                     id="in-another-commands-heredoc"),
        pytest.param(f"apply_patch <<$+x\n{_patch('*** Add File: notes.txt', '+x', '*** Delete File: models/orders.sql')}"
                     "\n$+x\n", id="delimiter-with-dollar"),
        pytest.param(f"apply_patch <<$'EOF'\n{_DELETE_ORDERS}\nEOF\n", id="ansi-quoted-delimiter"),
        pytest.param(_shell(_DELETE_ORDERS).replace("apply_patch", "apply\\\n_patch", 1),
                     id="continuation-inside-name"),
        pytest.param(_shell(_DELETE_ORDERS).replace("<<'EOF'", "< other.patch <<'EOF'", 1),
                     id="stdin-file-then-heredoc"),
        pytest.param(f"apply_patch '{_DELETE_ORDERS}'", id="single-quoted-argument"),
        pytest.param(f"apply_patch '<<EOF\n{_DELETE_ORDERS}\nEOF'", id="wrapper-in-argument"),
        pytest.param(_shell(_DELETE_ORDERS) + 'echo "$(true)"\n', id="text-after-the-heredoc"),
    ])
    def test_model_patch_denied(self, project, capsys, cmd):
        _unchecked_deny(_run_pre(cmd, project, capsys), "models/orders.sql")

    def test_continuation_before_dash_names_both_patches(self, project, capsys):
        """`<<\\⏎-EOF` is `<<-EOF`; the call after it is read too."""
        body = "\n".join("\t" + line for line in _DELETE_ORDERS.split("\n"))
        second = _patch("*** Delete File: models/customers.sql")
        cmd = f"apply_patch <<\\\n-EOF\n{body}\n\tEOF\napply_patch '{second}'\n"
        _unchecked_deny(_run_pre(cmd, project, capsys), "models/orders.sql", "models/customers.sql")

    def test_yaml_denied(self, project, capsys):
        text = _patch("*** Update File: models/schema.YML", "@@", "-a", "+b")
        _unchecked_deny(_run_pre(_shell(text, prefix="cd dbt; "), project, capsys), "models/schema.YML")

    def test_move_to_sql_denied(self, project, capsys):
        text = _patch("*** Update File: notes.md", "*** Move to: models/orders.sql", "@@", "-a", "+b")
        _unchecked_deny(_run_pre(_shell(text, prefix="cd dbt; "), project, capsys), "models/orders.sql")

    def test_one_reason_lists_every_path(self, project, capsys):
        cmd = _shell(_DELETE_ORDERS, prefix="env ") + _shell(_patch("*** Delete File: models/customers.sql"),
                                                              prefix="env ")
        reason = _unchecked_deny(_run_pre(cmd, project, capsys), "models/orders.sql, models/customers.sql")
        assert reason.count("couldn't check") == 1
        assert "isn't written out" not in reason and "expand" not in reason

    def test_denied_even_after_assessment_and_nothing_tracked(self, project, capsys):
        cache.mark_impact_check_verified(SESSION, "orders")
        _unchecked_deny(_run_pre(_shell(_DELETE_ORDERS, prefix="FOO=1 "), project, capsys))
        assert _edited() == []

    def test_two_calls_second_denied_tracks_nothing(self, project, capsys):
        first = _shell(_patch("*** Add File: models/brand_new.sql", "+select 1"))
        second = _shell(_patch(*_update("models/orders.sql")))
        _unchecked_deny(_run_pre(first + second, project, capsys), "models/orders.sql")
        assert _edited() == []

    @pytest.mark.parametrize("path", ["models/orders.sql/", "models/orders.sql/."])
    def test_trailing_slash_denied(self, project, capsys, path):
        _unchecked_deny(_run_pre(_shell(_patch(*_update(path)), prefix="env "), project, capsys), path)

    @pytest.mark.parametrize("cmd", [
        _shell(_DOCS_ONLY, prefix="env "),
        _shell(_DOCS_ONLY, prefix="FOO=1 "),
        _shell(_DOCS_ONLY, prefix="cd dbt; "),
        "(cd dbt && " + _shell(_DOCS_ONLY).rstrip("\n") + "\n)",
        _shell(_DOCS_ONLY) + _shell(_ADD_NOTES),
        f"apply_patch '{_DOCS_ONLY}'",
        _shell(_patch("*** Update File: src/app.py", "@@", "-x", "+print(\"a\\n\")"), prefix="FOO=1 ", delim="EOF"),
    ] + [_shell(_patch(*_update(path)), prefix="env ") for path in ["models/", "notes.md", "notes.md/"]])
    def test_non_dbt_patch_allowed_and_not_tracked(self, project, capsys, cmd):
        assert _run_pre(cmd, project, capsys) is None
        assert _edited() == []

    def test_backslash_joining_a_header_denied(self, project, capsys):
        """The shell joins these two lines into `*** Delete File: models/orders.sql`."""
        text = _patch("**\\", "* Delete File: models/orders.sql")
        _unchecked_deny(_run_pre(_shell(text, prefix="FOO=1 ", delim="EOF"), project, capsys), "models/orders.sql")

    def test_continuation_hiding_end_of_patch(self, project, capsys):
        """The shell joins `+hi\\` and `*** End Patch`, so the patch goes on to the next header."""
        text = _patch("*** Add File: notes.txt", "+hi\\", "*** End Patch", "*** Delete File: models/orders.sql")
        _unchecked_deny(_run_pre(_shell(text, prefix="FOO=1 ", delim="EOF"), project, capsys), "models/orders.sql")

    def test_long_nested_command_after_a_model_patch_denied(self, project, capsys):
        inner = "true"
        for _ in range(600):
            inner = f'"$({inner})"'
        cmd = _shell(_patch(*_update("models/orders.sql"))) + f"echo {inner}\n"
        _unchecked_deny(_run_pre(cmd, project, capsys), "models/orders.sql")


# --- Shell: a patch the command doesn't spell out ---

class TestShellUnwrittenPatch:
    @pytest.mark.parametrize("cmd", [
        "apply_patch < /tmp/p.diff",
        'apply_patch "$(cat /tmp/p.diff)"',
        "cat /tmp/p.diff | apply_patch",
        "cat /tmp/p.diff | ap''ply_patch",
        "apply_patch <<EOF\n*** Begin Patch\n*** Update File: $F\n@@\n-a\n+b\n*** End Patch\nEOF\n",
        _shell(_DOCS_ONLY).replace("apply_patch", 'apply_patch "$P"', 1),
        _shell(_DOCS_ONLY).replace("<<'EOF'", "<<'EOF' < other.patch", 1),
        _shell(_DOCS_ONLY).replace("<<'EOF'", "3<<'EOF'", 1),
        f"apply_patch <<< '{_DOCS_ONLY}'",
        f"cat > /tmp/p <<'EOF'\n{_DOCS_ONLY}\nEOF\nenv apply_patch < /tmp/p\n",
        _shell(_DELETE_ORDERS) + "apply_patch < f.patch\n",
    ])
    def test_denied(self, project, capsys, cmd):
        assert "the patch isn't written out" in _unchecked_deny(_run_pre(cmd, project, capsys))

    def test_unquoted_heredoc_built_from_a_variable_denied(self, project, capsys):
        """The patch text sits in `$X`, where no header line is written out."""
        cmd = ("X=$'*** Begin Patch\\n*** Delete File: models/orders.sql\\n*** End Patch'\n"
               "apply_patch <<EOF\n$X\nEOF\n")
        assert "the patch isn't written out" in _unchecked_deny(_run_pre(cmd, project, capsys))

    def test_continuation_in_delimiter_leaves_it_unquoted(self, project, capsys):
        """The shell drops the backslash-newline first, so `<<E\\⏎OF` is a plain `<<EOF`
        whose body it expands."""
        text = _patch("*** Update File: src/app.js", "@@", "-x", "+$(printf 'y')")
        assert "the patch isn't written out" in _unchecked_deny(
            _run_pre(f"apply_patch <<E\\\nOF\n{text}\nEOF\n", project, capsys))

    def test_mixed_command_blocked_and_nothing_tracked(self, project, capsys):
        cache.mark_impact_check_verified(SESSION, "orders")
        cmd = _shell(_patch(*_update("models/orders.sql"))) + "apply_patch < f.patch\n"
        reason = _unchecked_deny(_run_pre(cmd, project, capsys), "models/orders.sql")
        assert "the patch isn't written out" in reason
        assert _edited() == []

    @pytest.mark.parametrize("cmd", [
        "grep -rn apply_patch .",
        "echo 'run apply_patch <<EOF later'",
        "# apply_patch < x\nls",
        "echo apply_patch is a tool",
        "command -v apply_patch",
        "command -V apply_patch",
        f"cat > notes.md <<'EOF'\napply_patch <<'X'\n{_patch('*** Update File: docs/a.md')}\nX\nEOF\n",
    ])
    def test_mention_is_not_a_call(self, project, capsys, cmd):
        assert _run_pre(cmd, project, capsys) is None

    @pytest.mark.parametrize("cmd,expected", [
        ('git commit -m "use apply_patch"', False),
        ("apply_patch", True),
        ("x=1 env apply_patch", True),
        ("/usr/bin/applypatch < p", True),
        ("echo hi; apply_patch", True),
        ("echo hi && apply_patch <<'EOF'\nEOF\n", False),
        ("FOO=$x apply_patch <<EOF\nEOF\n", True),
        ("FOO=$x apply_patch <<\\EOF\nEOF\n", False),
        ("apply_patch '*** Begin Patch'", False),
        ("apply_patch <<(ls)", True),
    ])
    def test_reads_unwritten_patch(self, cmd, expected):
        from shell_patch import reads_unwritten_patch
        assert reads_unwritten_patch(cmd) is expected


# --- Shell: patch text the shell may expand ---

class TestShellExpandingPatch:
    def test_dollar_in_hunk_of_an_unquoted_heredoc_denied(self, project, capsys):
        text = _patch("*** Update File: src/app.js", "@@", "-x", "+$(printf 'y')")
        reason = _unchecked_deny(_run_pre(_shell(text, prefix="FOO=1 ", delim="EOF"), project, capsys))
        assert "expand" in reason

    @pytest.mark.parametrize("hunk", ["+$(printf 'y')", "+`printf y`", "+$X"])
    def test_expansion_in_patch_text_alone_denied(self, project, capsys, hunk):
        """Inside `bash -c "..."` the shell expands the patch text, wherever it is."""
        text = _patch("*** Update File: src/app.js", "@@", "-x", hunk)
        reason = _unchecked_deny(_run_pre(f"bash -c \"apply_patch <<'P'\n{text}\nP\"", project, capsys))
        assert "the shell may expand" in reason
        assert "isn't written out" not in reason

    def test_expansion_after_the_end_of_the_patch_is_not_the_patch(self, project, capsys):
        cmd = f"env apply_patch <<'EOF'\n{_DOCS_ONLY}\nEOF\necho \"$HOME\"\n"
        assert _run_pre(cmd, project, capsys) is None

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


# --- Shell: the recognised forms, read exactly ---

class TestShellRecognised:
    def test_backslash_continuation_after_cd(self, project, capsys):
        """Codex's parser sees through a backslash-newline between `&&` and the name."""
        cmd = "cd models && \\\n" + _shell(_patch("*** Delete File: orders.sql"))
        out = _run_pre(cmd, project, capsys)
        assert _denied(out)
        assert "orders" in out["permissionDecisionReason"]
        assert "couldn't check" not in out["permissionDecisionReason"]

    def test_backslash_at_end_of_unquoted_heredoc_line(self, project, capsys):
        """In an unquoted heredoc a trailing backslash joins the next line, so the
        `EOF` after it is body text and the heredoc runs on to the final `EOF`."""
        text = "\n".join([
            "*** Begin Patch", "*** Add File: notes.txt", "+hi\\", "EOF",
            "*** Delete File: models/orders.sql", "*** End Patch",
        ])
        assert "+hi\\\nEOF\n" in text
        out = _run_pre(f"apply_patch <<EOF\n{text}\nEOF\n", project, capsys)
        assert _denied(out) and "orders" in out["permissionDecisionReason"]
        assert "couldn't check" not in out["permissionDecisionReason"]

    def test_patch_further_into_the_body_also_checked(self, project, capsys):
        """A patch that doesn't start the body is text a real shell may apply on its own,
        so it is checked by path, in the same reply as the body's own gate."""
        text = _patch(*_update("models/orders.sql"), "+*** Begin Patch", "*** Delete File: models/customers.sql")
        reason = _run_pre(_shell(text), project, capsys)["permissionDecisionReason"]
        assert "couldn't check" in reason and "models/customers.sql" in reason
        assert "run the change impact assessment for orders" in reason

    @pytest.mark.parametrize("cmd", [
        f"apply_patch <<'X'\n<<EOF\n{_DELETE_ORDERS}\nEOF\nX\n",
        f"apply_patch <<'X'\n\n\t{_DELETE_ORDERS}\nX\n",
    ])
    def test_wrapper_and_leading_blanks_are_part_of_the_body(self, project, capsys, cmd):
        cache.mark_impact_check_verified(SESSION, "orders")
        assert _run_pre(cmd, project, capsys) is None
        assert _edited() == ["orders"]


# --- Patch text the recognised call doesn't gate ---

class TestUncheckedPatchPaths:
    @staticmethod
    def _unchecked(command):
        from shell_patch import find_invocation, unchecked_patch_paths
        return unchecked_patch_paths(command, find_invocation(command))

    def test_body_of_recognised_call_is_checked(self):
        assert self._unchecked(_shell(_DELETE_ORDERS)) == []

    def test_patch_text_further_into_a_body_is_checked_again(self):
        text = _patch("*** Update File: docs/a.md", "@@", "-x", "+*** Begin Patch",
                      "*** Delete File: models/orders.sql")
        assert self._unchecked(_shell(text)) == ["models/orders.sql"]

    def test_patch_after_leading_blank_lines(self):
        assert self._unchecked(_shell("\n\t" + _DELETE_ORDERS)) == []

    def test_other_forms(self):
        assert self._unchecked(_shell(_DELETE_ORDERS, prefix="cd dbt; ")) == ["models/orders.sql"]
        assert self._unchecked(f"apply_patch '{_DELETE_ORDERS}'") == ["models/orders.sql"]
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

    def test_text_other_than_the_wrapper_before_the_patch_still_unchecked(self):
        assert self._unchecked(f"apply_patch '<<END\n{_DELETE_ORDERS}\nEND'") == ["models/orders.sql"]


# --- Shell: switches and fallbacks ---

class TestShellSwitches:
    @pytest.mark.parametrize("cmd", [
        "apply_patch < /tmp/p.diff",
        _shell(_DELETE_ORDERS, prefix="env "),
        f"bash -lc 'apply_patch <<EOF\n{_DELETE_ORDERS}\nEOF'",
        f"bash -c \"apply_patch <<'P'\n{_patch('*** Add File: a.js', '+$(x)')}\nP\"",
    ])
    def test_disable_switch_suppresses_unchecked_deny(self, project, capsys, monkeypatch, cmd):
        monkeypatch.setenv("MC_PREVENT_HOOKS_DISABLED", "1")
        assert _run_pre(cmd, project, capsys) is None

    def test_any_error_reading_an_apply_patch_command_denied(self, project, capsys):
        with patch("bash_hook.find_invocation", side_effect=ValueError("boom")):
            out = _run_pre(_shell(_DOCS_ONLY), project, capsys)
        assert _denied(out) and "couldn't check" in out["permissionDecisionReason"]
        assert "boom" not in out["permissionDecisionReason"]

    def test_read_error_respects_the_disable_switch(self, project, capsys, monkeypatch):
        monkeypatch.setenv("MC_PREVENT_HOOKS_DISABLED", "1")
        with patch("bash_hook.find_invocation", side_effect=ValueError("boom")):
            assert _run_pre(_shell(_DOCS_ONLY), project, capsys) is None

    def test_read_error_without_apply_patch_allowed(self, project, capsys):
        with patch("bash_hook.find_invocation", side_effect=ValueError("boom")):
            assert _run_pre("ls", project, capsys) is None

    def test_git_commit_still_checked(self, project, capsys):
        from lib.protocol import HookOutput
        with patch("bash_hook.evaluate_pre_commit", return_value=HookOutput(action="context", context="ctx")):
            out = _run_pre("git commit -m 'x'", project, capsys)
        assert out["additionalContext"] == "ctx"

    def test_commit_message_naming_apply_patch_gets_the_commit_check(self, project, capsys):
        from lib.protocol import HookOutput
        with patch("bash_hook.evaluate_pre_commit", return_value=HookOutput(action="context", context="ctx")):
            out = _run_pre('git commit -m "use apply_patch"', project, capsys)
        assert out == {"hookEventName": "PreToolUse", "additionalContext": "ctx"}

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



# --- Shell: a command name the shell unquotes ---

class TestShellQuotedName:
    @pytest.mark.parametrize("name", ["ap''ply_patch", 'ap""ply_patch', "apply\\_patch", "'apply_patch'",
                                      '"apply"_patch'])
    def test_quoted_name_denied(self, project, capsys, name):
        cmd = _shell(_patch(*_update("models/orders.sql")), delim="'PATCH'").replace("apply_patch", name, 1)
        _unchecked_deny(_run_pre(cmd, project, capsys), "models/orders.sql")

    def test_quoted_name_with_patch_in_a_pipe_denied(self, project, capsys):
        cmd = f"cat <<'EOF' | env ap''ply_patch\n{_DELETE_ORDERS}\nEOF\n"
        _unchecked_deny(_run_pre(cmd, project, capsys), "models/orders.sql")


# --- Paths with a trailing slash ---

class TestTrailingSlashPaths:
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


# --- A patch inside Codex's `<<EOF` wrapper ---

def _wrapped(text, delim="EOF"):
    return f"<<{delim}\n{text}\nEOF"


class TestCodexWrapperInShell:
    @pytest.mark.parametrize("delim", ["EOF", "'EOF'", '"EOF"'])
    def test_heredoc_allowed_after_assessment(self, project, capsys, delim):
        cache.mark_impact_check_verified(SESSION, "orders")
        cmd = f"apply_patch <<'X'\n{_wrapped(_patch(*_update('models/orders.sql')), delim)}\nX\n"
        assert _run_pre(cmd, project, capsys) is None
        assert _edited() == ["orders"]

    def test_heredoc_denied_before_assessment(self, project, capsys):
        cmd = f"apply_patch <<'X'\n{_wrapped(_patch(*_update('models/orders.sql')))}\nX\n"
        out = _run_pre(cmd, project, capsys)
        assert _denied(out) and "orders" in out["permissionDecisionReason"]
        assert "couldn't check" not in out["permissionDecisionReason"]

    @pytest.mark.parametrize("cmd", [
        f"apply_patch '{_wrapped(_patch(*_update('models/orders.sql', 'a', 'b')))}'",
        f"FOO=1 apply_patch <<'X'\n{_wrapped(_patch(*_update('models/orders.sql')))}\nX\n",
    ])
    def test_other_forms_denied_even_after_assessment(self, project, capsys, cmd):
        cache.mark_impact_check_verified(SESSION, "orders")
        _unchecked_deny(_run_pre(cmd, project, capsys), "models/orders.sql")
        assert _edited() == []


# --- Behaviours of the shell gate as a whole ---

class TestShellGateContract:
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

    def test_other_form_is_not_tracked_or_gated(self, project, capsys):
        """Only a recognised call's files reach the gate."""
        assert _checked_paths(_shell(_DOCS_ONLY, prefix="env "), project, capsys) == []
