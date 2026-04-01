import sys
import os
import glob
import pytest

# Add the shared lib to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture(autouse=True)
def clean_cache():
    """Clean up mc_prevent temp files before/after each test."""
    for f in glob.glob("/tmp/mc_prevent_*"):
        os.remove(f)
    yield
    for f in glob.glob("/tmp/mc_prevent_*"):
        os.remove(f)
