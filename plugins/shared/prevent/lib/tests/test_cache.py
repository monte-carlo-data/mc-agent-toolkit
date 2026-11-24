import os
import stat
import time
import json
import pytest

import lib.cache as cache
from lib.cache import (
    claim_commit_checkpoint,
    is_valid_session_id,
    IC_PREFIX,
    TURN_PREFIX,
    PENDING_PREFIX,
    _validate_session_id,
    _w4_path,
    _mg_path,
    get_impact_check_state,
    mark_impact_check_injected,
    mark_impact_check_verified,
    get_impact_check_age_seconds,
    get_edited_tables,
    add_edited_table,
    clear_edited_tables,
    move_to_pending_validation,
    get_pending_validation_tables,
    clear_pending_validation,
    mark_monitor_gap,
    has_monitor_gap,
    clear_monitor_gap,
)


class TestImpactCheckState:
    def test_no_marker_returns_none(self):
        assert get_impact_check_state("test_session", "my_table") is None

    def test_injected_state(self):
        mark_impact_check_injected("test_session", "my_table")
        assert get_impact_check_state("test_session", "my_table") == "injected"

    def test_verified_state(self):
        mark_impact_check_injected("test_session", "my_table")
        mark_impact_check_verified("test_session", "my_table")
        assert get_impact_check_state("test_session", "my_table") == "verified"

    def test_marker_age(self):
        mark_impact_check_injected("test_session", "my_table")
        age = get_impact_check_age_seconds("test_session", "my_table")
        assert 0 <= age < 2  # Should be very recent

    def test_different_tables_independent(self):
        mark_impact_check_injected("test_session", "table_a")
        mark_impact_check_verified("test_session", "table_a")
        assert get_impact_check_state("test_session", "table_a") == "verified"
        assert get_impact_check_state("test_session", "table_b") is None


class TestEditAccumulator:
    def test_empty_session(self):
        assert get_edited_tables("session_1") == []

    def test_add_one_table(self):
        add_edited_table("session_1", "orders")
        assert get_edited_tables("session_1") == ["orders"]

    def test_add_multiple_tables(self):
        add_edited_table("session_1", "orders")
        add_edited_table("session_1", "customers")
        tables = get_edited_tables("session_1")
        assert "orders" in tables
        assert "customers" in tables

    def test_deduplication(self):
        add_edited_table("session_1", "orders")
        add_edited_table("session_1", "orders")
        assert get_edited_tables("session_1") == ["orders"]

    def test_clear(self):
        add_edited_table("session_1", "orders")
        clear_edited_tables("session_1")
        assert get_edited_tables("session_1") == []

    def test_sessions_independent(self):
        add_edited_table("session_1", "orders")
        add_edited_table("session_2", "customers")
        assert get_edited_tables("session_1") == ["orders"]
        assert get_edited_tables("session_2") == ["customers"]


class TestPendingValidation:
    def test_move_to_pending(self):
        add_edited_table("session_1", "orders")
        add_edited_table("session_1", "customers")
        move_to_pending_validation("session_1")
        pending = get_pending_validation_tables("session_1")
        assert "orders" in pending
        assert "customers" in pending
        # Turn accumulator should be cleared
        assert get_edited_tables("session_1") == []

    def test_clear_pending(self):
        add_edited_table("session_1", "orders")
        move_to_pending_validation("session_1")
        clear_pending_validation("session_1")
        assert get_pending_validation_tables("session_1") == []

    def test_no_pending_returns_empty(self):
        assert get_pending_validation_tables("session_1") == []


class TestSessionIdValidation:
    def test_valid_alphanumeric(self):
        assert _validate_session_id("abc123") == "abc123"

    def test_valid_with_dashes_underscores(self):
        assert _validate_session_id("session-1_test") == "session-1_test"

    def test_rejects_path_traversal(self):
        with pytest.raises(ValueError):
            _validate_session_id("../../etc/passwd")

    def test_rejects_spaces(self):
        with pytest.raises(ValueError):
            _validate_session_id("session 1")

    def test_rejects_shell_metacharacters(self):
        for bad in ["$(cmd)", "a;b", "a&b", "a|b", "a\nb"]:
            with pytest.raises(ValueError):
                _validate_session_id(bad)

    def test_rejects_empty(self):
        with pytest.raises(ValueError):
            _validate_session_id("")


class TestTableNameSanitization:
    """table_name flows into cache filenames; it must not be able to traverse
    out of CACHE_DIR (unlike session_id, it isn't otherwise validated)."""

    def _parent(self, path):
        return os.path.dirname(os.path.realpath(path))

    def test_w4_path_traversal_stays_in_cache_dir(self):
        assert self._parent(_w4_path("s1", "../../etc/passwd")) == os.path.realpath(cache.CACHE_DIR)

    def test_mg_path_traversal_stays_in_cache_dir(self):
        assert self._parent(_mg_path("s1", "../../etc/passwd")) == os.path.realpath(cache.CACHE_DIR)

    def test_path_separators_neutralized(self):
        assert self._parent(_w4_path("s1", "a/b/c")) == os.path.realpath(cache.CACHE_DIR)

    def test_normal_table_name_unchanged(self):
        # Sanitizer must be a no-op for ordinary dbt names.
        assert _w4_path("s1", "client_hub_master") == \
            os.path.join(cache.CACHE_DIR, f"{IC_PREFIX}s1_client_hub_master")

    def test_macro_prefix_preserved(self):
        assert _w4_path("s1", "macro:helper") == \
            os.path.join(cache.CACHE_DIR, f"{IC_PREFIX}s1_macro:helper")


class TestClearMonitorGap:
    def test_clear_removes_marker(self):
        mark_monitor_gap("test_clear_session", "orders")
        assert has_monitor_gap("test_clear_session", "orders") is True
        clear_monitor_gap("test_clear_session", "orders")
        assert has_monitor_gap("test_clear_session", "orders") is False

    def test_clear_when_not_marked_is_noop(self):
        assert has_monitor_gap("test_clear_session", "never_marked") is False
        clear_monitor_gap("test_clear_session", "never_marked")  # no exception
        assert has_monitor_gap("test_clear_session", "never_marked") is False

    def test_clear_one_table_does_not_affect_another(self):
        mark_monitor_gap("test_clear_session", "orders")
        mark_monitor_gap("test_clear_session", "users")
        clear_monitor_gap("test_clear_session", "orders")
        assert has_monitor_gap("test_clear_session", "orders") is False
        assert has_monitor_gap("test_clear_session", "users") is True


class TestFilePermissions:
    def _get_perms(self, path):
        return stat.S_IMODE(os.stat(path).st_mode)

    def test_impact_check_file_is_owner_only(self):
        mark_impact_check_injected("test_session", "perm_test_table")
        path = os.path.join(cache.CACHE_DIR, f"{IC_PREFIX}test_session_perm_test_table")
        assert self._get_perms(path) == 0o600

    def test_turn_file_is_owner_only(self):
        add_edited_table("perm_test_session", "orders")
        path = os.path.join(cache.CACHE_DIR, f"{TURN_PREFIX}perm_test_session")
        assert self._get_perms(path) == 0o600

    def test_pending_file_is_owner_only(self):
        add_edited_table("perm_test_session2", "orders")
        move_to_pending_validation("perm_test_session2")
        path = os.path.join(cache.CACHE_DIR, f"{PENDING_PREFIX}perm_test_session2")
        assert self._get_perms(path) == 0o600


class TestHeadSnapshot:
    def test_missing_returns_none(self):
        assert cache.get_head_snapshot("s1") is None

    def test_save_and_get(self):
        cache.save_head_snapshot("s1", "/repo", "abc123")
        assert cache.get_head_snapshot("s1") == {"cwd": "/repo", "sha": "abc123"}

    def test_clear(self):
        cache.save_head_snapshot("s1", "/repo", "abc123")
        cache.clear_head_snapshot("s1")
        assert cache.get_head_snapshot("s1") is None

    def test_file_is_owner_only(self):
        cache.save_head_snapshot("perm_head", "/repo", "abc123")
        path = os.path.join(cache.CACHE_DIR, f"{cache.HEAD_PREFIX}perm_head")
        assert oct(os.stat(path).st_mode & 0o777) == oct(0o600)


class TestBayesOffer:
    def test_offered_tables_empty(self):
        assert cache.get_bayes_offered_tables("s1") == []

    def test_add_offered_tables_dedupes(self):
        cache.add_bayes_offered_tables("s1", ["orders", "customers"])
        cache.add_bayes_offered_tables("s1", ["orders", "payments"])
        assert cache.get_bayes_offered_tables("s1") == ["orders", "customers", "payments"]

    def test_cleanup_covers_new_prefixes(self):
        assert cache.HEAD_PREFIX in cache.ALL_PREFIXES
        assert cache.BAYES_OFFERED_PREFIX in cache.ALL_PREFIXES


class TestHasVerifiedImpactCheck:
    def test_none(self):
        assert cache.has_verified_impact_check("s1") is False

    def test_injected_only(self):
        cache.mark_impact_check_injected("s1", "orders")
        assert cache.has_verified_impact_check("s1") is False

    def test_verified(self):
        cache.mark_impact_check_injected("s1", "orders")
        cache.mark_impact_check_injected("s1", "customers")
        cache.mark_impact_check_verified("s1", "customers")
        assert cache.has_verified_impact_check("s1") is True

    def test_other_session(self):
        cache.mark_impact_check_injected("s2", "orders")
        cache.mark_impact_check_verified("s2", "orders")
        assert cache.has_verified_impact_check("s1") is False

    @pytest.mark.parametrize("content", ["not json", "[]"])
    def test_unreadable_file_is_skipped(self, content):
        with open(os.path.join(cache.CACHE_DIR, cache.IC_PREFIX + "s1_bad"), "w") as f:
            f.write(content)
        cache.mark_impact_check_injected("s1", "orders")
        assert cache.has_verified_impact_check("s1") is False

    def test_missing_cache_dir(self, monkeypatch, tmp_path):
        monkeypatch.setattr(cache, "CACHE_DIR", str(tmp_path / "gone"))
        assert cache.has_verified_impact_check("s1") is False


class TestRemoveEditedTables:
    def test_removes_only_the_named_tables_in_order(self):
        for t in ("a", "b", "c"):
            cache.add_edited_table("s1", t)
        cache.remove_edited_tables("s1", ["b", "zzz"])
        assert cache.get_edited_tables("s1") == ["a", "c"]

    def test_removing_all_leaves_none(self):
        cache.add_edited_table("s1", "a")
        cache.remove_edited_tables("s1", ["a"])
        assert cache.get_edited_tables("s1") == []

    def test_no_file_is_fine(self):
        cache.remove_edited_tables("s1", ["a"])
        assert cache.get_edited_tables("s1") == []

    def test_other_sessions_untouched(self):
        cache.add_edited_table("s1", "a")
        cache.add_edited_table("s2", "a")
        cache.remove_edited_tables("s1", ["a"])
        assert cache.get_edited_tables("s2") == ["a"]


class TestCommitCheckpointClaim:
    DIGEST = "a" * 64

    def test_first_claim_wins(self):
        assert claim_commit_checkpoint("s1", self.DIGEST) is True
        assert claim_commit_checkpoint("s1", self.DIGEST) is False

    def test_claims_are_per_session_and_digest(self):
        assert claim_commit_checkpoint("s1", self.DIGEST) is True
        assert claim_commit_checkpoint("s2", self.DIGEST) is True
        assert claim_commit_checkpoint("s1", "b" * 64) is True

    @pytest.mark.parametrize("digest", ["", "a" * 63, "A" * 64, "../" + "a" * 61, "a" * 64 + "x"])
    def test_rejects_anything_but_a_sha256_hex_digest(self, digest):
        with pytest.raises(ValueError):
            claim_commit_checkpoint("s1", digest)

    @pytest.mark.parametrize("session", ["", "../etc", "a b", "a/b"])
    def test_rejects_invalid_session(self, session):
        with pytest.raises(ValueError):
            claim_commit_checkpoint(session, self.DIGEST)
        assert os.listdir(cache.CACHE_DIR) == []

    @pytest.mark.parametrize("session,valid", [
        ("s1", True), ("abc-DEF_123", True), ("", False), (None, False),
        ("a/b", False), ("a b", False), (123, False),
    ])
    def test_is_valid_session_id(self, session, valid):
        assert is_valid_session_id(session) is valid
