import sys
import os
import pytest

_hooks_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "hooks", "prevent"))
# Add hooks to path at collection time so test files can import lib.*
sys.path.insert(0, _hooks_dir)


@pytest.fixture(autouse=True)
def clean_cache(tmp_path, monkeypatch):
    """Give each test its own empty cache directory.

    Deleting /tmp/mc_prevent_* instead would wipe the live Prevent state of any
    agent session running on the same machine.
    """
    import lib.cache as cache
    monkeypatch.setattr(cache, "CACHE_DIR", str(tmp_path))
    yield


@pytest.fixture(autouse=True)
def isolate_hook_modules():
    """Ensure Codex hook modules are loaded from Codex's hooks dir."""
    hook_modules = [
        "post_edit_hook", "turn_end_hook", "bash_hook", "shell_patch",
    ]
    for mod_name in hook_modules:
        sys.modules.pop(mod_name, None)
    # Ensure our hooks dir is first on sys.path for this test
    if _hooks_dir in sys.path:
        sys.path.remove(_hooks_dir)
    sys.path.insert(0, _hooks_dir)
    yield
    for mod_name in hook_modules:
        sys.modules.pop(mod_name, None)
