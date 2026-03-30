"""Decorator that ensures hook scripts never block the engineer on error."""
import os
import sys
import traceback

DEBUG = os.environ.get("MC_SAFE_CHANGE_DEBUG", "").lower() in ("1", "true")


def safe_run(fn):
    """Catches all exceptions (including KeyboardInterrupt) and exits 0.

    When MC_SAFE_CHANGE_DEBUG=1, prints the traceback to stderr and re-raises
    so the error is visible and the hook reports a non-zero exit.
    """
    def wrapper():
        try:
            fn()
        except BaseException:
            if DEBUG:
                traceback.print_exc(file=sys.stderr)
                raise
            sys.exit(0)
    return wrapper
