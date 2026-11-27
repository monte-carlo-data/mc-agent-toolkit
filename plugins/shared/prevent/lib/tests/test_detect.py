import os
import pytest
from lib.detect import extract_table_name, is_dbt_model, is_dbt_schema_file, is_macro_file


class TestIsDbtModel:
    def test_sql_file_in_models_with_ref(self, tmp_path):
        """A .sql file under models/ with {{ ref() }} is a dbt model."""
        model_dir = tmp_path / "project" / "models" / "staging"
        model_dir.mkdir(parents=True)
        sql_file = model_dir / "client_hub_master.sql"
        sql_file.write_text("SELECT * FROM {{ ref('upstream_table') }}")
        assert is_dbt_model(str(sql_file)) is True

    def test_sql_file_in_models_with_source(self, tmp_path):
        """A .sql file under models/ with {{ source() }} is a dbt model."""
        model_dir = tmp_path / "project" / "models"
        model_dir.mkdir(parents=True)
        sql_file = model_dir / "raw_orders.sql"
        sql_file.write_text("SELECT * FROM {{ source('raw', 'orders') }}")
        assert is_dbt_model(str(sql_file)) is True

    def test_sql_file_outside_models(self, tmp_path):
        """A .sql file NOT under models/ is not a dbt model."""
        other_dir = tmp_path / "project" / "scripts"
        other_dir.mkdir(parents=True)
        sql_file = other_dir / "adhoc.sql"
        sql_file.write_text("SELECT * FROM {{ ref('something') }}")
        assert is_dbt_model(str(sql_file)) is False

    def test_sql_file_in_seeds(self, tmp_path):
        """Seeds directory should be excluded."""
        seed_dir = tmp_path / "project" / "seeds"
        seed_dir.mkdir(parents=True)
        sql_file = seed_dir / "seed_data.sql"
        sql_file.write_text("SELECT * FROM {{ ref('x') }}")
        assert is_dbt_model(str(sql_file)) is False

    def test_sql_file_in_macros(self, tmp_path):
        """Macros directory should be gated (not excluded) — macro changes affect all calling models."""
        macro_dir = tmp_path / "project" / "macros"
        macro_dir.mkdir(parents=True)
        sql_file = macro_dir / "helper.sql"
        sql_file.write_text("{% macro helper() %} SELECT 1 {% endmacro %}")
        assert is_dbt_model(str(sql_file)) is True

    def test_sql_file_in_analyses(self, tmp_path):
        """Analyses directory should be excluded."""
        dir_ = tmp_path / "project" / "analyses"
        dir_.mkdir(parents=True)
        sql_file = dir_ / "report.sql"
        sql_file.write_text("SELECT * FROM {{ ref('x') }}")
        assert is_dbt_model(str(sql_file)) is False

    def test_sql_file_in_snapshots(self, tmp_path):
        """Snapshots directory should be gated (not excluded) — snapshots control historical tracking."""
        dir_ = tmp_path / "project" / "snapshots"
        dir_.mkdir(parents=True)
        sql_file = dir_ / "snap.sql"
        sql_file.write_text("{% snapshot snap %} SELECT * FROM {{ ref('x') }} {% endsnapshot %}")
        assert is_dbt_model(str(sql_file)) is True

    def test_sql_file_without_ref_or_source(self, tmp_path):
        """A .sql file in models/ without ref/source is not a dbt model."""
        model_dir = tmp_path / "project" / "models"
        model_dir.mkdir(parents=True)
        sql_file = model_dir / "plain.sql"
        sql_file.write_text("SELECT 1 AS id")
        assert is_dbt_model(str(sql_file)) is False

    def test_yml_file_in_models_not_matched(self, tmp_path):
        """A .yml file under models/ is NOT a dbt model (tracked separately as schema file)."""
        model_dir = tmp_path / "project" / "models"
        model_dir.mkdir(parents=True)
        yml_file = model_dir / "schema.yml"
        yml_file.write_text("version: 2\nmodels:\n  - name: foo")
        assert is_dbt_model(str(yml_file)) is False

    def test_yaml_file_in_models_not_matched(self, tmp_path):
        """A .yaml file under models/ is NOT a dbt model (tracked separately)."""
        model_dir = tmp_path / "project" / "models"
        model_dir.mkdir(parents=True)
        yml_file = model_dir / "schema.yaml"
        yml_file.write_text("version: 2\nmodels:\n  - name: foo")
        assert is_dbt_model(str(yml_file)) is False

    def test_non_sql_non_yml_file(self, tmp_path):
        """A .py file under models/ is not a dbt model."""
        model_dir = tmp_path / "project" / "models"
        model_dir.mkdir(parents=True)
        py_file = model_dir / "script.py"
        py_file.write_text("print('hello')")
        assert is_dbt_model(str(py_file)) is False

    def test_ref_beyond_50_lines(self, tmp_path):
        """ref() past line 50 should not count."""
        model_dir = tmp_path / "project" / "models"
        model_dir.mkdir(parents=True)
        sql_file = model_dir / "deep_ref.sql"
        lines = ["-- comment\n"] * 55 + ["SELECT * FROM {{ ref('x') }}"]
        sql_file.write_text("".join(lines))
        assert is_dbt_model(str(sql_file)) is False

    def test_nonexistent_sql_in_models_is_new_model(self):
        """A nonexistent .sql file under models/ is treated as a new model."""
        assert is_dbt_model("/nonexistent/models/foo.sql") is True

    def test_nonexistent_file_outside_models(self):
        """A nonexistent file outside models/ returns False."""
        assert is_dbt_model("/nonexistent/scripts/foo.sql") is False


class TestExtractTableName:
    def test_simple_sql(self):
        assert extract_table_name("/project/models/staging/client_hub_master.sql") == "client_hub_master"

    def test_yml_file(self):
        assert extract_table_name("/project/models/schema.yml") == "schema"

    def test_nested_path(self):
        assert extract_table_name("/a/b/c/models/staging/finance/orders.sql") == "orders"


def _case_insensitive_fs(path) -> bool:
    probe = path / "CaseProbe"
    probe.write_text("")
    try:
        return os.path.exists(path / "caseprobe")
    finally:
        probe.unlink()


class TestFolderNameCase:
    """A folder named like a dbt path but in another case is the same folder on a
    case-insensitive filesystem (macOS, Windows), so it is gated as one. On a case-sensitive
    filesystem that costs at most an extra assessment, which is the safe side."""

    def test_new_file_under_upper_case_models_dir(self, tmp_path):
        assert is_dbt_model(str(tmp_path / "MODELS" / "orders.sql")) is True
        assert is_dbt_model(str(tmp_path / "Models" / "staging" / "Orders.Sql")) is True

    def test_custom_model_path_in_another_case(self, tmp_path):
        (tmp_path / "dbt_project.yml").write_text("model-paths: ['Transformations']\n")
        assert is_dbt_model(str(tmp_path / "transformations" / "orders.sql")) is True

    def test_existing_model_reached_through_another_case(self, tmp_path):
        if not _case_insensitive_fs(tmp_path):
            pytest.skip("needs a case-insensitive filesystem")
        (tmp_path / "models").mkdir()
        (tmp_path / "models" / "orders.sql").write_text("SELECT * FROM {{ ref('raw') }}")
        assert is_dbt_model(str(tmp_path / "MODELS" / "orders.sql")) is True

    def test_excluded_dir_in_another_case_does_not_ungate(self, tmp_path):
        """Seeds/analyses still match exactly: widening an exclusion would let a model through."""
        assert is_dbt_model(str(tmp_path / "models" / "SEEDS" / "orders.sql")) is True

    def test_macro_dir_in_another_case_is_gated_but_named_as_on_main(self, tmp_path):
        """Naming matches macro folders in exact case, as main does: a name main gives a
        model never turns into a macro name, which would drop it from the commit list."""
        path = str(tmp_path / "MACROS" / "helper.sql")
        assert is_dbt_model(path) is True
        assert is_macro_file(path) is False
        assert extract_table_name(path) == "helper"

    def test_model_under_a_differently_cased_macros_folder_keeps_its_name(self, tmp_path):
        path = str(tmp_path / "Macros" / "models" / "x.sql")
        assert is_dbt_model(path) is True
        assert extract_table_name(path) == "x"

    def test_schema_file_under_upper_case_models_dir(self, tmp_path):
        assert is_dbt_schema_file(str(tmp_path / "MODELS" / "schema.yml")) is True


def _project_under(tmp_path, *ancestors):
    """A dbt project whose folder sits below the given ancestor folders."""
    project = tmp_path.joinpath(*ancestors, "proj")
    project.mkdir(parents=True)
    (project / "dbt_project.yml").write_text("name: proj\n")
    return project


class TestFoldersAboveTheProject:
    """With a dbt_project.yml, only the folders below the project count: a folder above it
    that happens to share a dbt folder name says nothing about the file."""

    @pytest.mark.parametrize("ancestor", ["Macros", "macros"])
    def test_macros_ancestor_does_not_make_a_model_a_macro(self, tmp_path, ancestor):
        path = str(_project_under(tmp_path, ancestor) / "models" / "orders.sql")
        assert is_dbt_model(path) is True
        assert is_macro_file(path) is False
        assert extract_table_name(path) == "orders"

    @pytest.mark.parametrize("ancestor", ["seeds", "analyses"])
    def test_excluded_ancestor_does_not_ungate_models(self, tmp_path, ancestor):
        project = _project_under(tmp_path, ancestor)
        assert is_dbt_model(str(project / "models" / "orders.sql")) is True
        assert is_dbt_schema_file(str(project / "models" / "schema.yml")) is True

    def test_models_ancestor_still_gates_other_folders_as_on_main(self, tmp_path):
        """Gating is never narrower than main, which matches folder names anywhere in the
        path against the nearest project's settings; that costs at most an extra assessment."""
        project = _project_under(tmp_path, "models")
        assert is_dbt_model(str(project / "scripts" / "x.sql")) is True
        assert is_dbt_schema_file(str(project / "scripts" / "x.yml")) is True

    def test_folders_below_the_project_still_count(self, tmp_path):
        project = _project_under(tmp_path, "models")
        assert is_dbt_model(str(project / "seeds" / "x.sql")) is False
        assert extract_table_name(str(project / "macros" / "helper.sql")) == "macro:helper"

    def test_relative_path_is_resolved_against_the_project(self, tmp_path, monkeypatch):
        project = _project_under(tmp_path, "seeds", "Macros")
        monkeypatch.chdir(project)
        assert is_dbt_model("models/orders.sql") is True
        assert extract_table_name("models/orders.sql") == "orders"
        assert is_dbt_model("scripts/x.sql") is False

    def test_backslash_path_without_a_project_matches_its_folders(self):
        assert is_dbt_model("C:\\no_such_dir\\models\\orders.sql") is True
        assert is_dbt_model("C:\\no_such_dir\\seeds\\orders.sql") is False
        assert is_macro_file("C:\\no_such_dir\\macros\\helper.sql") is True


_MODEL_SQL = "SELECT * FROM {{ ref('raw') }}"
_MACRO_SQL = "{% macro helper() %}1{% endmacro %}"


def _write(path, text=_MODEL_SQL):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return str(path)


def _project(folder, yml="name: p\n"):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "dbt_project.yml").write_text(yml)
    return folder


class TestNestedProjects:
    """Gating is main's rule (nearest project's folder names anywhere in the path) united
    with an exact check against every project above the file: the file sits inside one of
    that project's configured model/macro/snapshot folders and not inside one of its seed
    or analysis folders. Names come from the exact check when any project contains the file."""

    def test_stray_project_in_models_does_not_ungate_models(self, tmp_path):
        outer = _project(tmp_path / "outer")
        _project(outer / "models")
        for path in (outer / "models" / "top.sql", outer / "models" / "staging" / "stg.sql"):
            path = _write(path)
            assert is_dbt_model(path) is True
            assert is_macro_file(path) is False
            assert extract_table_name(path) == os.path.splitext(os.path.basename(path))[0]
        assert is_dbt_schema_file(str(outer / "models" / "schema.yml")) is True

    def test_stray_project_in_a_models_subfolder_does_not_ungate_it(self, tmp_path):
        outer = _project(tmp_path / "outer")
        _project(outer / "models" / "sub")
        path = _write(outer / "models" / "sub" / "x.sql")
        assert is_dbt_model(path) is True
        assert extract_table_name(path) == "x"
        assert is_dbt_schema_file(str(outer / "models" / "sub" / "schema.yml")) is True

    def test_seeds_folder_between_projects_does_not_ungate_inner_models(self, tmp_path):
        inner = _project(_project(tmp_path / "outer") / "seeds" / "inner")
        path = _write(inner / "models" / "x.sql")
        assert is_dbt_model(path) is True
        assert extract_table_name(path) == "x"
        assert is_dbt_schema_file(str(inner / "models" / "schema.yml")) is True

    def test_macros_folder_between_projects_does_not_make_a_model_a_macro(self, tmp_path):
        inner = _project(_project(tmp_path / "outer") / "Macros" / "inner")
        path = _write(inner / "models" / "x.sql")
        assert is_dbt_model(path) is True
        assert is_macro_file(path) is False
        assert extract_table_name(path) == "x"

    def test_inner_project_under_outer_custom_model_path(self, tmp_path):
        outer = _project(tmp_path / "outer", "model-paths: ['transformations']\n")
        _project(outer / "transformations" / "sub")
        path = _write(outer / "transformations" / "sub" / "x.sql")
        assert is_dbt_model(path) is True
        assert extract_table_name(path) == "x"
        assert is_dbt_schema_file(str(outer / "transformations" / "sub" / "schema.yml")) is True

    def test_one_projects_exclusion_does_not_ungate_anothers_model(self, tmp_path):
        """The inner project claims `staging` as a model folder and also excludes it, so only
        the outer project's claim can gate the file."""
        outer = _project(tmp_path / "outer")
        _project(outer / "models", "model-paths: ['staging']\nanalysis-paths: ['staging']\n")
        path = _write(outer / "models" / "staging" / "stg.sql")
        assert is_dbt_model(path) is True
        assert is_dbt_schema_file(str(outer / "models" / "staging" / "schema.yml")) is True

    def test_models_folder_between_projects_gates_as_on_main(self, tmp_path):
        outer = _project(tmp_path / "outer", "model-paths: ['transformations']\n")
        inner = _project(outer / "models" / "inner")
        assert is_dbt_model(_write(inner / "scripts" / "x.sql")) is True
        assert is_dbt_model(_write(inner / "models" / "y.sql")) is True

    def test_macro_of_inner_project_only_is_named_as_macro(self, tmp_path):
        inner = _project(_project(tmp_path / "outer") / "tools" / "inner")
        path = _write(inner / "macros" / "helper.sql", _MACRO_SQL)
        assert is_dbt_model(path) is True
        assert is_macro_file(path) is True
        assert extract_table_name(path) == "macro:helper"

    def test_configured_exclusion_inside_a_model_folder_applies(self, tmp_path):
        project = _project(tmp_path / "p", "model-paths: ['src']\nseed-paths: ['src/seeds']\n")
        assert is_dbt_model(_write(project / "src" / "seeds" / "x.sql")) is False
        assert is_dbt_schema_file(str(project / "src" / "seeds" / "schema.yml")) is False
        assert is_dbt_model(_write(project / "src" / "y.sql")) is True

    def test_macros_folder_inside_a_model_folder_is_named_as_a_model(self, tmp_path):
        """dbt builds models/macros/x.sql as a model; main named it a macro. Naming it a
        model puts it back in the commit-time table list."""
        project = _project(tmp_path / "p")
        path = _write(project / "models" / "macros" / "helper.sql")
        assert is_dbt_model(path) is True
        assert extract_table_name(path) == "helper"


class TestConfiguredPaths:
    """Fixtures from review, each built by dbt; main gates every one."""

    def test_exclusion_sharing_a_basename_with_an_unrelated_folder(self, tmp_path):
        outer = _project(
            tmp_path / "outer", "model-paths: ['src/models']\nseed-paths: ['data/seeded']\n"
        )
        nested = _project(outer / "src" / "models" / "nested")
        path = _write(nested / "seeded" / "orders.sql")
        assert is_dbt_model(path) is True
        assert is_dbt_schema_file(str(nested / "seeded" / "schema.yml")) is True
        assert extract_table_name(path) == "orders"

    def test_model_path_through_a_parent_segment(self, tmp_path):
        x = _project(tmp_path / "x", "model-paths: ['../x']\n")
        path = _write(x / "staging" / "orders.sql")
        assert is_dbt_model(path) is True
        assert is_dbt_schema_file(str(x / "staging" / "schema.yml")) is True

    def test_project_outside_the_files_ancestry(self, tmp_path):
        _project(tmp_path / "build", "model-paths: ['../models']\n")
        nested = _project(tmp_path / "models" / "nested", "name: other\n")
        path = _write(nested / "orders.sql")
        assert is_dbt_model(path) is True
        assert is_dbt_schema_file(str(nested / "schema.yml")) is True

    def test_project_outside_the_files_ancestry_beside_a_directory_named_dbt_project_yml(self, tmp_path):
        _project(tmp_path / "build", "model-paths: ['../models']\n")
        (tmp_path / "models" / "nested" / "dbt_project.yml").mkdir(parents=True)
        assert is_dbt_model(_write(tmp_path / "models" / "nested" / "orders.sql")) is True
        assert is_dbt_schema_file(str(tmp_path / "models" / "nested" / "schema.yml")) is True

    def test_symlink_alias_reaches_the_outer_project(self, tmp_path):
        outer = _project(tmp_path / "outer")
        _project(outer / "models")
        _write(outer / "models" / "orders.sql")
        (tmp_path / "models").mkdir()
        os.symlink(outer / "models", tmp_path / "models" / "alias")
        path = str(tmp_path / "models" / "alias" / "orders.sql")
        assert is_dbt_model(path) is True
        assert extract_table_name(path) == "orders"

    def test_symlink_alias_under_a_neutral_folder(self, tmp_path):
        """No folder in the written path is a dbt folder; only the resolved path is."""
        outer = _project(tmp_path / "outer", "model-paths: ['transformations']\n")
        _project(outer / "transformations", "model-paths: ['nothing']\n")
        _write(outer / "transformations" / "orders.sql")
        (tmp_path / "links").mkdir()
        os.symlink(outer / "transformations", tmp_path / "links" / "alias")
        assert is_dbt_model(str(tmp_path / "links" / "alias" / "orders.sql")) is True

    def test_directory_named_like_a_project_file_does_not_hide_the_nearest_project(self, tmp_path):
        """Main's name rule reads the nearest real project's folder names."""
        r = _project(tmp_path / "r", "model-paths: ['x/models2']\n")
        (r / "other" / "models2" / "sub" / "dbt_project.yml").mkdir(parents=True)
        assert is_dbt_model(_write(r / "other" / "models2" / "sub" / "a.sql")) is True

    def test_directory_named_like_a_project_file_is_skipped(self, tmp_path):
        outer = _project(tmp_path / "outer", "model-paths: ['transformations']\n")
        (outer / "transformations" / "dbt_project.yml").mkdir(parents=True)
        path = _write(outer / "transformations" / "orders.sql")
        assert is_dbt_model(path) is True


class TestExactFolderMatching:
    """Cases only the exact check gates: a seed or analysis folder elsewhere shares a
    folder name with the file's path, so main's name rule excludes it."""

    def test_parent_segment_is_resolved(self, tmp_path):
        p = _project(tmp_path / "p", "model-paths: ['../p/core']\nseed-paths: ['data/stuff']\n")
        assert is_dbt_model(_write(p / "core" / "stuff" / "x.sql")) is True

    def test_model_folder_in_another_case(self, tmp_path):
        p = _project(tmp_path / "p", "model-paths: ['src/Models']\nseed-paths: ['data/seeded']\n")
        # A new file, so no symlink resolution can fix the folder's case.
        assert is_dbt_model(str(p / "src" / "models" / "seeded" / "x.sql")) is True

    def test_exclusion_folder_matches_exact_case_only(self, tmp_path):
        p = _project(
            tmp_path / "p",
            "model-paths: ['src']\nseed-paths: ['src/seeds']\nanalysis-paths: ['other/SEEDS']\n",
        )
        assert is_dbt_model(_write(p / "src" / "SEEDS" / "x.sql")) is True


class TestNamingByConfiguredPaths:
    def test_inner_macro_under_an_outer_folder_named_like_a_model_folder(self, tmp_path):
        outer = _project(tmp_path / "outer", "model-paths: ['src/models']\nmacro-paths: ['udfs']\n")
        inner = _project(outer / "other" / "models" / "inner")
        path = _write(inner / "macros" / "helper.sql", _MACRO_SQL)
        assert extract_table_name(path) == "macro:helper"

    def test_inner_snapshot_under_an_outer_folder_named_like_a_macro_folder(self, tmp_path):
        outer = _project(tmp_path / "outer", "macro-paths: ['ops/macros']\n")
        inner = _project(outer / "macros" / "inner")
        path = _write(inner / "snapshots" / "orders.sql", "{% snapshot orders %}1{% endsnapshot %}")
        assert is_dbt_model(path) is True
        assert extract_table_name(path) == "orders"

    def test_inner_snapshot_inside_an_outer_macro_folder(self, tmp_path):
        """The outer project's macro folder holds the inner project; the inner snapshot
        folder still names the file as a snapshot."""
        inner = _project(_project(tmp_path / "outer") / "macros" / "inner")
        path = _write(inner / "snapshots" / "orders.sql", "{% snapshot orders %}1{% endsnapshot %}")
        assert extract_table_name(path) == "orders"

    def test_file_no_project_contains_falls_back_to_folder_names(self, tmp_path):
        project = _project(tmp_path / "p", "model-paths: ['src']\n")
        path = str(project / "lib" / "macros" / "helper.sql")
        assert extract_table_name(path) == "macro:helper"


class TestUnreadableProjects:
    """A project file that can't be read skips that project; it never aborts or stalls
    classification by another."""

    def test_ancestor_config_vanishing_after_discovery(self, tmp_path, monkeypatch):
        import lib.cache as cache
        outer = _project(tmp_path / "outer")
        inner = _project(outer / "inner")
        path = _write(inner / "models" / "orders.sql")
        real_getmtime = os.path.getmtime
        outer_yml = str(outer / "dbt_project.yml")

        def getmtime(p):
            if str(p) == outer_yml:
                raise FileNotFoundError(p)
            return real_getmtime(p)

        monkeypatch.setattr(cache.os.path, "getmtime", getmtime)
        assert is_dbt_model(path) is True
        assert is_dbt_schema_file(str(inner / "models" / "schema.yml")) is True
        assert extract_table_name(path) == "orders"

    def test_nearest_config_unreadable_falls_back_to_defaults(self, tmp_path, monkeypatch):
        import lib.cache as cache
        project = _project(tmp_path / "p")
        path = _write(project / "models" / "orders.sql")

        def getmtime(p):
            raise PermissionError(p)

        monkeypatch.setattr(cache.os.path, "getmtime", getmtime)
        assert is_dbt_model(path) is True

    @pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="needs mkfifo")
    def test_fifo_named_like_a_project_file_is_not_read(self, tmp_path):
        outer = tmp_path / "outer"
        outer.mkdir()
        os.mkfifo(outer / "dbt_project.yml")
        inner = _project(outer / "inner")
        path = _write(inner / "models" / "orders.sql")
        assert is_dbt_model(path) is True
        assert extract_table_name(path) == "orders"


class TestNamingNeverMacroWhereMainSaysModel:
    """The exact check can only veto a macro name main's rule gives, never add one."""

    @staticmethod
    def _sibling_owner(root):
        _project(root / "build", "model-paths: ['../models']\n")
        nested = _project(root / "models" / "nested", "macro-paths: ['.']\n")
        _write(root / "models" / "raw.sql", "select 1 as id")
        return _write(nested / "orders.sql", "select * from {{ ref('raw') }}")

    def test_sibling_projects_model_beside_an_inner_macro_root(self, tmp_path):
        path = self._sibling_owner(tmp_path)
        assert is_dbt_model(path) is True
        assert extract_table_name(path) == "orders"

    def test_sibling_projects_model_stays_in_the_post_commit_list(self, tmp_path):
        import subprocess
        from lib.protocol import _get_committed_model_tables

        repo = tmp_path / "repo"
        repo.mkdir()
        self._sibling_owner(repo)
        git = ["git", "-c", "user.email=t@example.com", "-c", "user.name=t", "-c", "commit.gpgsign=false"]
        subprocess.run(git + ["init", "-q"], cwd=repo, check=True)
        subprocess.run(git + ["add", "."], cwd=repo, check=True)
        subprocess.run(git + ["commit", "-q", "-m", "x"], cwd=repo, check=True)
        assert "orders" in _get_committed_model_tables(str(repo))

    def test_outer_macro_root_over_an_inner_project(self, tmp_path):
        outer = _project(tmp_path / "outer", "macro-paths: ['udfs']\n")
        inner = _project(outer / "udfs" / "inner", "model-paths: ['a/models']\n")
        path = _write(inner / "b" / "models" / "x.sql")
        assert is_dbt_model(path) is True
        assert extract_table_name(path) == "x"

    def test_absolute_configured_model_path(self, tmp_path):
        p = tmp_path / "p"
        _project(p, f"model-paths: ['{p}/warehouse']\nmacro-paths: ['warehouse/udfs']\n")
        path = _write(p / "warehouse" / "udfs" / "orders.sql")
        assert is_dbt_model(path) is True
        assert extract_table_name(path) == "orders"


def _symlink_chain(folder, hops, target):
    """folder/0 -> 1 -> ... -> hops-1 -> target, each link one hop."""
    folder.mkdir(parents=True)
    for i in range(hops - 1):
        os.symlink(str(i + 1), folder / str(i))
    os.symlink(target, folder / str(hops - 1))
    return folder / "0"


class TestCanonicalPaths:
    def test_deep_symlink_chain_in_the_written_path(self, tmp_path):
        p = _project(tmp_path / "p")
        (p / "real").mkdir()
        _symlink_chain(p / "chain", 1100, "../real")
        (p / "models").mkdir()
        os.symlink("../chain/0", p / "models" / "loop")
        path = str(p / "models" / "loop" / "orders.sql")
        assert is_dbt_model(path) is True
        assert extract_table_name(path) == "orders"

    def test_deep_symlink_chain_in_a_configured_root(self, tmp_path):
        p = _project(tmp_path / "p", "macro-paths: ['chain/0']\n")
        (p / "real").mkdir()
        _symlink_chain(p / "chain", 1100, "../real")
        path = _write(p / "models" / "orders.sql")
        assert is_dbt_model(path) is True
        assert extract_table_name(path) == "orders"

    def test_deep_symlink_chain_where_main_rule_does_not_decide(self, tmp_path):
        """Resolving is reached here, so its failure must fall back, not raise."""
        p = _project(tmp_path / "p")
        (p / "real").mkdir()
        _symlink_chain(p / "chain", 1100, "../real")
        (p / "scripts").mkdir()
        os.symlink("../chain/0", p / "scripts" / "loop")
        path = str(p / "scripts" / "loop" / "orders.sql")
        assert is_dbt_model(path) is False
        assert is_dbt_schema_file(str(p / "scripts" / "loop" / "schema.yml")) is False

    def test_deep_symlink_chain_in_a_configured_root_while_naming(self, tmp_path):
        p = _project(tmp_path / "p", "macro-paths: ['macros', 'chain/0']\n")
        (p / "real").mkdir()
        _symlink_chain(p / "chain", 1100, "../real")
        path = _write(p / "macros" / "helper.sql", _MACRO_SQL)
        assert is_dbt_model(path) is True
        assert extract_table_name(path) == "macro:helper"

    def test_dangling_alias_to_a_model_folder(self, tmp_path):
        p = _project(tmp_path / "p", "model-paths: ['src']\nseed-paths: ['data/alias']\n")
        os.symlink("src/future", p / "alias")
        assert is_dbt_model(str(p / "alias" / "orders.sql")) is True

    def test_parent_segment_after_an_alias(self, tmp_path):
        p = _project(tmp_path / "p", "model-paths: ['src']\nseed-paths: ['data/alias']\n")
        _write(p / "src" / "orders.sql")
        (p / "src" / "deeper").mkdir()
        os.symlink("src/deeper", p / "alias")
        assert is_dbt_model(str(p / "alias" / ".." / "orders.sql")) is True


class TestUnreadableConfigs:
    @pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="needs mkfifo")
    def test_config_replaced_by_a_fifo_after_discovery_is_not_read(self, tmp_path, monkeypatch):
        import signal
        import lib.cache as cache
        outer = tmp_path / "outer"
        outer.mkdir()
        fifo = str(outer / "dbt_project.yml")
        os.mkfifo(fifo)
        # Read as an empty project, the outer defaults would claim outer/models and
        # rename the inner macro.
        inner = _project(outer / "models" / "inner")
        path = _write(inner / "macros" / "helper.sql", _MACRO_SQL)
        real_isfile = os.path.isfile
        # Discovery saw a regular file; by the read it is a FIFO.
        monkeypatch.setattr(cache.os.path, "isfile", lambda p: p == fifo or real_isfile(p))

        class Blocked(BaseException):
            """Not an OSError, so no handler in the code under test can swallow it."""

        def timed_out(*_):
            raise Blocked("blocked reading a FIFO")

        previous = signal.signal(signal.SIGALRM, timed_out)
        signal.alarm(5)
        try:
            assert is_dbt_model(path) is True
            assert extract_table_name(path) == "macro:helper"
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, previous)

    @pytest.mark.skipif(not hasattr(os, "geteuid") or os.geteuid() == 0, reason="root reads mode 000")
    def test_config_that_cannot_be_read_is_skipped_and_not_cached(self, tmp_path):
        import lib.cache as cache
        outer = _project(tmp_path / "outer", "model-paths: ['warehouse']\n")
        inner = _project(outer / "models" / "inner")
        path = _write(inner / "macros" / "helper.sql", _MACRO_SQL)
        yml = outer / "dbt_project.yml"
        yml.chmod(0)
        try:
            assert is_dbt_model(path) is True
            assert extract_table_name(path) == "macro:helper"
            assert not os.path.exists(cache._dbt_config_cache_path(str(yml)))
        finally:
            yml.chmod(0o644)
        assert extract_table_name(path) == "macro:helper"

    @pytest.mark.skipif(not hasattr(os, "geteuid") or os.geteuid() == 0, reason="root reads mode 000")
    def test_nearest_config_that_cannot_be_read_uses_defaults(self, tmp_path):
        p = _project(tmp_path / "p", "model-paths: ['warehouse']\n")
        path = _write(p / "models" / "orders.sql")
        (p / "dbt_project.yml").chmod(0)
        try:
            assert is_dbt_model(path) is True
        finally:
            (p / "dbt_project.yml").chmod(0o644)


_MAIN_DEFAULT_PATHS = {
    "model-paths": ["models"],
    "macro-paths": ["macros"],
    "snapshot-paths": ["snapshots"],
    "seed-paths": ["seeds"],
    "analysis-paths": ["analyses"],
}


def _main_find_dbt_project_yml(file_path):
    """main's lookup (797fc40), copied: nearest regular file."""
    directory = os.path.dirname(os.path.abspath(file_path))
    while True:
        candidate = os.path.join(directory, "dbt_project.yml")
        if os.path.isfile(candidate):
            return candidate
        parent = os.path.dirname(directory)
        if parent == directory:
            return None
        directory = parent


def _main_parse_dbt_project_paths(project_yml_path):
    """main's parser (797fc40), copied verbatim, so the reference shares nothing with
    the loader under test."""
    result = {}
    try:
        with open(project_yml_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except (OSError, UnicodeDecodeError):
        return result

    current_key = None
    for line in lines:
        stripped = line.strip()
        for key in _MAIN_DEFAULT_PATHS:
            if stripped.startswith(f"{key}:"):
                value_part = stripped[len(key) + 1:].strip()
                if value_part.startswith("["):
                    inner = value_part.strip("[]")
                    items = [
                        item.strip().strip("'\"")
                        for item in inner.split(",")
                        if item.strip()
                    ]
                    if items:
                        result[key] = items
                    current_key = None
                elif not value_part or value_part == "":
                    current_key = key
                    result[key] = []
                break
        else:
            if current_key and stripped.startswith("- "):
                item = stripped[2:].strip().strip("'\"")
                if item:
                    result.setdefault(current_key, []).append(item)
            elif current_key and not stripped.startswith("#") and stripped:
                current_key = None

    return result


def _main_get_dbt_paths(file_path):
    project_yml = _main_find_dbt_project_yml(file_path)
    paths = dict(_MAIN_DEFAULT_PATHS)
    if project_yml:
        paths.update(_main_parse_dbt_project_paths(project_yml))
    return paths


def _main_is_macro_file(file_path: str) -> bool:
    """main's is_macro_file (797fc40), copied, over main's own lookup and parser."""
    parts = set(file_path.replace("\\", "/").split("/"))
    names = {p.rstrip("/").rsplit("/", 1)[-1] for p in _main_get_dbt_paths(file_path).get("macro-paths", [])}
    return bool(parts & names)


_LS = "\u2028"


def _hidden(key_line):
    """A quoted YAML scalar whose text holds key_line between U+2028 separators: one
    YAML line, which main's parser never reads as a key."""
    return f'vars:\n  note: "a{_LS}{key_line}{_LS}b"\n'


class TestMacroNameNeverBeyondMain:
    """is_macro_file True implies main's is_macro_file True, over every fixture layout
    in this file and a file in each of their folders."""

    @staticmethod
    def _layouts(root):
        _project(root / "a" / "outer")
        _project(root / "a" / "outer" / "models")
        _project(root / "b" / "outer" / "Macros" / "inner")
        _project(root / "c" / "outer", "macro-paths: ['udfs']\n")
        _project(root / "c" / "outer" / "udfs" / "inner", "model-paths: ['a/models']\n")
        _project(root / "d" / "build", "model-paths: ['../models']\n")
        _project(root / "d" / "models" / "nested", "macro-paths: ['.']\n")
        _project(root / "e" / "outer", "model-paths: ['src/models']\nmacro-paths: ['udfs']\n")
        _project(root / "e" / "outer" / "other" / "models" / "inner")
        _project(root / "f" / "outer", "macro-paths: ['ops/macros']\n")
        _project(root / "f" / "outer" / "macros" / "inner")
        _project(root / "g" / "p", "model-paths: ['MODELS']\nmacro-paths: ['Macros', 'lib/macros']\n")
        e = root / "h" / "p"
        _project(e, f"model-paths: ['{e}/warehouse']\nmacro-paths: ['warehouse/udfs']\n")
        _project(root / "j" / "build", "model-paths: ['../models']\n")
        _project(root / "j" / "models" / "nested", "macro-paths: ['udfs']\n" + _hidden("macro-paths: ['macros']"))
        (root / "k" / "p").mkdir(parents=True)
        (root / "k" / "p" / "dbt_project.yml").write_bytes(
            b"model-paths: ['warehouse']\nmacro-paths: ['udfs']\n# \xff\n"
        )
        for rel in (
            "a/outer/models/macros", "b/outer/Macros/inner/models", "b/outer/Macros/inner/macros",
            "c/outer/udfs/inner/b/models", "c/outer/udfs/inner/macros", "d/models/nested",
            "e/outer/other/models/inner/macros", "e/outer/udfs", "f/outer/macros/inner/snapshots",
            "f/outer/ops/macros", "g/p/macros", "g/p/Macros/models", "g/p/lib/MACROS", "h/p/warehouse/udfs",
            "i/MACROS", "i/Macros/models", "i/macros/models", "i/models/macros",
            "j/models/nested/macros", "j/models/nested/udfs", "k/p/warehouse/macros", "k/p/udfs",
        ):
            (root / rel).mkdir(parents=True, exist_ok=True)

    def test_every_folder(self, tmp_path):
        self._layouts(tmp_path)
        checked = 0
        for folder, _, _ in os.walk(tmp_path):
            path = os.path.join(folder, "x.sql")
            if is_macro_file(path):
                assert _main_is_macro_file(path), path
            checked += 1
        assert checked > 40


class TestParserMatchesMain:
    """The config parser reads lines and bytes as main's did."""

    def test_line_separator_inside_a_quoted_value_is_not_a_line_break(self, tmp_path):
        p = _project(tmp_path / "p", "model-paths: ['warehouse']\n" + _hidden("seed-paths: ['warehouse']"))
        assert is_dbt_model(_write(p / "warehouse" / "orders.sql")) is True
        assert is_dbt_schema_file(str(p / "warehouse" / "schema.yml")) is True

    def test_hidden_macro_path_does_not_rename_a_sibling_projects_model(self, tmp_path):
        import subprocess
        from lib.protocol import _get_committed_model_tables

        repo = tmp_path / "repo"
        _project(repo / "build", "model-paths: ['../models']\n")
        nested = _project(repo / "models" / "nested", "macro-paths: ['udfs']\n" + _hidden("macro-paths: ['macros']"))
        _write(repo / "models" / "raw.sql", "select 1 as id")
        path = _write(nested / "macros" / "orders.sql", "select * from {{ ref('raw') }}")
        assert is_dbt_model(path) is True
        assert extract_table_name(path) == "orders"
        git = ["git", "-c", "user.email=t@example.com", "-c", "user.name=t", "-c", "commit.gpgsign=false"]
        subprocess.run(git + ["init", "-q"], cwd=repo, check=True)
        subprocess.run(git + ["add", "."], cwd=repo, check=True)
        subprocess.run(git + ["commit", "-q", "-m", "x"], cwd=repo, check=True)
        assert "orders" in _get_committed_model_tables(str(repo))

    def test_crlf_and_cr_line_endings_split_like_main(self, tmp_path):
        p = tmp_path / "p"
        p.mkdir()
        (p / "dbt_project.yml").write_bytes(b"name: p\r\nmodel-paths: ['warehouse']\rseed-paths: ['data']\r\n")
        assert is_dbt_model(_write(p / "warehouse" / "orders.sql")) is True

    def test_undecodable_byte_falls_back_to_defaults_as_on_main(self, tmp_path):
        """main's Python parser gave up on invalid UTF-8 and used the defaults."""
        p = tmp_path / "p"
        p.mkdir()
        (p / "dbt_project.yml").write_bytes(b"model-paths: ['warehouse']\nmacro-paths: ['udfs']\n# \xff\n")
        path = _write(p / "warehouse" / "orders.sql")
        assert is_dbt_model(path) is _main_is_dbt_model_by_name(path)
        macro = _write(p / "warehouse" / "macros" / "orders.sql")
        assert extract_table_name(macro) == ("macro:orders" if _main_is_macro_file(macro) else "orders")


def _main_is_dbt_model_by_name(file_path):
    """main's folder-name gate (797fc40), copied, over main's own lookup and parser."""
    parts = set(file_path.replace("\\", "/").split("/"))
    paths = _main_get_dbt_paths(file_path)
    last = lambda keys: {p.rstrip("/").rsplit("/", 1)[-1] for k in keys for p in paths.get(k, [])}
    if parts & last(("seed-paths", "analysis-paths")):
        return False
    return bool(parts & last(("model-paths", "macro-paths", "snapshot-paths")))
