"""Codex hook registration tests — plugin-bundled hooks.json and install.sh."""
import json
import os
import re
import shlex
import shutil
import subprocess
import sys

import pytest

_PLUGIN_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_REPO_ROOT = os.path.abspath(os.path.join(_PLUGIN_DIR, "..", ".."))
_HOOKS_JSON = os.path.join(_PLUGIN_DIR, "hooks", "prevent", "hooks.json")
_INSTALL_SH = os.path.join(_PLUGIN_DIR, "scripts", "install.sh")

# Codex sets PLUGIN_ROOT (and CLAUDE_PLUGIN_ROOT for compatibility) for
# plugin-bundled hook commands. See https://developers.openai.com/codex/hooks
_PLUGIN_ROOT_VAR = "${PLUGIN_ROOT}"
_VAR_PATTERN = re.compile(r"\$\{([A-Z_]+)\}")


def _hook_commands(hooks_config):
    for groups in hooks_config["hooks"].values():
        for group in groups:
            for hook in group["hooks"]:
                yield hook["command"]


def test_plugin_hooks_use_documented_plugin_root_var():
    with open(_HOOKS_JSON) as f:
        commands = list(_hook_commands(json.load(f)))

    assert commands
    for command in commands:
        assert _VAR_PATTERN.findall(command) == ["PLUGIN_ROOT"], command


def test_plugin_hook_commands_resolve_to_existing_scripts():
    with open(_HOOKS_JSON) as f:
        commands = list(_hook_commands(json.load(f)))

    for command in commands:
        script = shlex.split(command)[-1].replace(_PLUGIN_ROOT_VAR, _PLUGIN_DIR)
        assert os.path.isfile(script), command


@pytest.fixture
def installed(tmp_path):
    """Run install.sh --local into a scratch repo with an isolated HOME."""
    home = tmp_path / "home"
    target_repo = tmp_path / "repo"
    bin_dir = tmp_path / "bin"
    for d in (home, target_repo, bin_dir):
        d.mkdir()
    # Only python3 plus system tools on PATH, so `codex mcp login` is skipped.
    os.symlink(sys.executable, bin_dir / "python3")
    env = {"HOME": str(home), "PATH": f"{bin_dir}:/usr/bin:/bin", "TMPDIR": str(tmp_path)}

    if not shutil.which("cpio", path=env["PATH"]):
        pytest.skip("install.sh requires cpio")

    result = subprocess.run(
        ["bash", _INSTALL_SH, "--local", _REPO_ROOT, str(target_repo)],
        env=env, capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return target_repo


def test_install_does_not_register_plugin_hooks_twice(installed):
    """install.sh writes project-level hooks, so the installed plugin copy must
    not also declare them — Codex would otherwise run each hook twice once the
    user trusts the plugin's hooks."""
    manifest_path = installed / "plugins" / "mc-agent-toolkit" / ".codex-plugin" / "plugin.json"
    with open(manifest_path) as f:
        manifest = json.load(f)

    assert "hooks" not in manifest
    assert manifest["name"] == "mc-agent-toolkit"
    assert manifest["skills"] == "./skills/"


def test_install_project_hooks_point_to_installed_scripts(installed):
    with open(installed / ".codex" / "hooks.json") as f:
        commands = list(_hook_commands(json.load(f)))

    assert commands
    for command in commands:
        script = shlex.split(command)[-1]
        assert os.path.isabs(script), command
        assert os.path.isfile(script), command
