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


def test_safe_run_debug_mode_reraises(monkeypatch):
    """In debug mode, exceptions propagate instead of being swallowed."""
    monkeypatch.setenv("MC_SAFE_CHANGE_DEBUG", "1")
    # Re-import to pick up the env var change
    import importlib
    import lib.safe_run as sr
    importlib.reload(sr)

    @sr.safe_run
    def bad_fn():
        raise ValueError("boom")

    with pytest.raises(ValueError, match="boom"):
        bad_fn()


def test_safe_run_debug_mode_prints_traceback(monkeypatch, capsys):
    """Debug mode prints traceback to stderr."""
    monkeypatch.setenv("MC_SAFE_CHANGE_DEBUG", "1")
    import importlib
    import lib.safe_run as sr
    importlib.reload(sr)

    @sr.safe_run
    def bad_fn():
        raise RuntimeError("debug trace")

    with pytest.raises(RuntimeError):
        bad_fn()

    captured = capsys.readouterr()
    assert "debug trace" in captured.err
