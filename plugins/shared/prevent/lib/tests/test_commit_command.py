"""Tests for the commit-command grammar used by the pause-once pre-commit checkpoint.

parse_commit_command returns a CommitTarget only for a standalone `git commit` that
commits exactly the current index. Every other shape returns None, so the checkpoint
stays silent rather than pausing a command whose effect it can't predict.
"""
import os

import pytest

from lib.commit_command import CommitTarget, parse_commit_command

CWD = "/work/repo"


def target(command, cwd=CWD):
    return parse_commit_command(command, cwd)


class TestSupportedForms:
    @pytest.mark.parametrize("command", [
        "git commit",
        "git commit -m 'add orders'",
        'git commit -m "add orders"',
        "git commit --message='add orders'",
        "git commit --message 'add orders'",
        "git commit -F msg.txt",
        "git commit --file=msg.txt",
        "git commit -s -m x",
        "git commit -sm x",
        "git commit -nm x",
        "git commit --no-verify -m x",
        "git commit -q -m x",
        "git commit --allow-empty -m x",
        "git commit --author='A <a@b.c>' -m x",
        "git commit --trailer 'Co-Authored-By: X <x@y.z>' -m x",
        "git commit -m x --",
        "  git commit -m x  ",
        "git commit -m x\n",
        "/usr/bin/git commit -m x",
        "GIT_AUTHOR_NAME=A git commit -m x",
        "GIT_COMMITTER_DATE='2026-01-01' GIT_AUTHOR_DATE=x git commit -m x",
        "git -c user.name=A -c user.email=a@b.c commit -m x",
        "git --no-pager commit -m x",
    ])
    def test_accepted_in_cwd(self, command):
        assert target(command) == CommitTarget(repo_dir=CWD, amend=False)

    def test_amend(self):
        assert target("git commit --amend --no-edit") == CommitTarget(repo_dir=CWD, amend=True)

    def test_message_that_looks_like_dry_run_is_a_real_commit(self):
        # Option arguments are consumed, not read as options.
        assert target("git commit -m '--dry-run'") == CommitTarget(repo_dir=CWD, amend=False)
        assert target("git commit -m --dry-run") == CommitTarget(repo_dir=CWD, amend=False)

    def test_message_containing_operators_is_one_word(self):
        assert target("git commit -m 'a && b; c | d > e'") == CommitTarget(repo_dir=CWD, amend=False)
        assert target('git commit -m "a && b; c"') == CommitTarget(repo_dir=CWD, amend=False)

    def test_heredoc_message_via_command_substitution(self):
        command = (
            'git commit -m "$(cat <<\'EOF\'\n'
            "Fix orders\n"
            "\n"
            "A quote \" and a paren ) on a later line\n"
            "EOF\n"
            ')"'
        )
        assert target(command) == CommitTarget(repo_dir=CWD, amend=False)

    def test_backtick_substitution_in_message(self):
        assert target('git commit -m "`cat msg`"') == CommitTarget(repo_dir=CWD, amend=False)

    @pytest.mark.parametrize("command", [
        "git commit -m x 2>&1",
        "git commit -m x > /dev/null",
        "git commit -m x >/dev/null 2>&1",
        "git commit -m x &> out.log",
        "git commit -m x < /dev/null",
    ])
    def test_redirections_are_ignored(self, command):
        assert target(command) == CommitTarget(repo_dir=CWD, amend=False)


class TestTrailingCommands:
    """Commands after the commit can't change what it records, so they're allowed.

    Agents often run `git commit ... && git status` as one command.
    """

    @pytest.mark.parametrize("command", [
        "git commit -m x && git status",
        "git commit -m x; git status",
        "git commit -m x && git log --oneline -1",
        "git commit -m x\ngit status",
        "git commit -m x || echo failed",
        "git commit -m x | cat",
        "git commit -m x && git push",
        "git commit -m x &",
        "git commit -m x;",
        "git commit -m x && (git status)",
        "git commit -m x && { git status; }",
        'git commit -m "$(cat <<\'EOF\'\nmsg\nEOF\n)" && git status --short',
    ])
    def test_accepted(self, command):
        assert target(command) == CommitTarget(repo_dir=CWD, amend=False)

    def test_with_cd_prefix(self):
        assert target("cd dbt && git commit -m x && git status") == \
            CommitTarget(repo_dir="/work/repo/dbt", amend=False)

    @pytest.mark.parametrize("command", [
        "git commit -am x && git status",
        "git commit --dry-run && git status",
    ])
    def test_still_unsupported(self, command):
        assert target(command) is None


class TestAddBeforeCommit:
    """`git add <file paths> && git commit` is how agents often commit their own edits.

    The parser returns the named paths, resolved against the directory git add runs in,
    so the checkpoint can work out what the commit will record.
    """

    def test_one_path(self):
        assert target("git add models/orders.sql && git commit -m x") == CommitTarget(
            repo_dir=CWD, amend=False, add_paths=("/work/repo/models/orders.sql",))

    def test_several_paths_and_adds(self):
        t = target("git add a.sql b.sql && git add -- -odd.sql && git commit -m x")
        assert t.add_paths == ("/work/repo/a.sql", "/work/repo/b.sql", "/work/repo/-odd.sql")

    def test_add_and_commit_with_dash_c(self):
        t = target("git -C /r add models/o.sql && git -C /r commit -m x && git log -1")
        assert t == CommitTarget(repo_dir="/r", amend=False, add_paths=("/r/models/o.sql",))

    def test_cd_prefix(self):
        t = target("cd dbt && git add models/o.sql && git commit -m x")
        assert t == CommitTarget(repo_dir="/work/repo/dbt", amend=False,
                                 add_paths=("/work/repo/dbt/models/o.sql",))

    def test_paths_are_normalized(self):
        assert target("git add ./models/../models/o.sql && git commit -m x").add_paths == \
            ("/work/repo/models/o.sql",)

    def test_quoted_path_with_space(self):
        assert target("git add 'models/my orders.sql' && git commit -m x").add_paths == \
            ("/work/repo/models/my orders.sql",)

    def test_dot_is_passed_on_as_a_directory(self):
        # The checkpoint, not the parser, decides that a directory is out of scope.
        assert target("git add . && git commit -m x").add_paths == ("/work/repo",)

    def test_standalone_commit_names_no_paths(self):
        assert target("git commit -m x").add_paths == ()

    @pytest.mark.parametrize("command", [
        "git add -A && git commit -m x",
        "git add -u && git commit -m x",
        "git add --all && git commit -m x",
        "git add -p models/o.sql && git commit -m x",
        "git add -f models/o.sql && git commit -m x",
        "git add && git commit -m x",
        "git add -- && git commit -m x",
        "git add *.sql && git commit -m x",
        "git add 'models/*.sql' && git commit -m x",
        "git add 'models/o?.sql' && git commit -m x",
        "git add 'models/[ab].sql' && git commit -m x",
        "git add :/models/o.sql && git commit -m x",
        "git add $F && git commit -m x",
        'git add "$(ls)" && git commit -m x',
        "git add models/o.sql || git commit -m x",
        "git add models/o.sql | git commit -m x",
        "git add models/o.sql & git commit -m x",
        "git add models/o.sql\ngit commit -m x",
        "GIT_INDEX_FILE=i git add models/o.sql && git commit -m x",
        "git --git-dir=/x add models/o.sql && git commit -m x",
        "git add models/o.sql && git status && git commit -m x",
        "git status && git add models/o.sql && git commit -m x",
        "git add models/o.sql && git commit -am x",
        "git add models/o.sql && git commit -m x models/o.sql",
        "git rm models/o.sql && git commit -m x",
        "git add models/o.sql && cd x && git commit -m x",
    ])
    def test_unsupported(self, command):
        assert target(command) is None


class TestNewBranchBeforeCommit:
    """Creating a branch from HEAD keeps the index, so it may come before the add or commit.

    Agents told to branch first often run it in the same command as the commit.
    """

    @pytest.mark.parametrize("command", [
        "git checkout -b feat && git commit -m x",
        "git checkout -B feat && git commit -m x",
        "git switch -c feat && git commit -m x",
        "git switch -C feat && git commit -m x",
        "git -C /work/repo checkout -b jonathan/review-orders && git commit -m x",
    ])
    def test_accepted(self, command):
        assert target(command) == CommitTarget(repo_dir=CWD, amend=False)

    def test_with_add_and_cd(self):
        t = target("cd dbt && git checkout -b feat && git add models/o.sql && git commit -m x && git status")
        assert t == CommitTarget(repo_dir="/work/repo/dbt", amend=False,
                                 add_paths=("/work/repo/dbt/models/o.sql",))

    def test_after_the_add(self):
        assert target("git add o.sql && git switch -c feat && git commit -m x").add_paths == \
            ("/work/repo/o.sql",)

    @pytest.mark.parametrize("command", [
        "git checkout -b feat main && git commit -m x",
        "git switch -c feat origin/main && git commit -m x",
        "git checkout main && git commit -m x",
        "git switch main && git commit -m x",
        "git checkout --orphan feat && git commit -m x",
        "git switch --orphan feat && git commit -m x",
        "git checkout -b && git commit -m x",
        "git checkout -b '' && git commit -m x",
        "git checkout -b -x && git commit -m x",
        "git checkout -bfeat && git commit -m x",
        "git checkout -b feat -- o.sql && git commit -m x",
        "git checkout -b $B && git commit -m x",
        "git checkout -b feat; git commit -m x",
        "git checkout -b feat || git commit -m x",
        "git checkout -c feat && git commit -m x",
        "git switch -b feat && git commit -m x",
        "git checkout -b feat",
    ])
    def test_unsupported(self, command):
        assert target(command) is None


class TestDirectory:
    def test_dash_c_relative(self):
        assert target("git -C dbt commit -m x") == CommitTarget(repo_dir="/work/repo/dbt", amend=False)

    def test_dash_c_absolute(self):
        assert target("git -C /elsewhere commit -m x") == CommitTarget(repo_dir="/elsewhere", amend=False)

    def test_dash_c_chains(self):
        assert target("git -C a -C b commit") == CommitTarget(repo_dir="/work/repo/a/b", amend=False)

    def test_dash_c_home(self):
        expected = os.path.join(os.path.expanduser("~"), "repo")
        assert target("git -C ~/repo commit") == CommitTarget(repo_dir=expected, amend=False)

    def test_cd_prefix(self):
        assert target("cd dbt && git commit -m x") == CommitTarget(repo_dir="/work/repo/dbt", amend=False)

    def test_cd_prefix_quoted_dir(self):
        assert target("cd 'my dbt' && git commit -m x") == CommitTarget(repo_dir="/work/repo/my dbt", amend=False)

    @pytest.mark.parametrize("command", [
        "git -C $REPO commit -m x",
        'git -C "$REPO" commit -m x',
        "git -C `pwd` commit -m x",
        "cd $REPO && git commit -m x",
        "cd && git commit -m x",
        "cd - && git commit -m x",
        "cd a b && git commit -m x",
        "cd a; git commit -m x",
        "cd a || git commit -m x",
    ])
    def test_unknowable_directory_is_unsupported(self, command):
        assert target(command) is None


class TestUnsupported:
    @pytest.mark.parametrize("command", [
        # dry runs
        "git commit --dry-run",
        "git commit --short",
        "git commit --long",
        "git commit --porcelain",
        # commits something other than the current index
        "git commit -a -m x",
        "git commit -am x",
        "git commit --all -m x",
        "git commit -m x models/orders.sql",
        "git commit -m x -- models/orders.sql",
        "git commit --only models/orders.sql",
        "git commit -o -m x models/orders.sql",
        "git commit --include -m x models/orders.sql",
        "git commit -i -m x models/orders.sql",
        "git commit -p",
        "git commit --patch",
        "git commit --interactive",
        "git commit --pathspec-from-file=f",
        # unknown options are not guessed at
        "git commit --frobnicate",
        "git commit -X",
        # repo or index overrides
        "GIT_INDEX_FILE=/tmp/idx git commit -m x",
        "GIT_DIR=/x/.git git commit -m x",
        "GIT_WORK_TREE=/x git commit -m x",
        "git --git-dir=/x/.git commit -m x",
        "git --work-tree /x commit -m x",
        "git --bare commit -m x",
        # compound commands
        "git add models/orders.sql; git commit -m x",
        "git add .\ngit commit -m x",
        "(git commit -m x)",
        "{ git commit -m x; }",
        # wrappers
        "env GIT_DIR=x git commit -m x",
        "sudo git commit -m x",
        "time git commit -m x",
        "command git commit -m x",
        # malformed
        "git commit -m 'unterminated",
        'git commit -m "unterminated',
        "git commit -m",
        "git -C",
    ])
    def test_unsupported(self, command):
        assert target(command) is None


class TestNotACommit:
    @pytest.mark.parametrize("command", [
        "",
        "ls -la",
        "git status",
        "git commit-tree HEAD^{tree}",
        "git log --grep 'git commit'",
        'echo "git commit"',
        "echo git commit",
        "printf '%s' '&&' git commit",
        "printf '%s' ';' git commit -m x",
        "gitx commit",
        "git --version",
        "git help commit",
        "git",
    ])
    def test_not_a_commit(self, command):
        assert target(command) is None
