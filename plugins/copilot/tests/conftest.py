import sys
import os
import glob
import pytest

_hooks_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "hooks"))
_prevent_dir = os.path.join(_hooks_dir, "prevent")
# Add hooks dirs to path at collection time so test files can import lib.*
sys.path.insert(0, _hooks_dir)
sys.path.insert(0, _prevent_dir)


@pytest.fixture(autouse=True)
def clean_cache():
    """Clean up mc_prevent temp files before/after each test."""
    for f in glob.glob("/tmp/mc_prevent_*"):
        os.remove(f)
    yield
    for f in glob.glob("/tmp/mc_prevent_*"):
        os.remove(f)


@pytest.fixture(autouse=True)
def isolate_hook_modules():
    """Ensure Copilot hook modules are loaded from Copilot's hooks dir."""
    hook_modules = [
        "pre_edit_hook", "post_edit_hook", "pre_commit_hook",
        "turn_end_hook",
    ]
    for mod_name in hook_modules:
        sys.modules.pop(mod_name, None)
    # Ensure our hooks dir is first on sys.path for this test
    for d in [_hooks_dir, _prevent_dir]:
        if d in sys.path:
            sys.path.remove(d)
        sys.path.insert(0, d)
    yield
    for mod_name in hook_modules:
        sys.modules.pop(mod_name, None)
