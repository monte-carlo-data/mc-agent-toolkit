"""Tests for scripts/build_coco_desktop.py. Stdlib only: run with `python3 <this file>`."""

import importlib.util
import json
import os
import re
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "build_coco_desktop.py"

_spec = importlib.util.spec_from_file_location("build_coco_desktop", SCRIPT)
build_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build_mod)


def write(path: Path, text: str, executable: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    if executable:
        path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def frontmatter(path: Path) -> tuple[dict, str]:
    """Parse the generated SKILL.md: `key: value` lines, JSON-quoted values allowed."""
    match = re.match(r"^---\n(.*?)\n---\n(.*)$", path.read_text(), re.S)
    assert match, f"{path} has no frontmatter"
    fields = {}
    for line in match.group(1).splitlines():
        key, _, value = line.partition(":")
        value = value.strip()
        fields[key.strip()] = json.loads(value) if value.startswith('"') else value
    return fields, match.group(2)


def tree(root: Path) -> dict:
    """Relative path -> (bytes, executable) for every file under root."""
    out = {}
    for path in sorted(root.rglob("*")):
        if path.is_file():
            out[str(path.relative_to(root))] = (path.read_bytes(), os.access(path, os.X_OK))
    return out


def make_fixture(root: Path) -> Path:
    """A small repo laid out like mc-agent-toolkit. Returns the plugin dir."""
    write(root / "LICENSE", "Apache License\n")
    write(root / "skills/alpha/SKILL.md", "---\nname: alpha-skill\ndescription: Alpha.\n---\n\nAlpha body.\n")
    write(root / "skills/alpha/scripts/run.sh", "#!/bin/sh\necho alpha\n", executable=True)
    write(root / "skills/alpha/tests/test_alpha.py", "# skill-level tests ship with the skill\n")
    write(root / "skills/beta/SKILL.md", "---\nname: beta\ndescription: Beta.\n---\n\nBeta body.\n")
    write(root / "README.md", "# repo\n")

    plugin = root / "plugins/cortex-code"
    manifest = {
        "name": "fixture-toolkit",
        "version": "9.9.9",
        "skills": "./skills/",
        "mcpServers": "./.mcp.json",
        "commands": ["./commands/x/", "./commands/y/"],
    }
    write(plugin / ".cortex-plugin/plugin.json", json.dumps(manifest, indent=2) + "\n")
    write(plugin / ".mcp.json", '{"mcpServers": {}}\n')
    write(plugin / "settings.json", "{}\n")
    write(plugin / "CHANGELOG.md", "# Changelog\n")
    write(
        plugin / "README.md",
        "# Fixture\n\n"
        "[alpha](../../skills/alpha/SKILL.md) [skills dir](../../skills/) [plugins](../README.md)\n"
        "[web](https://example.com/x) [anchor](#usage) [log](CHANGELOG.md) [settings](settings.json)\n",
    )
    (plugin / "skills").mkdir()
    os.symlink("../../../skills/alpha", plugin / "skills/alpha")
    os.symlink("../../../skills/beta", plugin / "skills/beta")
    # Name clash with skill frontmatter `beta` -> dropped.
    write(plugin / "commands/x/beta.md", "---\ndescription: Beta command.\n---\n\nRun beta.\n")
    # Folder clash with skills/alpha (whose name is alpha-skill) -> alpha-cmd.
    write(plugin / "commands/x/alpha.md", "---\ndescription: Alpha command.\n---\n\nRun alpha with $ARGUMENTS.\n")
    # No frontmatter: description from the first non-heading line.
    write(plugin / "commands/y/nofront.md", "# /nofront\n\nDo the thing.\n\nMore detail: `x`.\n")
    write(
        plugin / "commands/y/withfront.md",
        '---\ndescription: Says "hi": loudly\nargument-hint: <who>\n---\n\nGreet $ARGUMENTS.\n',
    )
    write(plugin / "hooks/hooks.json", '{"hooks": {}}\n')
    write(plugin / "hooks/prevent/pre.py", "print('x')\n")
    write(plugin / "hooks/prevent/lib/core.py", "X = 1\n")
    write(plugin / "hooks/prevent/lib/tests/test_core.py", "# dev only\n")
    write(plugin / "hooks/prevent/__pycache__/pre.cpython-312.pyc", "bytecode")
    write(plugin / "hooks/telemetry/scripts/beacon.sh", "#!/bin/sh\n", executable=True)
    write(plugin / "hooks/telemetry/tests/test_beacon.bats", "# dev only\n")
    write(plugin / "tests/test_plugin.py", "# dev only\n")
    write(plugin / "scripts/install.sh", "#!/bin/sh\n", executable=True)
    write(plugin / ".DS_Store", "junk")
    return plugin


class FixtureBuildTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.plugin = make_fixture(self.tmp / "repo")
        self.out = self.tmp / "dist"
        self.report = build_mod.build(self.plugin, self.out, ref="v9.9.9")

    def tearDown(self):
        self._tmp.cleanup()

    def test_no_symlinks_and_skills_are_real_copies(self):
        links = [p for p in self.out.rglob("*") if p.is_symlink()]
        self.assertEqual(links, [])
        self.assertEqual(
            (self.out / "skills/alpha/SKILL.md").read_bytes(),
            (self.tmp / "repo/skills/alpha/SKILL.md").read_bytes(),
        )

    def test_dev_artifacts_are_excluded(self):
        for rel in [
            "tests", "scripts", "commands", "hooks/prevent/lib/tests", "hooks/telemetry/tests",
            "hooks/prevent/__pycache__", ".DS_Store",
        ]:
            with self.subTest(rel=rel):
                self.assertFalse((self.out / rel).exists())

    def test_runtime_files_kept_with_exec_bits(self):
        self.assertTrue(os.access(self.out / "skills/alpha/scripts/run.sh", os.X_OK))
        self.assertTrue(os.access(self.out / "hooks/telemetry/scripts/beacon.sh", os.X_OK))
        self.assertTrue((self.out / "skills/alpha/tests/test_alpha.py").is_file())
        self.assertTrue((self.out / "hooks/prevent/lib/core.py").is_file())
        self.assertTrue((self.out / "hooks/hooks.json").is_file())
        self.assertTrue((self.out / "settings.json").is_file())

    def test_report(self):
        self.assertEqual(self.report["converted"], ["alpha-cmd", "nofront", "withfront"])
        self.assertEqual(self.report["dropped"], ["beta"])
        self.assertEqual(self.report["renamed"], ["alpha-cmd"])
        self.assertEqual(self.report["skills"], ["alpha", "alpha-cmd", "beta", "nofront", "withfront"])

    def test_command_with_frontmatter(self):
        fields, body = frontmatter(self.out / "skills/withfront/SKILL.md")
        self.assertEqual(fields["name"], "withfront")
        self.assertEqual(fields["description"], 'Says "hi": loudly. Triggers: /withfront, withfront.')
        self.assertEqual(body, "\nGreet $ARGUMENTS.\n")

    def test_command_without_frontmatter(self):
        fields, body = frontmatter(self.out / "skills/nofront/SKILL.md")
        self.assertEqual(fields["name"], "nofront")
        self.assertEqual(fields["description"], "Do the thing. Triggers: /nofront, nofront.")
        self.assertEqual(body, "\n# /nofront\n\nDo the thing.\n\nMore detail: `x`.\n")

    def test_only_manifest_command_paths_convert(self):
        out = self.tmp / "dist2"
        write(self.plugin / "commands/draft/unlisted.md", "---\ndescription: Draft.\n---\n\nNot shipped.\n")
        report = build_mod.build(self.plugin, out, ref="main")
        self.assertNotIn("unlisted", report["converted"])
        self.assertFalse((out / "skills/unlisted").exists())

    def test_command_frontmatter_name_wins_over_filename(self):
        out = self.tmp / "dist2"
        write(self.plugin / "commands/y/shortcut.md", "---\nname: published-name\ndescription: P.\n---\n\nBody.\n")
        report = build_mod.build(self.plugin, out, ref="main")
        self.assertIn("published-name", report["converted"])
        fields, _ = frontmatter(out / "skills/published-name/SKILL.md")
        self.assertEqual(fields["name"], "published-name")
        self.assertIn("/published-name", fields["description"])

    def test_folder_clash_keeps_command_name(self):
        fields, body = frontmatter(self.out / "skills/alpha-cmd/SKILL.md")
        self.assertEqual(fields["name"], "alpha")
        self.assertEqual(body, "\nRun alpha with $ARGUMENTS.\n")
        fields, _ = frontmatter(self.out / "skills/alpha/SKILL.md")
        self.assertEqual(fields["name"], "alpha-skill")

    def test_manifest(self):
        manifest = json.loads((self.out / ".cortex-plugin/plugin.json").read_text())
        self.assertNotIn("commands", manifest)
        self.assertEqual(manifest["version"], "9.9.9")
        self.assertEqual(manifest["skills"], "./skills/")

    def test_root_files(self):
        self.assertEqual((self.out / "LICENSE").read_text(), "Apache License\n")
        self.assertFalse((self.out / "CHANGELOG.md").exists())
        self.assertEqual((self.out / "docs/CHANGELOG.md").read_text(), "# Changelog\n")
        root_md = sorted(p.name for p in self.out.glob("*.md"))
        self.assertEqual(root_md, ["README.md"])

    def test_readme_links(self):
        text = (self.out / "README.md").read_text()
        base = "https://github.com/monte-carlo-data/mc-agent-toolkit"
        self.assertIn(f"[alpha]({base}/blob/v9.9.9/skills/alpha/SKILL.md)", text)
        self.assertIn(f"[skills dir]({base}/tree/v9.9.9/skills)", text)
        self.assertIn(f"[plugins]({base}/blob/v9.9.9/plugins/README.md)", text)
        self.assertIn("[web](https://example.com/x)", text)
        self.assertIn("[anchor](#usage)", text)
        self.assertIn("[log](docs/CHANGELOG.md)", text)
        self.assertIn("[settings](settings.json)", text)

    def test_deterministic(self):
        again = self.tmp / "dist2"
        build_mod.build(self.plugin, again, ref="v9.9.9")
        self.assertEqual(tree(self.out), tree(again))

    def test_cli_prints_report(self):
        out = self.tmp / "dist-cli"
        result = subprocess.run(
            ["python3", str(SCRIPT), str(self.plugin), str(out), "--ref", "v9.9.9"],
            capture_output=True, text=True, check=True,
        )
        self.assertEqual(json.loads(result.stdout)["dropped"], ["beta"])


class FixtureFailureTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.plugin = make_fixture(self.tmp / "repo")
        self.out = self.tmp / "dist"

    def tearDown(self):
        self._tmp.cleanup()

    def assert_build_fails(self, pattern):
        with self.assertRaisesRegex(build_mod.BuildError, pattern):
            build_mod.build(self.plugin, self.out, ref="main")
        self.assertFalse(self.out.exists(), "a failed build must leave no output")
        leftovers = [p.name for p in self.tmp.iterdir() if p.name not in ("repo", "outside")]
        self.assertEqual(leftovers, [], "a failed build must leave no staging dir")

    def test_existing_output(self):
        self.out.mkdir()
        with self.assertRaisesRegex(build_mod.BuildError, "exists"):
            build_mod.build(self.plugin, self.out, ref="main")

    def test_output_inside_source(self):
        with self.assertRaisesRegex(build_mod.BuildError, "inside"):
            build_mod.build(self.plugin, self.plugin / "dist", ref="main")

    def test_dangling_symlink(self):
        os.symlink("../../../skills/missing", self.plugin / "skills/missing")
        self.assert_build_fails("missing")

    def test_link_outside_the_repo(self):
        write(self.tmp / "outside/secret.txt", "not for publishing\n")
        os.symlink("../../../outside/secret.txt", self.plugin / "secret.txt")
        self.assert_build_fails("outside")

    def test_absolute_link_outside_the_repo(self):
        write(self.tmp / "outside/secret.txt", "not for publishing\n")
        os.symlink(str(self.tmp / "outside/secret.txt"), self.plugin / "secret.txt")
        self.assert_build_fails("outside")

    def test_nested_link_outside_the_repo(self):
        # Inside a skill the plugin reaches through its own (allowed) link.
        write(self.tmp / "outside/secret.txt", "not for publishing\n")
        os.symlink("../../../outside/secret.txt", self.tmp / "repo/skills/alpha/secret.txt")
        self.assert_build_fails("outside")

    def test_duplicate_command_names(self):
        write(self.plugin / "commands/y/nofront-dup.md", "Dup.\n")
        (self.plugin / "commands/y/nofront-dup.md").rename(self.plugin / "commands/x/nofront.md")
        self.assert_build_fails("nofront")

    def test_occupied_cmd_folder(self):
        write(self.tmp / "repo/skills/alpha-cmd/SKILL.md", "---\nname: other\ndescription: O.\n---\n\nO.\n")
        os.symlink("../../../skills/alpha-cmd", self.plugin / "skills/alpha-cmd")
        self.assert_build_fails("alpha-cmd")

    def test_empty_command_body(self):
        write(self.plugin / "commands/y/empty.md", "---\ndescription: Empty.\n---\n\n")
        self.assert_build_fails("empty")

    def test_manifest_path_missing(self):
        manifest_path = self.plugin / ".cortex-plugin/plugin.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["mcpServers"] = "./missing.json"
        manifest_path.write_text(json.dumps(manifest))
        self.assert_build_fails("missing.json")

    def test_manifest_path_escaping(self):
        manifest_path = self.plugin / ".cortex-plugin/plugin.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["mcpServers"] = "../../README.md"
        manifest_path.write_text(json.dumps(manifest))
        self.assert_build_fails("outside")

    def test_skill_without_description(self):
        write(self.tmp / "repo/skills/beta/SKILL.md", "---\nname: beta\n---\n\nBeta body.\n")
        self.assert_build_fails("description")


class InstallScriptAgreementTest(unittest.TestCase):
    def test_build_excludes_everything_install_sh_strips(self):
        """install.sh (CLI) and the Desktop build must strip the same dev artifacts."""
        text = (REPO_ROOT / "plugins/cortex-code/scripts/install.sh").read_text()
        stripped = re.findall(r'"\$STAGING/([^"]+)"', text)
        self.assertTrue(stripped)
        for rel in stripped:
            with self.subTest(rel=rel):
                self.assertTrue(build_mod.is_excluded(rel), f"install.sh strips {rel}; the build must too")


class RealPluginBuildTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls._tmp.name) / "dist"
        cls.report = build_mod.build(REPO_ROOT / "plugins/cortex-code", cls.out, ref="main")

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def expected_conversion(self):
        """What the current tree should convert to, derived from it so adding a command or skill needs no edit here."""
        plugin = REPO_ROOT / "plugins/cortex-code"
        skill_dirs = {p.name for p in (plugin / "skills").iterdir()}
        skill_names = set()
        for skill_md in (plugin / "skills").glob("*/SKILL.md"):
            fields, _ = build_mod.parse_frontmatter(skill_md.read_text())
            skill_names.add((fields or {}).get("name") or skill_md.parent.name)
        stems = sorted(p.stem for p in (plugin / "commands").rglob("*.md"))
        dropped = [s for s in stems if s in skill_names]
        kept = [s for s in stems if s not in skill_names]
        renamed = sorted(f"{s}-cmd" for s in kept if s in skill_dirs)
        converted = sorted(f"{s}-cmd" if s in skill_dirs else s for s in kept)
        return dropped, renamed, converted

    def test_command_conversion(self):
        dropped, renamed, converted = self.expected_conversion()
        self.assertEqual(self.report["dropped"], dropped)
        self.assertEqual(self.report["renamed"], renamed)
        self.assertEqual(self.report["converted"], converted)
        # The tree exercises every conversion path, so a regression in one shows up here too.
        self.assertTrue(dropped and renamed)
        self.assertIn("mc", converted)

    def test_every_source_skill_ships(self):
        source = sorted(p.name for p in (REPO_ROOT / "plugins/cortex-code/skills").iterdir())
        for name in source:
            with self.subTest(skill=name):
                src_tree = tree((REPO_ROOT / "plugins/cortex-code/skills" / name).resolve())
                expected = {k: v for k, v in src_tree.items() if not build_mod.is_excluded(f"skills/{name}/{k}")}
                self.assertEqual(tree(self.out / "skills" / name), expected)
        self.assertEqual(len(self.report["skills"]), len(source) + len(self.expected_conversion()[2]))

    def test_hooks_ship_whole(self):
        src = REPO_ROOT / "plugins/cortex-code/hooks"
        expected = {k: v for k, v in tree(src).items() if not build_mod.is_excluded(f"hooks/{k}")}
        self.assertEqual(tree(self.out / "hooks"), expected)

    def test_named_conversions(self):
        fields, body = frontmatter(self.out / "skills/instrument-agent-cmd/SKILL.md")
        self.assertEqual(fields["name"], "instrument-agent")
        source = (REPO_ROOT / "plugins/cortex-code/commands/instrument-agent/instrument-agent.md").read_text()
        self.assertTrue(source.endswith(body.lstrip("\n")))
        fields, body = frontmatter(self.out / "skills/mc-validate-lineage/SKILL.md")
        self.assertTrue(fields["description"].startswith("Verify that pushed table and column lineage"))
        self.assertTrue(body.startswith("\n# /mc-validate-lineage\n"))


if __name__ == "__main__":
    unittest.main()
