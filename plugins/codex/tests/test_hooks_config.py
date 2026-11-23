"""Checks the Codex hook registrations against how Codex matches hooks.

Codex (0.124.0+) sends PreToolUse and PostToolUse for its own `apply_patch` tool with
`tool_name: "apply_patch"`, and `"Bash"` for shell commands. A matcher made only of
letters, digits, `_` and `|` matches a tool name exactly (`codex-rs/hooks/src/engine/matcher.rs`).

Two configs register the hooks: the plugin's `hooks/prevent/hooks.json`, and the
project-level `.codex/hooks.json` that `scripts/install.sh` writes. Both are checked, and
each registered command is run through a shell with the env vars Codex gives plugin hooks
(`PLUGIN_ROOT`, `CLAUDE_PLUGIN_ROOT`; never `CODEX_PLUGIN_ROOT`), from a copy of the plugin
whose path contains a space, to prove it starts, reads an apply_patch payload, denies, and tracks.

Stdlib only, so CI can run it with plain ``python3``.
"""

import json
import os
import re
import shutil
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
        return {
            "plugin": json.loads(PLUGIN_HOOKS.read_text()),
            "installer": installer_hooks(str(PLUGIN_ROOT / "hooks" / "prevent"),
                                         str(PLUGIN_ROOT / "hooks" / "telemetry" / "scripts")),
        }

    def test_manifest_points_at_the_plugin_hooks(self):
        self.assertEqual(json.loads(MANIFEST.read_text())["hooks"], "./hooks/prevent/hooks.json")

    def test_each_tool_reaches_its_script_once(self):
        for name, config in self.configs().items():
            for event, tool, script in EXPECTED:
                with self.subTest(config=name, event=event, tool=tool):
                    commands = handlers(config, event, tool)
                    matching = [c for c in commands if script in c]
                    self.assertEqual(len(matching), 1, commands)

    def test_lookalike_tools_reach_no_prevent_edit_hook(self):
        for name, config in self.configs().items():
            for event in ("PreToolUse", "PostToolUse"):
                for tool in NEVER:
                    with self.subTest(config=name, event=event, tool=tool):
                        self.assertEqual(handlers(config, event, tool), [])

    def test_installer_keeps_session_start(self):
        config = self.configs()["installer"]
        commands = handlers(config, "SessionStart", None)
        self.assertTrue(any("ensure-toolkit-ids.sh" in c for c in commands), commands)

    def test_registered_commands_gate_and_track_a_patch(self):
        """Run what each config registers the way Codex does, from a copy of the plugin
        whose path has a space, and check a deny and an allow-then-track."""
        for name in ("plugin", "installer"):
            with self.subTest(config=name), tempfile.TemporaryDirectory() as tmp:
                tmp = Path(tmp)
                plugin_copy = tmp / "my plugin"
                shutil.copytree(PLUGIN_ROOT / "hooks", plugin_copy / "hooks",
                                ignore=shutil.ignore_patterns("__pycache__"))
                hooks_dir = plugin_copy / "hooks" / "prevent"
                cache_dir = tmp / "cache"
                cache_dir.mkdir()
                cache_py = hooks_dir / "lib" / "cache.py"
                source = cache_py.read_text()
                rewritten = re.sub(r"(?m)^CACHE_DIR = .*$", lambda _: f"CACHE_DIR = {str(cache_dir)!r}", source)
                self.assertNotEqual(rewritten, source, "CACHE_DIR assignment not found")
                cache_py.write_text(rewritten)

                if name == "plugin":
                    config = json.loads(PLUGIN_HOOKS.read_text())
                else:
                    config = installer_hooks(str(hooks_dir), str(plugin_copy / "hooks" / "telemetry" / "scripts"))

                env = {**os.environ, "PLUGIN_ROOT": str(plugin_copy), "CLAUDE_PLUGIN_ROOT": str(plugin_copy)}
                env.pop("CODEX_PLUGIN_ROOT", None)
                env.pop("MC_PREVENT_HOOKS_DISABLED", None)

                project = tmp / "proj"
                (project / "models").mkdir(parents=True)
                (project / "models" / "orders.sql").write_text("SELECT * FROM {{ ref('raw') }}\n")
                session_id = f"cfg_{name}"

                def run(event, tool, command_text, tool_use_id):
                    (command,) = handlers(config, event, tool)
                    payload = {"session_id": session_id, "transcript_path": "", "cwd": str(project),
                               "hook_event_name": event, "tool_name": tool,
                               "tool_input": {"command": command_text}, "tool_use_id": tool_use_id}
                    result = subprocess.run(command, shell=True, env=env, input=json.dumps(payload),
                                            capture_output=True, text=True)
                    self.assertEqual(result.returncode, 0,
                                     f"{command!r} exited {result.returncode}: {result.stderr}")
                    return result.stdout

                def decision(out):
                    return json.loads(out)["hookSpecificOutput"]["permissionDecision"] if out.strip() else None

                delete = "*** Begin Patch\n*** Delete File: models/orders.sql\n*** End Patch"
                self.assertEqual(decision(run("PreToolUse", "apply_patch", delete, "call_del")), "deny")
                shell = f"apply_patch <<'EOF'\n{delete}\nEOF\n"
                self.assertEqual(decision(run("PreToolUse", "Bash", shell, "call_sh")), "deny")

                add = ("*** Begin Patch\n*** Add File: models/brand_new.sql\n"
                       "+SELECT * FROM {{ ref('raw') }}\n*** End Patch")
                self.assertNotEqual(decision(run("PreToolUse", "apply_patch", add, "call_add")), "deny")
                (project / "models" / "brand_new.sql").write_text("SELECT * FROM {{ ref('raw') }}\n")
                run("PostToolUse", "apply_patch", add, "call_add")

                read_tables = (
                    "import json, sys; sys.path.insert(0, sys.argv[1]); "
                    "from lib.cache import get_edited_tables; print(json.dumps(get_edited_tables(sys.argv[2])))"
                )
                tables = subprocess.run([sys.executable, "-c", read_tables, str(hooks_dir), session_id],
                                        capture_output=True, text=True, check=True).stdout
                self.assertEqual(json.loads(tables), ["brand_new"])


if __name__ == "__main__":
    unittest.main()
