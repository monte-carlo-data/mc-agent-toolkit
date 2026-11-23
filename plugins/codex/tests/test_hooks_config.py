"""Checks the Codex hook registrations against how Codex matches hooks.

Codex (0.124.0+) sends PreToolUse and PostToolUse for its own `apply_patch` tool with
`tool_name: "apply_patch"`, and `"Bash"` for shell commands. A matcher made only of
letters, digits, `_` and `|` matches a tool name exactly (`codex-rs/hooks/src/engine/matcher.rs`).

Two configs register the hooks: the plugin's `hooks/prevent/hooks.json`, and the
project-level `.codex/hooks.json` that `scripts/install.sh` writes. Both are checked, and
each registered Prevent script is run with an apply_patch payload to prove it reads it.

Stdlib only, so CI can run it with plain ``python3``.
"""

import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_HOOKS = PLUGIN_ROOT / "hooks" / "prevent" / "hooks.json"
MANIFEST = PLUGIN_ROOT / ".codex-plugin" / "plugin.json"
INSTALLER = PLUGIN_ROOT / "scripts" / "install.sh"

# (event, tool name or None, script that must handle it)
EXPECTED = [
    ("PreToolUse", "Bash", "hooks/prevent/bash_hook.py"),
    ("PreToolUse", "apply_patch", "hooks/prevent/bash_hook.py"),
    ("PostToolUse", "apply_patch", "hooks/prevent/post_edit_hook.py"),
    ("Stop", None, "hooks/prevent/turn_end_hook.py"),
]
NEVER = ["bash", "Edit", "Write", "apply_patch_v2", "my_apply_patch", "spawn_agent", ""]


def codex_matches(matcher, tool_name):
    """Codex's matcher semantics: missing or '*' matches all; [A-Za-z0-9_|]+ is an exact
    list; anything else an unanchored regex."""
    if not matcher or matcher == "*":
        return True
    if re.fullmatch(r"[A-Za-z0-9_|]+", matcher):
        return tool_name in matcher.split("|")
    return tool_name is not None and re.search(matcher, tool_name) is not None


# Runs a hook script as __main__ with Prevent's cache in a temp dir, so the test never
# touches /tmp/mc_prevent_* state of agent sessions running on this machine.
_RUN_WITH_CACHE_DIR = """
import runpy, sys
script, cache_dir = sys.argv[1], sys.argv[2]
sys.argv = [script]
sys.path.insert(0, __import__("os").path.dirname(script))
import lib.cache
lib.cache.CACHE_DIR = cache_dir
runpy.run_path(script, run_name="__main__")
"""


def installer_hooks(hooks_dir, telemetry_dir):
    """The JSON install.sh writes, with its shell variables filled in."""
    text = INSTALLER.read_text()
    body = re.search(r'cat > "\$HOOKS_FILE" << HOOKEOF\n(.*?)\nHOOKEOF\n', text, re.S).group(1)
    body = body.replace("$HOOKS_DIR", hooks_dir).replace("$TELEMETRY_DIR", telemetry_dir)
    return json.loads(body)


def handlers(config, event, tool_name):
    found = []
    for group in config["hooks"].get(event, []):
        if codex_matches(group.get("matcher"), tool_name):
            found += [h["command"] for h in group["hooks"]]
    return found


class HookConfigTests(unittest.TestCase):
    def configs(self):
        root = "${CODEX_PLUGIN_ROOT}"
        return {
            "plugin": (json.loads(PLUGIN_HOOKS.read_text()), root),
            "installer": (installer_hooks(str(PLUGIN_ROOT / "hooks" / "prevent"),
                                          str(PLUGIN_ROOT / "hooks" / "telemetry" / "scripts")), str(PLUGIN_ROOT)),
        }

    def test_manifest_points_at_the_plugin_hooks(self):
        self.assertEqual(json.loads(MANIFEST.read_text())["hooks"], "./hooks/prevent/hooks.json")

    def test_each_tool_reaches_its_script_once(self):
        for name, (config, root) in self.configs().items():
            for event, tool, script in EXPECTED:
                with self.subTest(config=name, event=event, tool=tool):
                    commands = handlers(config, event, tool)
                    matching = [c for c in commands if script in c]
                    self.assertEqual(len(matching), 1, commands)

    def test_lookalike_tools_reach_no_prevent_edit_hook(self):
        for name, (config, _) in self.configs().items():
            for event in ("PreToolUse", "PostToolUse"):
                for tool in NEVER:
                    with self.subTest(config=name, event=event, tool=tool):
                        self.assertEqual(handlers(config, event, tool), [])

    def test_installer_keeps_session_start(self):
        config, _ = self.configs()["installer"]
        commands = handlers(config, "SessionStart", None)
        self.assertTrue(any("ensure-toolkit-ids.sh" in c for c in commands), commands)

    def test_registered_commands_gate_and_track_a_patch(self):
        """Run what each config registers, as Codex would, on a real dbt project."""
        for name, (config, root) in self.configs().items():
            with self.subTest(config=name), tempfile.TemporaryDirectory() as tmp:
                project = Path(tmp) / "proj"
                (project / "models").mkdir(parents=True)
                (project / "models" / "orders.sql").write_text("SELECT * FROM {{ ref('raw') }}\n")
                cache_dir = Path(tmp) / "cache"
                cache_dir.mkdir()
                env = {**os.environ, "CODEX_PLUGIN_ROOT": str(PLUGIN_ROOT)}
                env.pop("MC_PREVENT_HOOKS_DISABLED", None)
                patch = "*** Begin Patch\n*** Delete File: models/orders.sql\n*** End Patch"

                def run(event, tool, extra=None):
                    (command,) = [c for c in handlers(config, event, tool) if "/prevent/" in c]
                    argv = shlex.split(command.replace("${CODEX_PLUGIN_ROOT}", str(PLUGIN_ROOT)))
                    payload = {"session_id": f"cfg_{name}", "transcript_path": "", "cwd": str(project),
                               "hook_event_name": event, "tool_name": tool,
                               "tool_input": {"command": patch}, "tool_use_id": "call_cfg", **(extra or {})}
                    return subprocess.run([sys.executable, "-c", _RUN_WITH_CACHE_DIR, argv[1], str(cache_dir)],
                                          input=json.dumps(payload),
                                          capture_output=True, text=True, env=env, check=True).stdout

                out = run("PreToolUse", "apply_patch")
                self.assertEqual(json.loads(out)["hookSpecificOutput"]["permissionDecision"], "deny")
                shell = run("PreToolUse", "Bash", {"tool_input": {
                    "command": f"apply_patch <<'EOF'\n{patch}\nEOF\n"}})
                self.assertEqual(json.loads(shell)["hookSpecificOutput"]["permissionDecision"], "deny")
                self.assertEqual(run("PostToolUse", "apply_patch"), "")


if __name__ == "__main__":
    unittest.main()
