"""Reading staged dbt models from a real git index."""
import os
import re
import subprocess

import pytest

from lib.protocol import StagedModel, _get_staged_model_tables, _read_staged_models

DBT_SQL = "select * from {{ ref('raw_orders') }}\n"
PLAIN_SQL = "select 1\n"


def git(repo, *args):
    return subprocess.run(
        ["git", *args], cwd=repo, check=True, capture_output=True, text=True,
    ).stdout


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-q", "-b", "main")
    git(root, "config", "user.name", "Test")
    git(root, "config", "user.email", "test@example.com")
    git(root, "config", "commit.gpgsign", "false")
    (root / "README.md").write_text("hi\n")
    git(root, "add", "README.md")
    git(root, "commit", "-q", "-m", "init")
    return root


def write(repo, rel, text):
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def blob_id(repo, rel):
    return git(repo, "rev-parse", f":{rel}").strip()


class TestLegacyStagedTablesJoin:
    """_get_staged_model_tables backs evaluate_pre_commit in every plugin."""

    def test_root_cwd_finds_model(self, repo):
        write(repo, "models/orders.sql", DBT_SQL)
        git(repo, "add", ".")
        assert _get_staged_model_tables(str(repo)) == ["orders"]

    def test_subdirectory_cwd_reads_the_real_file(self, repo):
        # git prints paths relative to the repo root. Joining them to a
        # subdirectory cwd points at a file that doesn't exist, and a missing
        # file under models/ counts as a model whatever it holds.
        write(repo, "dbt/models/plain.sql", PLAIN_SQL)
        git(repo, "add", ".")
        assert _get_staged_model_tables(str(repo / "dbt")) == []

    def test_subdirectory_cwd_still_finds_real_model(self, repo):
        write(repo, "dbt/models/orders.sql", DBT_SQL)
        git(repo, "add", ".")
        assert _get_staged_model_tables(str(repo / "dbt" / "models")) == ["orders"]


class TestReadStagedModels:
    def test_reports_toplevel_paths_and_full_blob_ids(self, repo):
        write(repo, "dbt/models/orders.sql", DBT_SQL)
        git(repo, "add", ".")
        toplevel, models = _read_staged_models(str(repo / "dbt"))
        assert os.path.realpath(toplevel) == os.path.realpath(repo)
        assert models == [StagedModel(
            path="dbt/models/orders.sql",
            blob=blob_id(repo, "dbt/models/orders.sql"),
            table="orders",
        )]
        assert re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", models[0].blob)

    def test_classifies_the_staged_content_not_the_worktree(self, repo):
        write(repo, "models/orders.sql", DBT_SQL)
        git(repo, "add", ".")
        write(repo, "models/orders.sql", PLAIN_SQL)
        _, models = _read_staged_models(str(repo))
        assert [m.table for m in models] == ["orders"]

    def test_plain_staged_content_is_not_a_model_even_if_worktree_is(self, repo):
        write(repo, "models/orders.sql", PLAIN_SQL)
        git(repo, "add", ".")
        write(repo, "models/orders.sql", DBT_SQL)
        _, models = _read_staged_models(str(repo))
        assert models == []

    def test_staged_deletion_of_a_model_is_reported(self, repo):
        write(repo, "models/orders.sql", DBT_SQL)
        git(repo, "add", ".")
        git(repo, "commit", "-q", "-m", "add orders")
        git(repo, "rm", "-q", "models/orders.sql")
        _, models = _read_staged_models(str(repo))
        assert len(models) == 1
        assert models[0].table == "orders"
        assert models[0].path == "models/orders.sql"
        assert set(models[0].blob) == {"0"}

    def test_staged_deletion_of_plain_sql_is_not_a_model(self, repo):
        write(repo, "models/plain.sql", PLAIN_SQL)
        git(repo, "add", ".")
        git(repo, "commit", "-q", "-m", "add plain")
        git(repo, "rm", "-q", "models/plain.sql")
        _, models = _read_staged_models(str(repo))
        assert models == []

    def test_rename_reports_the_new_name(self, repo):
        write(repo, "models/orders.sql", DBT_SQL)
        git(repo, "add", ".")
        git(repo, "commit", "-q", "-m", "add orders")
        git(repo, "mv", "models/orders.sql", "models/orders_v2.sql")
        _, models = _read_staged_models(str(repo))
        assert [m.table for m in models] == ["orders_v2"]

    def test_macro_and_non_model_files(self, repo):
        write(repo, "macros/cents.sql", "{% macro cents(x) %}{{ x }}/100{% endmacro %}\n")
        write(repo, "seeds/raw.sql", DBT_SQL)
        write(repo, "models/schema.yml", "version: 2\n")
        git(repo, "add", ".")
        _, models = _read_staged_models(str(repo))
        assert [m.table for m in models] == ["macro:cents"]

    def test_reads_blobs_only_for_sql_files(self, repo, monkeypatch):
        # Reading every staged blob would make large commits slow.
        import lib.protocol as protocol
        write(repo, "models/orders.sql", DBT_SQL)
        for i in range(5):
            write(repo, f"docs/note{i}.md", "x\n")
        git(repo, "add", ".")
        calls = []
        real_git = protocol._git

        def spy(args, cwd, text=True):
            calls.append(args[0])
            return real_git(args, cwd, text=text)

        monkeypatch.setattr(protocol, "_git", spy)
        _, models = _read_staged_models(str(repo))
        assert [m.table for m in models] == ["orders"]
        assert calls.count("cat-file") == 1

    def test_nothing_staged(self, repo):
        toplevel, models = _read_staged_models(str(repo))
        assert os.path.realpath(toplevel) == os.path.realpath(repo)
        assert models == []

    def test_not_a_repo(self, tmp_path):
        assert _read_staged_models(str(tmp_path)) is None

    def test_missing_directory(self, tmp_path):
        assert _read_staged_models(str(tmp_path / "nope")) is None
