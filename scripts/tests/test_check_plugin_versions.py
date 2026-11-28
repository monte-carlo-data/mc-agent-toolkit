"""Tests for scripts/check_plugin_versions.py, run through its CLI as CI runs it.

Run: python3 scripts/tests/test_check_plugin_versions.py
"""
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "check_plugin_versions.py"
BUMP = (REPO_ROOT / "scripts" / "bump-version.sh").read_text()
MANIFESTS = re.findall(r'"([^"]+)"', re.search(r"VERSION_FILES=\(\n(.*?)\n\)", BUMP, re.DOTALL).group(1))


def run(root: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), str(root)], capture_output=True, text=True, check=False)


class CheckPluginVersions(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / "scripts").mkdir()
        (self.root / "scripts" / "bump-version.sh").write_text(BUMP)
        for path in MANIFESTS:
            self.write(path, {"name": "x", "version": "1.2.3"})

    def tearDown(self):
        self._tmp.cleanup()

    def write(self, path: str, data) -> None:
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(data, indent=2) + "\n")

    def test_the_list_covers_every_editor_plugin(self):
        self.assertEqual(len(MANIFESTS), 6)
        self.assertIn("plugins/cortex-code/.cortex-plugin/plugin.json", MANIFESTS)

    def test_agreeing_manifests_pass(self):
        result = run(self.root)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("1.2.3", result.stdout)

    def test_a_manifest_left_behind_fails_and_is_named(self):
        # The case that leaves a release with no Cortex Code build: only one manifest was bumped.
        self.write("plugins/claude-code/.claude-plugin/plugin.json", {"name": "x", "version": "1.2.4"})
        result = run(self.root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("plugins/claude-code/.claude-plugin/plugin.json: 1.2.4", result.stdout)
        self.assertIn("bump-version.sh", result.stdout)

    def test_a_missing_manifest_fails(self):
        (self.root / "plugins/opencode/package.json").unlink()
        result = run(self.root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("plugins/opencode/package.json", result.stdout)

    def test_a_manifest_without_a_version_fails(self):
        self.write("plugins/copilot/plugin.json", {"name": "x"})
        result = run(self.root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("plugins/copilot/plugin.json", result.stdout)

    def test_unreadable_json_fails(self):
        (self.root / "plugins/codex/.codex-plugin/plugin.json").write_text("{not json")
        result = run(self.root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("plugins/codex/.codex-plugin/plugin.json", result.stdout)

    def test_a_bump_script_without_the_list_fails(self):
        (self.root / "scripts" / "bump-version.sh").write_text("#!/bin/sh\n")
        result = run(self.root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("VERSION_FILES", result.stdout)

    def test_the_repo_passes(self):
        result = run(REPO_ROOT)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
