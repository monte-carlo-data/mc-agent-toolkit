import sys
import os
import pytest

# Add hooks/prevent to path so `from lib.<module>` resolves from any working directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


@pytest.fixture(autouse=True)
def clean_cache(tmp_path, monkeypatch):
    """Give each test its own empty cache directory.

    Deleting /tmp/mc_prevent_* instead would wipe the live Prevent state of any
    agent session running on the same machine.
    """
    import lib.cache as cache
    monkeypatch.setattr(cache, "CACHE_DIR", str(tmp_path))
    yield
