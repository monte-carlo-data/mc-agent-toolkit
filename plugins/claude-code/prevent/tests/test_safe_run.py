import pytest
from lib.safe_run import safe_run


def test_safe_run_passes_through_on_success():
    """Function that succeeds should run normally."""
    calls = []

    @safe_run
    def good_fn():
        calls.append("ran")

    good_fn()
    assert calls == ["ran"]


def test_safe_run_exits_0_on_exception():
    """Function that raises should cause exit(0), not propagate."""

    @safe_run
    def bad_fn():
        raise ValueError("boom")

    with pytest.raises(SystemExit) as exc_info:
        bad_fn()
    assert exc_info.value.code == 0


def test_safe_run_exits_0_on_keyboard_interrupt():
    """Even KeyboardInterrupt should exit 0."""

    @safe_run
    def interrupted_fn():
        raise KeyboardInterrupt()

    with pytest.raises(SystemExit) as exc_info:
        interrupted_fn()
    assert exc_info.value.code == 0
