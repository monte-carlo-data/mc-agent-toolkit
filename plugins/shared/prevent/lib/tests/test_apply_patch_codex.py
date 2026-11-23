"""The `apply_patch` parser in its "codex" dialect (Codex 0.171.0,
`codex-rs/apply-patch/src/streaming_parser.rs`), and the per-call patch record."""
import os

import pytest

from lib import cache
from lib.apply_patch import parse_operations


def _ops(text):
    return [(op.kind, op.path, op.move_to) for op in parse_operations(text, "codex")]


def _patch(*body):
    return "\n".join(["*** Begin Patch", *body, "*** End Patch"])


class TestCodexDialect:
    def test_every_operation(self):
        text = _patch("*** Add File: a.sql", "+x", "*** Delete File: b.sql",
                      "*** Update File: c.sql", "*** Move to: d.sql", "@@", "-x", "+y")
        assert _ops(text) == [("add", "a.sql", None), ("delete", "b.sql", None), ("update", "c.sql", "d.sql")]

    def test_path_kept_as_written_after_the_marker(self):
        """Codex strips the marker from the trimmed line and keeps the rest, spaces included."""
        assert _ops(_patch("*** Delete File:  models/a.sql")) == [("delete", " models/a.sql", None)]

    def test_line_is_trimmed_the_rust_way(self):
        # U+0085 is whitespace to Rust, so the header is found and the path loses it.
        assert _ops(_patch("\x85*** Delete File: models/a.sql\x85")) == [("delete", "models/a.sql", None)]
        # U+FEFF isn't, so this line is no header.
        assert _ops(_patch("﻿*** Delete File: models/a.sql")) == []

    def test_indented_header_outside_an_update_counts(self):
        assert _ops(_patch("*** Delete File: a.sql", "   *** Delete File: b.sql")) == [
            ("delete", "a.sql", None), ("delete", "b.sql", None)]

    def test_indented_header_inside_an_update_is_content(self):
        text = _patch("*** Update File: a.sql", "@@", " *** Delete File: b.sql")
        assert _ops(text) == [("update", "a.sql", None)]

    def test_move_only_before_the_first_hunk_line(self):
        text = _patch("*** Update File: a.sql", "@@", "-x", "+y", "*** Move to: b.sql")
        assert _ops(text) == [("update", "a.sql", None)]

    def test_move_after_a_content_line_is_content(self):
        for content in (" context", "+x", "-x"):
            text = _patch("*** Update File: a.sql", content, "*** Move to: b.sql")
            assert _ops(text) == [("update", "a.sql", None)], content

    def test_move_after_leading_end_of_file_marker(self):
        """An `*** End of File` line with no chunk yet doesn't open one, so the Move still counts."""
        text = _patch("*** Update File: notes.txt", "*** End of File", "*** Move to: models/orders.sql",
                      "@@", "-a", "+b")
        assert _ops(text) == [("update", "notes.txt", "models/orders.sql")]

    def test_eof_wrapper(self):
        for wrapper in ("<<EOF", "<<'EOF'", '<<"EOF"'):
            assert _ops(f"{wrapper}\n" + _patch("*** Delete File: a.sql") + "\nEOF") == [("delete", "a.sql", None)]

    def test_end_marker_is_trimmed(self):
        assert _ops("*** Begin Patch\n*** Delete File: a.sql\n  *** End Patch  \n*** Delete File: b.sql") == [
            ("delete", "a.sql", None)]

    def test_environment_line_is_not_an_operation(self):
        assert _ops(_patch("*** Environment ID: remote", "*** Delete File: a.sql")) == [("delete", "a.sql", None)]

    def test_crlf(self):
        assert _ops("*** Begin Patch\r\n*** Delete File: a.sql\r\n*** End Patch\r\n") == [("delete", "a.sql", None)]

    def test_not_a_patch(self):
        assert _ops("apply_patch <<'EOF'\n" + _patch("*** Delete File: a.sql")) == []
        assert _ops(None) == []


class TestPatchRecord:
    def test_round_trip_consumes_the_record(self):
        cache.save_patch_record("s1", "call/../x", ["/p/a.sql"])
        assert cache.pop_patch_record("s1", "call/../x") == ["/p/a.sql"]
        assert cache.pop_patch_record("s1", "call/../x") is None

    def test_key_is_a_hash_inside_the_cache_dir(self):
        cache.save_patch_record("s1", "../../etc/passwd", [])
        names = [n for n in os.listdir(cache.CACHE_DIR) if n.startswith(cache.PATCH_PREFIX)]
        assert len(names) == 1 and len(names[0]) == len(cache.PATCH_PREFIX) + 64

    def test_calls_and_sessions_kept_apart(self):
        cache.save_patch_record("s1", "c1", ["a"])
        cache.save_patch_record("s1", "c2", ["b"])
        cache.save_patch_record("s2", "c1", ["c"])
        assert cache.pop_patch_record("s1", "c2") == ["b"]
        assert cache.pop_patch_record("s2", "c1") == ["c"]
        assert cache.pop_patch_record("s1", "c1") == ["a"]

    def test_invalid_session_id_rejected(self):
        with pytest.raises(ValueError):
            cache.save_patch_record("../x", "c1", [])

    def test_swept_when_stale(self):
        cache.save_patch_record("s1", "c1", ["a"])
        (name,) = [n for n in os.listdir(cache.CACHE_DIR) if n.startswith(cache.PATCH_PREFIX)]
        old = os.path.getmtime(os.path.join(cache.CACHE_DIR, name)) - cache.STALE_THRESHOLD_SECONDS - 10
        os.utime(os.path.join(cache.CACHE_DIR, name), (old, old))
        cache.cleanup_stale_cache()
        assert cache.pop_patch_record("s1", "c1") is None
