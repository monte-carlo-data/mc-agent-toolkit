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


def _unchecked_deny(out):
    """Assert the couldn't-check deny."""
    from bash_hook import _UNCHECKED_REASON
    assert _denied(out)
    assert out["permissionDecisionReason"] == _UNCHECKED_REASON


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

    def test_two_invocations_denied_unchecked_tracks_nothing(self, project, capsys):
        first = _shell(_patch("*** Add File: models/brand_new.sql", "+select 1"))
        second = _shell(_patch(*_update("models/orders.sql")))
        _unchecked_deny(_run_pre(first + second, project, capsys))
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



# --- Shell: every other command that names apply_patch ---
#
# Only `apply_patch <<'EOF'` and `cd <dir> && apply_patch <<'EOF'` are gated against a
# folder. Any other command naming apply_patch is denied as unchecked, whatever its patch
# text, with no dbt project in reach, or when it only mentions the name. Each form below
# was once read wrongly by a hook that tried to work out what the shell would do.

_DELETE_ORDERS = _patch("*** Delete File: models/orders.sql")
_DOCS_ONLY = _patch("*** Update File: docs/readme.md", "@@", "-a", "+b")
_ADD_NOTES = _patch("*** Add File: notes.txt", "+hi")
_SPLIT_MODEL = "\n".join(["*** Update File: models/orders.sql", "@@", "-select 1 as id", "+select 9 as id",
                          "*** End Patch"])
# Tab-indented: as written, the second header is hunk text; a shell strips the tabs of a
# `<<-` heredoc and reads it as a header.
_TAB_HIDDEN = "\n".join("\t" + line for line in _patch(
    "*** Update File: docs/a.md", "@@", "-x", "+y", *_update("models/orders.sql")).split("\n"))
_TAB_DOCS = "\n".join("\t" + line for line in _DOCS_ONLY.split("\n"))


# Text before a written-out call that may change the folder it runs in or what runs.
_PREFIXES = [
    "cd dbt; ", "cd dbt && cd models && ", "false && cd dbt; ", 'cd "$DBT_DIR" && ', 'cd "a"$B && ',
    "cd ~/dbt && ", "cd - && ", "pushd dbt && ", "chdir models && ", "C=cd; $C models && ",
    "trap 'cd models' DEBUG; ", "builtin cd models && ", "source env.sh && ", ". env.sh && ",
    "c\\\nd models && ", "f() { :; }; ", "function f { :; }; ", "alias x=y; ", "eval cd models; ",
    "if cd models; then :; fi; ", "while cd models; do break; done; ", "{ cd models; }; ", "! cd models; ",
    "time cd models; ", "command -p cd models && ", "exec -a name cd models && ", "noglob cd models && ",
    "- cd models && ", "FOO=1 ", 'FOO="$(pwd)" ', "FOO=1 \\\n", "/usr/local/bin/", "command ", "exec ",
    "builtin -- ", "nocorrect ", "time -p ", "env ", "env FOO=1 ", "env -u FOO ", "timeout 30 ",
    "nice -n 5 ", "nohup ", "sudo -u root ", "xargs -I {} ", "a=(x y); ", "diff <(ls) x; ",
    "cat <<< hi\n", "true; ", "echo hi && ",
]

# Wrappers around a call: (before, after).
_WRAPPERS = [
    ("{ ", "; }"), ("if ", "; then :; fi"), ("if true; then ", "; fi"), ("if false; then :; else ", "; fi"),
    ("if false; then :; elif ", "; then :; fi"), ("while true; do ", "; break; done"),
    ("while ", "; do break; done"), ("until ", "; do :; done"), ("(", ")"), ("out=$(", ")"),
]

_OTHER_FORMS = [
    # The two recognised forms, with a model patch, in a shape Codex doesn't intercept.
    *[pytest.param(_shell(_DELETE_ORDERS, prefix=p), id=f"prefix:{p!r}") for p in _PREFIXES],
    *[pytest.param(f"{a}apply_patch <<'EOF'{b}\n{_DOCS_ONLY}\nEOF\n", id=f"wrapper:{a}CALL{b}")
      for a, b in _WRAPPERS],
    pytest.param(f"bash -lc 'apply_patch <<EOF\n{_DELETE_ORDERS}\nEOF'", id="bash-lc"),
    pytest.param(f"zsh -c 'apply_patch <<EOF\n{_DELETE_ORDERS}\nEOF'", id="zsh-c"),
    pytest.param(f"bash -c \"apply_patch <<'P'\n{_patch('*** Add File: a.js', '+$(x)')}\nP\"",
                 id="bash-c-expanding"),
    pytest.param(f"bash <<'EOF'\napply_patch <<'P'\n{_DELETE_ORDERS}\nP\nEOF\n", id="inside-bash-heredoc"),
    pytest.param(f"apply_patch <<'A'\n{_ADD_NOTES}\nA\nenv apply_patch <<'B'\n{_DELETE_ORDERS}\nB\n",
                 id="recognised-call-then-env-call"),
    pytest.param(_shell(_DOCS_ONLY) + _shell(_ADD_NOTES), id="two-recognised-calls"),
    pytest.param(_shell(_DOCS_ONLY) + 'echo "$(true)"\n', id="text-after-the-heredoc"),
    pytest.param(_shell(_DELETE_ORDERS) + "apply_patch < f.patch\n", id="call-then-file-call"),
    pytest.param(f"cat <<'EOF' | env apply_patch\n{_DELETE_ORDERS}\nEOF\n", id="piped-to-env-call"),
    pytest.param(f"cat <<'EOF' | env ap''ply_patch\n{_DELETE_ORDERS}\nEOF\n", id="piped-to-quoted-name"),
    pytest.param(f"cat > /tmp/p <<'EOF'\n{_DOCS_ONLY}\nEOF\nenv apply_patch < /tmp/p\n", id="file-into-env-call"),
    pytest.param(f"cat > notes.md <<'EOF'\napply_patch <<'X'\n{_DELETE_ORDERS}\nX\nEOF\n",
                 id="in-another-commands-heredoc"),
    # Delimiters and heredoc operators.
    pytest.param(f"apply_patch <<$+x\n{_DELETE_ORDERS}\n$+x\n", id="delimiter-with-dollar"),
    pytest.param(f"apply_patch <<$'EOF'\n{_DELETE_ORDERS}\nEOF\n", id="ansi-quoted-delimiter"),
    pytest.param(f"apply_patch <<E\\\nOF\n{_DOCS_ONLY}\nEOF\n", id="continuation-in-delimiter"),
    pytest.param(f"apply_patch <<\\\n-EOF\n{_TAB_DOCS}\n\tEOF\n", id="continuation-before-dash"),
    pytest.param(f"apply_patch <<-'EOF'\n{_TAB_HIDDEN}\n\tEOF\n", id="dash-heredoc"),
    pytest.param(f"apply_patch <<-EOF\n{_TAB_DOCS}\n\tEOF\n", id="dash-heredoc-unquoted"),
    pytest.param(f"apply_patch <<-'EOF'\n{_DOCS_ONLY}\nEOF\n", id="dash-heredoc-without-tabs"),
    pytest.param(f"true; apply_patch <<-'EOF'\n{_TAB_HIDDEN}\n\tEOF\n", id="after-true-dash-heredoc"),
    pytest.param(f"FOO=1 apply_patch <<-'EOF'\n{_TAB_HIDDEN}\n\tEOF\n", id="assignment-dash-heredoc"),
    pytest.param(f"(apply_patch <<-'EOF'\n{_TAB_HIDDEN}\n\tEOF\n)", id="subshell-dash-heredoc"),
    pytest.param(_shell(_DOCS_ONLY).replace("<<'EOF'", "3<<'EOF'", 1), id="heredoc-on-fd-3"),
    pytest.param(_shell(_DOCS_ONLY).replace("<<'EOF'", "< other.patch <<'EOF'", 1), id="file-then-heredoc"),
    pytest.param(_shell(_DOCS_ONLY).replace("<<'EOF'", "<<'EOF' < other.patch", 1), id="heredoc-then-file"),
    pytest.param(_shell(_DOCS_ONLY).replace("<<'EOF'", "<<'EOF' > out.txt", 1), id="heredoc-then-stdout"),
    pytest.param(_shell(_DOCS_ONLY).replace("apply_patch", 'apply_patch "$P"', 1), id="argument-beside-heredoc"),
    pytest.param("apply_patch <<EOF\n*** Begin Patch\n*** Update File: $F\n@@\n-a\n+b\n*** End Patch\nEOF\n",
                 id="variable-in-header"),
    pytest.param(_shell(_patch("**\\", "* Delete File: models/orders.sql"), delim="EOF"),
                 id="backslash-joining-a-header"),
    pytest.param(_shell(_patch("*** Add File: notes.txt", "+hi\\", "*** End Patch",
                               "*** Delete File: models/orders.sql"), delim="EOF"),
                 id="continuation-hiding-end-of-patch"),
    pytest.param("X=$'*** Begin Patch\\n*** Delete File: models/orders.sql\\n*** End Patch'\n"
                 "apply_patch <<EOF\n$X\nEOF\n", id="heredoc-from-a-variable"),
    # A delimiter that isn't a plain word, which Codex's parser may not match.
    pytest.param(f'apply_patch <<"E\\\\"\n{_patch("*** Add File: docs/a.md", "+x")}\nE\\\n'
                 "apply_patch < p.txt\nE\\\\\n", id="backslash-in-quoted-delimiter"),
    pytest.param(f"apply_patch <<'E$'\n{_DOCS_ONLY}\nE$\n", id="dollar-in-quoted-delimiter"),
    pytest.param(f"apply_patch <<'E OF'\n{_DOCS_ONLY}\nE OF\n", id="space-in-quoted-delimiter"),
    pytest.param(f"apply_patch <<\"E'\"\n{_DOCS_ONLY}\nE'\n", id="quote-in-quoted-delimiter"),
    pytest.param(f"apply_patch <<1EOF\n{_DOCS_ONLY}\n1EOF\n", id="delimiter-starting-with-digit"),
    # `$`, a backtick or a backslash anywhere in an unquoted body, which a real shell expands.
    pytest.param(_shell(_patch("*** Add File: docs/a.md", "+$(apply_patch < p.txt)"), delim="EOF"),
                 id="unquoted-substitution-in-hunk"),
    pytest.param(_shell(_patch("*** Add File: docs/a.md", "+`apply_patch < p.txt`"), delim="EOF"),
                 id="unquoted-backtick-in-hunk"),
    pytest.param(_shell(_patch("*** Update File: src/app.js", "@@", "-a", '+print("a\\n")'), delim="EOF"),
                 id="unquoted-backslash-in-hunk"),
    pytest.param(_shell(_patch(*_update("models/orders.sql", new="SELECT '$1' FROM {{ ref('raw') }}")),
                        prefix="cd . && ", delim="EOF"), id="unquoted-dollar-in-model-hunk"),
    pytest.param("apply_patch <<EOF\n*** Begin Patch\n*** Add File: docs/a.md\n+$(apply_patch < p.txt)\n"
                 "EOFX\n*** End Patch\nEOF\n", id="unquoted-substitution-and-delimiter-prefix"),
    # A body line another heredoc reader may take for the delimiter line.
    pytest.param(_shell(_patch("*** Add File: docs/a.md", "+x", "EOFX", "+y")), id="line-starting-with-delimiter"),
    pytest.param(_shell(_patch("*** Add File: docs/a.md", "+x", "EOF ", "+y")), id="delimiter-then-space"),
    pytest.param(_shell(_patch("*** Add File: docs/a.md", "+x", "EOF\t", "+y")), id="delimiter-then-tab"),
    pytest.param(_shell(_patch("*** Add File: docs/a.md", "+x", "  EOF", "+y")), id="indented-delimiter"),
    pytest.param(_shell(_DOCS_ONLY).replace("\nEOF\n", "\nEOF \n"), id="terminator-with-trailing-space"),
    # A second patch in a recognised body, which a real shell may apply on its own.
    pytest.param(_shell(_patch(*_update("models/orders.sql"), "+*** Begin Patch",
                               "*** Delete File: models/customers.sql")), id="patch-further-into-body"),
    pytest.param(_shell(_DOCS_ONLY + "\n" + _DELETE_ORDERS), id="two-patches-in-body"),
    pytest.param(_shell(_patch("*** Update File: docs/a.md", "@@", "-x", "+*** Begin \\", "Patch")),
                 id="patch-joined-by-continuation-in-body"),
    pytest.param(f"apply_patch <<'X'\n+x\n{_DELETE_ORDERS}\nX\n", id="patch-not-at-body-start"),
    # Arguments, files, pipes and here-strings.
    pytest.param(f"apply_patch '{_DOCS_ONLY}'", id="single-quoted-argument"),
    pytest.param(f"apply_patch '<<EOF\n{_DELETE_ORDERS}\nEOF'", id="wrapper-in-argument"),
    pytest.param(f"apply_patch '*** Begin'' Patch\n{_SPLIT_MODEL}'", id="single-quoted-split-begin"),
    pytest.param(f'apply_patch "*** Begin"" Patch\n{_SPLIT_MODEL}"', id="double-quoted-split-begin"),
    pytest.param(f"env apply_patch '*** Begin\\ Patch\n{_SPLIT_MODEL}'", id="backslash-in-begin"),
    pytest.param(f"apply_patch <<< '{_DOCS_ONLY}'", id="here-string"),
    pytest.param("apply_patch < /tmp/p.diff", id="file"),
    pytest.param('apply_patch "$(cat /tmp/p.diff)"', id="substituted-argument"),
    pytest.param("cat /tmp/p.diff | apply_patch", id="pipe"),
    pytest.param("apply_patch", id="bare-name"),
    pytest.param("0<p.txt env apply_patch", id="fd-redirect-before-name"),
    pytest.param("< p.txt env apply_patch", id="redirect-before-wrapper"),
    pytest.param("xargs -0 apply_patch < p.txt", id="xargs"),
    pytest.param("sudo -u root /usr/bin/applypatch < p.txt", id="sudo-full-path"),
    pytest.param('X="a b" apply_patch < p.txt', id="double-quoted-assignment-with-space"),
    pytest.param("X='a b' apply_patch < p.txt", id="single-quoted-assignment-with-space"),
    pytest.param('< "p 1.txt" apply_patch', id="quoted-redirect-target-first"),
    pytest.param("function f { apply_patch < p.txt; }; f", id="function-body"),
    pytest.param("command env -v apply_patch < p.txt", id="command-env-v"),
    # The name, unquoted by the shell.
    pytest.param("$'apply_patch' < p.txt", id="ansi-c-quoted-name"),
    *[pytest.param(_shell(_DELETE_ORDERS, delim="'PATCH'").replace("apply_patch", name, 1), id=f"name:{name}")
      for name in ["ap''ply_patch", 'ap""ply_patch', "apply\\_patch", "'apply_patch'", '"apply"_patch',
                   "apply\\\n_patch"]],
    # Docs-only and non-dbt patches, in forms Prevent doesn't check.
    pytest.param(_shell(_DOCS_ONLY, prefix="env "), id="docs-only-env"),
    pytest.param(f"env apply_patch <<'EOF'\n{_DOCS_ONLY}\nEOF\necho \"$HOME\"\n", id="docs-only-then-expansion"),
    pytest.param(_shell(_patch(*_update("models/orders.sql/")), prefix="env "), id="trailing-slash-env"),
    pytest.param(f"FOO=1 apply_patch <<'X'\n<<EOF\n{_DOCS_ONLY}\nEOF\nX\n", id="wrapper-line-after-assignment"),
    # Mentions.
    pytest.param("rg apply_patch", id="rg"),
    pytest.param("grep -rn apply_patch .", id="grep"),
    pytest.param("cat lib/apply_patch.py", id="file-name"),
    pytest.param('git commit -m "use apply_patch"', id="commit-message"),
    pytest.param("echo 'run apply_patch <<EOF later'", id="echo"),
    pytest.param("# apply_patch < x\nls", id="comment"),
    pytest.param("command -v apply_patch", id="command-v"),
]


class TestShellUnrecognised:
    @pytest.mark.parametrize("cmd", _OTHER_FORMS)
    def test_denied_unchecked_and_nothing_gated_or_tracked(self, project, capsys, cmd):
        (project / "p.txt").write_text(_DELETE_ORDERS + "\n")
        _unchecked_deny(_run_pre(cmd, project, capsys))
        assert _checked_paths(cmd, project, capsys) == []
        assert _edited() == []

    def test_denied_outside_a_dbt_project(self, tmp_path, capsys):
        _unchecked_deny(_run_pre("rg apply_patch", tmp_path, capsys))

    def test_denied_even_after_assessment(self, project, capsys):
        cache.mark_impact_check_verified(SESSION, "orders")
        _unchecked_deny(_run_pre(_shell(_DELETE_ORDERS, prefix="FOO=1 "), project, capsys))
        assert _edited() == []

    @pytest.mark.parametrize("cmd", ["rg apply_patc[h]", "ls", "git commit -F msg.txt", "ap${x}ply_patch"])
    def test_command_not_naming_it_is_not_denied(self, project, capsys, cmd):
        assert _run_pre(cmd, project, capsys) is None


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
        """In an unquoted heredoc a trailing backslash joins the next line, so a shell reads
        the `EOF` after it as body text. An unquoted body with a backslash isn't recognised."""
        text = "\n".join([
            "*** Begin Patch", "*** Add File: notes.txt", "+hi\\", "EOF",
            "*** Delete File: models/orders.sql", "*** End Patch",
        ])
        assert "+hi\\\nEOF\n" in text
        _unchecked_deny(_run_pre(f"apply_patch <<EOF\n{text}\nEOF\n", project, capsys))
        assert _edited() == []

    @pytest.mark.parametrize("cmd", [
        f"apply_patch <<'X'\n<<EOF\n{_DELETE_ORDERS}\nEOF\nX\n",
        f"apply_patch <<'X'\n\n\t{_DELETE_ORDERS}\nX\n",
    ])
    def test_wrapper_and_leading_blanks_are_part_of_the_body(self, project, capsys, cmd):
        cache.mark_impact_check_verified(SESSION, "orders")
        assert _run_pre(cmd, project, capsys) is None
        assert _edited() == ["orders"]

    # A quoted delimiter keeps `$`, backticks and backslashes in hunk lines as written.
    @pytest.mark.parametrize("delim", ["'EOF'", '"EOF"'])
    def test_quoted_expansions_in_hunk_allowed(self, project, capsys, delim):
        text = _patch("*** Update File: src/app.js", "@@", "-const s = 'a';",
                      "+const s = `${name}`;", "+print(\"a\\n\")")
        assert _run_pre(_shell(text, delim=delim), project, capsys) is None

    def test_quoted_expansions_in_hunk_still_gate_models(self, project, capsys):
        text = _patch(*_update("models/orders.sql", new="SELECT '$1' FROM {{ ref('raw') }}"))
        out = _run_pre(_shell(text, prefix="cd . && "), project, capsys)
        assert _denied(out)
        assert "orders" in out["permissionDecisionReason"]
        assert "couldn't check" not in out["permissionDecisionReason"]

    def test_second_begin_patch_anywhere_in_the_body_is_not_recognised(self):
        """Even inside a hunk line: if Codex's parser didn't match, a real shell may hand
        that text to apply_patch, so only a body with one patch, at its start, counts."""
        from shell_patch import find_invocation
        assert find_invocation(_shell(_DOCS_ONLY)) is not None
        assert find_invocation(_shell(_patch("*** Update File: docs/a.md", "@@", "-x", "+*** Begin Patch"))) is None

    def test_quoted_name_in_a_hunk_line_still_recognised(self, project, capsys):
        cmd = _shell(_patch("*** Update File: docs/a.md", "@@", "-x", "+ap''ply_patch", '+echo "$HOME"'))
        assert _run_pre(cmd, project, capsys) is None


# --- Shell: switches and fallbacks ---

class TestShellSwitches:
    @pytest.mark.parametrize("cmd", [
        "apply_patch < /tmp/p.diff",
        _shell(_DELETE_ORDERS, prefix="env "),
        "rg apply_patch",
    ])
    def test_disable_switch_suppresses_unchecked_deny(self, project, capsys, monkeypatch, cmd):
        monkeypatch.setenv("MC_PREVENT_HOOKS_DISABLED", "1")
        assert _run_pre(cmd, project, capsys) is None

    def test_any_error_reading_an_apply_patch_command_denied(self, project, capsys):
        with patch("bash_hook.find_invocation", side_effect=ValueError("boom")):
            out = _run_pre(_shell(_DOCS_ONLY), project, capsys)
        _unchecked_deny(out)
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

    def test_commit_message_naming_apply_patch_denied(self, project, capsys):
        from lib.protocol import HookOutput
        with patch("bash_hook.evaluate_pre_commit", return_value=HookOutput(action="context", context="ctx")):
            _unchecked_deny(_run_pre('git commit -m "use apply_patch"', project, capsys))

    def test_commit_message_naming_apply_patch_checked_when_disabled(self, project, capsys, monkeypatch):
        """With the switch on, a command naming apply_patch is like any other command."""
        from lib.protocol import HookOutput
        monkeypatch.setenv("MC_PREVENT_HOOKS_DISABLED", "1")
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
        _unchecked_deny(_run_pre(cmd, project, capsys))
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
