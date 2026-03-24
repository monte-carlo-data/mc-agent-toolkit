import os
import pytest
from lib.detect import is_dbt_model, extract_table_name


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
        """Macros directory should be excluded."""
        macro_dir = tmp_path / "project" / "macros"
        macro_dir.mkdir(parents=True)
        sql_file = macro_dir / "helper.sql"
        sql_file.write_text("SELECT * FROM {{ ref('x') }}")
        assert is_dbt_model(str(sql_file)) is False

    def test_sql_file_in_analyses(self, tmp_path):
        """Analyses directory should be excluded."""
        dir_ = tmp_path / "project" / "analyses"
        dir_.mkdir(parents=True)
        sql_file = dir_ / "report.sql"
        sql_file.write_text("SELECT * FROM {{ ref('x') }}")
        assert is_dbt_model(str(sql_file)) is False

    def test_sql_file_in_snapshots(self, tmp_path):
        """Snapshots directory should be excluded."""
        dir_ = tmp_path / "project" / "snapshots"
        dir_.mkdir(parents=True)
        sql_file = dir_ / "snap.sql"
        sql_file.write_text("SELECT * FROM {{ ref('x') }}")
        assert is_dbt_model(str(sql_file)) is False

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
