"""The `apply_patch` parser in its "cortex" dialect (CoCo Desktop 2.0.0, Cortex Code CLI
1.2.46), and path resolution. The "codex" dialect is in test_apply_patch_codex.py."""
import pytest


def _patch(*body):
    return "\n".join(["*** Begin Patch", *body, "*** End Patch"]) + "\n"


def _update(path, old="a", new="b"):
    return [f"*** Update File: {path}", "@@", f"-{old}", f"+{new}"]


# --- Parser ---

class TestParseOperations:
    def _ops(self, text):
        from lib.apply_patch import parse_operations
        return [(op.kind, op.path, op.move_to) for op in parse_operations(text)]

    def test_update(self):
        assert self._ops(_patch(*_update("models/orders.sql"))) == [("update", "models/orders.sql", None)]

    def test_add_and_delete(self):
        text = _patch("*** Add File: models/new.sql", "+select 1", "*** Delete File: models/old.sql")
        assert self._ops(text) == [("add", "models/new.sql", None), ("delete", "models/old.sql", None)]

    def test_move_attaches_to_update(self):
        text = _patch("*** Update File: models/a.sql", "*** Move to: models/b.sql", "@@", "-x", "+y")
        assert self._ops(text) == [("update", "models/a.sql", "models/b.sql")]

    def test_rename_without_hunks(self):
        text = _patch("*** Update File: models/a.sql", "*** Move to: models/b.sql")
        assert self._ops(text) == [("update", "models/a.sql", "models/b.sql")]

    def test_move_after_a_hunk_still_counts(self):
        """The clients reject this patch; reading the Move anyway only adds a file to check."""
        text = _patch("*** Update File: models/a.sql", "@@", "-x", "+y", "*** Move to: models/b.sql")
        assert self._ops(text) == [("update", "models/a.sql", "models/b.sql")]

    def test_bom_after_header_inside_update_section(self):
        text = _patch(*_update("README.md"), "*** Delete File: models/orders.sql\ufeff")
        assert self._ops(text)[-1] == ("delete", "models/orders.sql", None)
        # Trailing whitespace is stripped the JavaScript way (U+FEFF included), so a
        # header with nothing after it is not an operation.
        assert self._ops(_patch(*_update("README.md"), "*** Delete File: \ufeff")) == [("update", "README.md", None)]

    @pytest.mark.parametrize("char", ["\x1c", "\x1d", "\x1e", "\x1f", "\x85"])
    def test_python_only_whitespace_is_not_trimmed(self, char):
        """JavaScript's trim keeps these five, which Python's isspace counts as whitespace."""
        assert self._ops(_patch(*_update(f"{char}/../models/orders.sql"))) == [
            ("update", f"{char}/../models/orders.sql", None)
        ]
        # The Add's path is the character itself, so the Update section ends and the
        # indented header after it is read.
        text = _patch(*_update("README.md"), f"*** Add File: {char}", "  *** Update File: models/orders.sql")
        assert self._ops(text)[-1] == ("update", "models/orders.sql", None)

    def test_first_move_kept(self):
        text = _patch("*** Update File: models/a.sql", "*** Move to: models/b.sql", "*** Move to: models/c.sql")
        assert self._ops(text) == [("update", "models/a.sql", "models/b.sql")]

    def test_move_not_right_after_update_is_ignored(self):
        text = _patch("*** Add File: models/a.sql", "*** Move to: models/b.sql", "+x")
        assert self._ops(text) == [("add", "models/a.sql", None)]

    def test_several_files_in_order(self):
        text = _patch(*_update("README.md"), *_update("models/orders.sql"), "*** Delete File: x.txt")
        assert [p for _, p, _ in self._ops(text)] == ["README.md", "models/orders.sql", "x.txt"]

    def test_crlf(self):
        text = (_patch(*_update("models/orders.sql")) + "*** Delete File: models/customers.sql\n").replace("\n", "\r\n")
        assert self._ops(text) == [("update", "models/orders.sql", None)]

    def test_leading_blank_lines_and_bom(self):
        text = "\ufeff\n  \n" + _patch(*_update("models/orders.sql"))
        assert self._ops(text) == [("update", "models/orders.sql", None)]

    def test_path_with_spaces_kept(self):
        assert self._ops(_patch(*_update("models/my model.sql"))) == [("update", "models/my model.sql", None)]

    def test_path_is_trimmed(self):
        assert self._ops(_patch("*** Delete File:   models/a.sql  ")) == [("delete", "models/a.sql", None)]

    def test_path_trailing_bom_is_trimmed(self):
        """JavaScript's trim, which the clients use on paths, also removes U+FEFF."""
        assert self._ops(_patch("*** Delete File: models/orders.sql\ufeff")) == [("delete", "models/orders.sql", None)]

    def test_indented_patch_outside_update_hunks(self):
        """The Cortex Code CLI trims a line before matching a header outside an Update hunk."""
        text = "  *** Begin Patch\n  *** Delete File: models/orders.sql\n  *** End Patch\n"
        assert self._ops(text) == [("delete", "models/orders.sql", None)]

    def test_indented_header_after_add_or_delete(self):
        text = _patch("*** Add File: notes.txt", "+hi", "  *** Update File: models/orders.sql", "@@", "-a", "+b",
                      "*** Delete File: x.txt", "\t*** Delete File: models/customers.sql")
        assert [p for _, p, _ in self._ops(text)] == ["notes.txt", "models/orders.sql", "x.txt", "models/customers.sql"]

    def test_indented_line_in_update_hunk_is_content(self):
        """Inside an Update's hunks the CLI only strips trailing whitespace, so an indented
        header there is a context line, not a new operation."""
        text = _patch("*** Update File: README.md", "@@", "  *** Delete File: models/orders.sql", "-a", "+b")
        assert self._ops(text) == [("update", "README.md", None)]

    def test_update_header_on_last_line(self):
        assert self._ops("*** Begin Patch\n*** Update File: models/orders.sql") == [("update", "models/orders.sql", None)]

    def test_hunk_content_that_looks_like_a_header_is_not_one(self):
        text = _patch("*** Update File: README.md", "@@", "-old", "+*** Update File: models/orders.sql",
                      " *** Delete File: models/customers.sql")
        assert self._ops(text) == [("update", "README.md", None)]

    def test_stops_at_end_patch(self):
        text = _patch(*_update("README.md")) + "*** Update File: models/orders.sql\n"
        assert self._ops(text) == [("update", "README.md", None)]

    def test_missing_end_patch_still_returns_headers(self):
        text = "*** Begin Patch\n*** Update File: models/orders.sql\n@@\n-a\n+b\n"
        assert self._ops(text) == [("update", "models/orders.sql", None)]

    def test_empty_path_skipped(self):
        assert self._ops(_patch("*** Delete File:   ")) == []

    def test_not_a_patch(self):
        assert self._ops("*** Update File: models/orders.sql\n") == []
        assert self._ops("Here is the change:\n*** Update File: models/orders.sql\n@@\n-a\n+b\n") == []
        assert self._ops("echo hi") == []
        assert self._ops("") == []

    def test_non_string(self):
        assert self._ops(None) == []
        assert self._ops({"input": "x"}) == []

    def test_op_paths_dedupes_and_includes_move_destination(self):
        from lib.apply_patch import op_paths, parse_operations
        text = _patch("*** Update File: a.sql", "*** Move to: b.sql", *_update("a.sql"), "*** Delete File: c.sql")
        assert op_paths(parse_operations(text)) == ["a.sql", "b.sql", "c.sql"]


class TestResolvePath:
    def test_relative_joined_to_cwd(self):
        from lib.apply_patch import resolve_path
        assert resolve_path("models/orders.sql", "/proj") == "/proj/models/orders.sql"

    def test_absolute_kept(self):
        from lib.apply_patch import resolve_path
        assert resolve_path("/other/models/orders.sql", "/proj") == "/other/models/orders.sql"

    def test_normalized(self):
        from lib.apply_patch import resolve_path
        assert resolve_path("seeds/../models/./orders.sql", "/proj") == "/proj/models/orders.sql"

    def test_empty_cwd_is_filesystem_root(self):
        """Desktop resolves a relative path with no working directory as /<path>."""
        from lib.apply_patch import resolve_path
        assert resolve_path("models/orders.sql", "") == "/models/orders.sql"
        assert resolve_path("models/orders.sql", None) == "/models/orders.sql"


class TestTrailingSlash:
    """Codex's applier writes `models/orders.sql` for `models/orders.sql/`."""

    @pytest.mark.parametrize("path", ["models/orders.sql/", "models/orders.sql/.", "models/./orders.sql"])
    def test_may_be_dbt_file(self, path):
        from lib.detect import may_be_dbt_file
        assert may_be_dbt_file(path)

    @pytest.mark.parametrize("path", ["models/", "models/.", "notes.md", "notes.md/"])
    def test_not_a_dbt_file(self, path):
        from lib.detect import may_be_dbt_file
        assert not may_be_dbt_file(path)

    @pytest.mark.parametrize("path", ["models/orders.sql/", "models/orders.sql/."])
    def test_resolved_to_the_file(self, path):
        from lib.apply_patch import op_groups, parse_operations, resolve_path
        assert resolve_path(path, "/proj") == "/proj/models/orders.sql"
        assert op_groups(parse_operations(_patch(*_update(path))), "/proj") == [["/proj/models/orders.sql"]]

    def test_resolved_path_is_a_model(self, tmp_path):
        from lib.apply_patch import resolve_path
        from lib.detect import is_dbt_model
        (tmp_path / "models").mkdir()
        (tmp_path / "models" / "orders.sql").write_text("select * from {{ ref('raw') }}\n")
        assert is_dbt_model(resolve_path("models/orders.sql/", str(tmp_path)))


class TestTrackWithoutRecord:
    """A PostToolUse with no record of its PreToolUse (missing or unmatched call id)."""

    @pytest.fixture
    def project(self, tmp_path):
        (tmp_path / "models").mkdir()
        (tmp_path / "docs").mkdir()
        return tmp_path

    def _track(self, text, project, call_id="call_1"):
        from lib.apply_patch import track_patch
        track_patch(text, "codex", cwd=str(project), session_id="s1", call_id=call_id)
        from lib.cache import get_edited_tables
        return sorted(get_edited_tables("s1"))

    def test_gone_model_with_an_assessment_tracked(self, project):
        from lib.cache import mark_impact_check_verified
        mark_impact_check_verified("s1", "orders")
        assert self._track(_patch("*** Delete File: models/orders.sql"), project) == ["orders"]

    def test_gone_model_without_call_id_tracked(self, project):
        from lib.cache import mark_impact_check_verified
        mark_impact_check_verified("s1", "orders")
        assert self._track(_patch("*** Delete File: models/orders.sql"), project, call_id=None) == ["orders"]

    def test_gone_file_without_an_assessment_not_tracked(self, project):
        assert self._track(_patch("*** Delete File: models/orders.sql"), project) == []

    def test_gone_non_model_with_an_assessed_stem_not_tracked(self, project):
        from lib.cache import mark_impact_check_verified
        mark_impact_check_verified("s1", "orders")
        assert self._track(_patch("*** Delete File: docs/orders.sql"), project) == []

    def test_record_present_wins_over_assessment(self, project):
        """The pre hook saw no model at that path, so an old assessment of the stem doesn't count."""
        from lib.cache import mark_impact_check_verified, save_patch_record
        mark_impact_check_verified("s1", "orders")
        save_patch_record("s1", "call_1", [])
        assert self._track(_patch("*** Delete File: models/orders.sql"), project) == []
