import sys
import os
import pytest

_hooks_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "hooks", "prevent"))
# Add hooks to path at collection time so test files can import lib.*
sys.path.insert(0, _hooks_dir)

import lib.cache as cache  # noqa: E402


@pytest.fixture(autouse=True)
def clean_cache(tmp_path, monkeypatch):
    """Give each test its own empty prevent cache directory.

    Pointing CACHE_DIR at a per-test directory keeps tests from reading or deleting
    the /tmp/mc_prevent_* state of real sessions running on the same machine.
    """
    cache_dir = tmp_path / "mc_prevent_cache"
    cache_dir.mkdir()
    monkeypatch.setattr(cache, "CACHE_DIR", str(cache_dir))
    yield


@pytest.fixture(autouse=True)
def isolate_hook_modules():
    """Ensure Cortex hook modules are loaded from Cortex's hooks dir (not another plugin's
    identically-named module)."""
    hook_modules = ["pre_edit_hook", "post_edit_hook", "pre_commit_hook", "turn_end_hook", "patch_result"]
    for mod_name in hook_modules:
        sys.modules.pop(mod_name, None)
    if _hooks_dir in sys.path:
        sys.path.remove(_hooks_dir)
    sys.path.insert(0, _hooks_dir)
    yield
    for mod_name in hook_modules:
        sys.modules.pop(mod_name, None)
