"""Checks the Cortex Code hook config against how Cortex Code loads and matches hooks.

Cortex Code reads a plugin's hooks from ``hooks/hooks.json`` at the plugin root. CoCo
Desktop ignores a manifest ``hooks`` array, so the manifest must not declare one.
Matchers are unanchored, case-sensitive regexes tested against Cortex's lowercase tool
IDs (``bash``, ``edit``, ``write``, ``multi_edit``, ``skill``); PascalCase names never
match. ``${CORTEX_PLUGIN_ROOT}`` is substituted into the command text, not exported, so
the commands must quote it to survive install paths that contain spaces.

Stdlib only, so CI can run it with plain ``python3``.
"""

import json
import os
import re
import shlex
import unittest
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
HOOKS_FILE = PLUGIN_ROOT / "hooks" / "hooks.json"
MANIFEST = PLUGIN_ROOT / ".cortex-plugin" / "plugin.json"

EDIT_TOOLS = ["edit", "write", "multi_edit"]
# Tool IDs that must never trigger a hook meant for another tool: lookalikes Cortex
# registers, plus the PascalCase names Cortex never sends.
NEVER = [
    "bash_output", "notebook_edit_cell", "notebook_edit", "apply_patch", "read", "grep",
    "Bash", "Edit", "Write", "MultiEdit", "Skill", "skill_search", "",
]

# (event, script relative to plugin root, tool IDs that must match or None for no matcher)
EXPECTED = [
    ("SessionStart", "hooks/telemetry/scripts/ensure-toolkit-ids.sh", None),
    ("PreToolUse", "hooks/prevent/pre_edit_hook.py", EDIT_TOOLS),
    ("PreToolUse", "hooks/prevent/pre_commit_hook.py", ["bash"]),
    ("PreToolUse", "hooks/telemetry/scripts/skill-beacon.sh", ["skill"]),
    ("PostToolUse", "hooks/prevent/post_edit_hook.py", EDIT_TOOLS),
    ("Stop", "hooks/prevent/turn_end_hook.py", None),
]

ROOT_VAR = "${CORTEX_PLUGIN_ROOT}"


def cortex_matches(matcher, tool_name):
    """Cortex's matcher semantics: missing or '*' matches all, else an unanchored regex."""
    if not matcher or matcher == "*":
        return True
    try:
        return re.search(matcher, tool_name) is not None
    except re.error:
        return matcher == tool_name


def load_handlers():
    """Flatten hooks.json into (event, matcher, command) tuples."""
    config = json.loads(HOOKS_FILE.read_text())
    handlers = []
    for event, groups in config["hooks"].items():
        for group in groups:
            for hook in group["hooks"]:
                handlers.append((event, group.get("matcher"), hook["command"]))
    return handlers


def script_of(command):
    """The plugin-relative script a command runs, after quoting is applied."""
    fake_root = "/tmp/cortex plugin root"
    for token in shlex.split(command.replace(ROOT_VAR, fake_root)):
        if token.startswith(fake_root + "/"):
            return token[len(fake_root) + 1:]
    return None


class HookConfigTest(unittest.TestCase):
    def test_manifest_does_not_declare_hooks(self):
        manifest = json.loads(MANIFEST.read_text())
        self.assertNotIn("hooks", manifest, "Desktop ignores a hooks array; rely on hooks/hooks.json")

    def test_single_root_hooks_file(self):
        self.assertTrue(HOOKS_FILE.is_file())
        nested = sorted(str(p.relative_to(PLUGIN_ROOT)) for p in PLUGIN_ROOT.glob("hooks/*/hooks.json"))
        self.assertEqual(nested, [], "per-feature hooks.json files are not loaded by Cortex Code")

    def test_every_command_quotes_the_plugin_root(self):
        for event, _, command in load_handlers():
            with self.subTest(event=event, command=command):
                self.assertIsNotNone(script_of(command), "the root must be quoted with the script path")

    def test_handlers_are_exactly_the_expected_set(self):
        actual = sorted((event, script_of(command)) for event, _, command in load_handlers())
        expected = sorted((event, script) for event, script, _ in EXPECTED)
        self.assertEqual(actual, expected)

    def test_matchers_hit_only_their_tools(self):
        by_key = {(event, script_of(command)): matcher for event, matcher, command in load_handlers()}
        for event, script, tools in EXPECTED:
            matcher = by_key.get((event, script))
            with self.subTest(event=event, script=script, matcher=matcher):
                if tools is None:
                    self.assertIsNone(matcher)
                    continue
                for tool in tools:
                    self.assertTrue(cortex_matches(matcher, tool), f"{matcher!r} must match {tool!r}")
                others = [t for t in NEVER + EDIT_TOOLS + ["bash", "skill"] if t not in tools]
                for tool in others:
                    self.assertFalse(cortex_matches(matcher, tool), f"{matcher!r} must not match {tool!r}")

    def test_scripts_exist_and_direct_ones_are_executable(self):
        for event, _, command in load_handlers():
            script = script_of(command)
            path = PLUGIN_ROOT / script
            with self.subTest(event=event, script=script):
                self.assertTrue(path.is_file())
                if shlex.split(command.replace(ROOT_VAR, "/r"))[0] != "python3":
                    self.assertTrue(os.access(path, os.X_OK), "run without an interpreter, so it must be executable")


if __name__ == "__main__":
    unittest.main()
