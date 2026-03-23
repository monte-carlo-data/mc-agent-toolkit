import os
import time
import json
import pytest

from lib.cache import (
    get_workflow4_state,
    mark_workflow4_injected,
    mark_workflow4_verified,
    get_marker_age_seconds,
    get_edited_tables,
    add_edited_table,
    clear_edited_tables,
    move_to_pending_validation,
    get_pending_validation_tables,
    clear_pending_validation,
)


class TestWorkflow4State:
    def test_no_marker_returns_none(self):
        assert get_workflow4_state("my_table") is None

    def test_injected_state(self):
        mark_workflow4_injected("my_table")
        assert get_workflow4_state("my_table") == "injected"

    def test_verified_state(self):
        mark_workflow4_injected("my_table")
        mark_workflow4_verified("my_table")
        assert get_workflow4_state("my_table") == "verified"

    def test_marker_age(self):
        mark_workflow4_injected("my_table")
        age = get_marker_age_seconds("my_table")
        assert 0 <= age < 2  # Should be very recent

    def test_different_tables_independent(self):
        mark_workflow4_injected("table_a")
        mark_workflow4_verified("table_a")
        assert get_workflow4_state("table_a") == "verified"
        assert get_workflow4_state("table_b") is None


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
