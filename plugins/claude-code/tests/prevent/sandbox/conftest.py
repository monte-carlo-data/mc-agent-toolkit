"""Shared fixtures for sandbox script tests."""
import sys
from pathlib import Path

# Make sandbox scripts importable for tests that want to call functions directly.
_SANDBOX_DIR = Path(__file__).resolve().parents[3] / "skills" / "prevent" / "scripts" / "sandbox"
sys.path.insert(0, str(_SANDBOX_DIR))
