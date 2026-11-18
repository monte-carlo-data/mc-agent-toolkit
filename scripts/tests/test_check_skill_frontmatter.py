"""Tests for scripts/check_skill_frontmatter.py, run through its CLI as CI runs it.

Run: python3 scripts/tests/test_check_skill_frontmatter.py   (needs PyYAML)
"""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "check_skill_frontmatter.py"

GOOD = "---\nname: monte-carlo-example\ndescription: Connect a warehouse.\n---\n\n# Example\n"

# The onboarding description as it shipped in 1.30.0: unquoted, with ": " inside.
ONBOARDING_UNQUOTED = (
    "description: Connect warehouses, BI tools (Tableau, Looker, Power BI) and custom connectors"
    " to Monte Carlo with API v2 tools: show what exists, reference credentials, create, validate"
    " and fix connections. Use to onboard platforms or generate Terraform or scripts."
)


def run(*roots: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, roots)], capture_output=True, text=True
    )


class CheckSkillFrontmatter(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / "skills"
        self.root.mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    def skill(self, folder: str, text: str) -> Path:
        (self.root / folder).mkdir()
        path = self.root / folder / "SKILL.md"
        path.write_text(text)
        return path

    def assert_fails(self, text: str, reason: str):
        path = self.skill("broken", text)
        result = run(self.root)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn(f"::error file={path}::", result.stdout)
        self.assertIn(reason, result.stdout)

    def test_good_skill_passes(self):
        self.skill("example", GOOD)
        result = run(self.root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("OK: 1 skills checked", result.stdout)

    def test_unquoted_colon_in_description_fails(self):
        self.assert_fails(
            f"---\nname: monte-carlo-onboarding\n{ONBOARDING_UNQUOTED}\n---\nBody.\n",
            "not valid YAML",
        )

    def test_quoted_onboarding_description_passes(self):
        value = ONBOARDING_UNQUOTED.split(": ", 1)[1]
        self.skill("onboarding", f'---\nname: monte-carlo-onboarding\ndescription: "{value}"\n---\nBody.\n')
        self.assertEqual(run(self.root).returncode, 0)

    def test_block_scalar_description_passes(self):
        # Parser compatibility: shipped skills use | and > blocks, and a block may hold an indented ---.
        self.skill(
            "example",
            "---\nname: monte-carlo-example\ndescription: |\n  Line one: with a colon.\n  ---\n  Line two.\n---\nBody.\n",
        )
        self.assertEqual(run(self.root).returncode, 0)

    def test_no_frontmatter_fails(self):
        self.assert_fails("# Example\n\nNo frontmatter.\n", "no frontmatter")

    def test_opening_fence_must_be_exact(self):
        self.assert_fails("--- \nname: x\ndescription: y\n---\nBody.\n", "no frontmatter")

    def test_missing_closing_fence_fails(self):
        self.assert_fails("---\nname: x\ndescription: y\n\nBody.\n", "no closing ---")

    def test_closing_fence_with_suffix_fails(self):
        self.assert_fails("---\nname: x\ndescription: y\n---oops\nBody.\n", "no closing ---")

    def test_top_level_not_a_mapping_fails(self):
        self.assert_fails("---\n- name\n- description\n---\nBody.\n", "not a mapping")

    def test_required_fields(self):
        cases = {
            "missing name": ("description: y", "name"),
            "missing description": ("name: x", "description"),
            "blank name": ('name: "   "\ndescription: y', "name"),
            "empty description": ("name: x\ndescription:", "description"),
            "boolean description": ("name: x\ndescription: yes", "description"),
            "list name": ("name: [a, b]\ndescription: y", "name"),
        }
        for i, (label, (body, field)) in enumerate(cases.items()):
            with self.subTest(label):
                self.root = Path(self._tmp.name) / f"skills-{i}"
                self.root.mkdir()
                self.assert_fails(f"---\n{body}\n---\nBody.\n", f"`{field}` must be")

    def test_broken_sibling_fails_then_passes_when_fixed(self):
        self.skill("good", GOOD)
        broken = self.skill("onboarding", f"---\nname: monte-carlo-onboarding\n{ONBOARDING_UNQUOTED}\n---\nBody.\n")
        result = run(self.root)
        self.assertEqual(result.returncode, 1)
        self.assertIn(str(broken), result.stdout)
        self.assertNotIn(str(self.root / "good"), result.stdout)

        broken.write_text(GOOD)
        result = run(self.root)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("OK: 2 skills checked", result.stdout)

    def test_every_root_is_checked(self):
        other = Path(self._tmp.name) / "other"
        (other / "broken").mkdir(parents=True)
        (other / "broken" / "SKILL.md").write_text("---\nname: x\n---\nBody.\n")
        self.skill("good", GOOD)
        result = run(self.root, other)
        self.assertEqual(result.returncode, 1)
        self.assertIn(str(other / "broken" / "SKILL.md"), result.stdout)

    def test_missing_root_fails(self):
        result = run(Path(self._tmp.name) / "skils")
        self.assertEqual(result.returncode, 1)
        self.assertIn("does not exist", result.stdout)

    def test_root_without_skills_fails(self):
        result = run(self.root)
        self.assertEqual(result.returncode, 1)
        self.assertIn("no */SKILL.md", result.stdout)


if __name__ == "__main__":
    unittest.main()
