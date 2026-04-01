"""Decorator that ensures hook scripts never block the engineer on error."""
import sys


def safe_run(fn):
    """Catches all exceptions (including KeyboardInterrupt) and exits 0."""
    def wrapper():
        try:
            fn()
        except BaseException:
            sys.exit(0)
    return wrapper
