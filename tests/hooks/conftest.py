import sys
import os
import glob
import pytest

# Add hooks to path so all test files can import lib.*
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "plugins", "claude-code", "safe-change", "hooks"))


@pytest.fixture(autouse=True)
def clean_cache():
    """Clean up mc_safe_change temp files before/after each test."""
    for f in glob.glob("/tmp/mc_safe_change_*"):
        os.remove(f)
    yield
    for f in glob.glob("/tmp/mc_safe_change_*"):
        os.remove(f)
