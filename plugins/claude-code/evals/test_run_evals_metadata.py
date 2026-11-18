"""Offline tests for reading a skill's frontmatter into the trigger-eval judge prompt.

Run: uv run python -m unittest test_run_evals_metadata
"""
import tempfile
import unittest
from pathlib import Path

from run_evals import SKILLS_DIR, load_skill_metadata


class LoadSkillMetadata(unittest.TestCase):
    def load(self, frontmatter: str) -> tuple[str, str, str]:
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "SKILL.md").write_text(f"---\n{frontmatter}\n---\n\n# Body\n")
            return load_skill_metadata(Path(directory))

    def test_quoted_description_is_unquoted(self):
        self.assertEqual(self.load('name: x\ndescription: "A: B"'), ("x", "A: B", ""))

    def test_block_scalars_are_normalised(self):
        self.assertEqual(
            self.load(
                "name: x\ndescription: >\n  One\n  two.\n\n  Three.\n"
                "when_to_use: |\n  first\n\n    second\n  last"
            ),
            ("x", "One two. Three.", "first\nsecond\nlast"),
        )

    def test_inline_when_to_use(self):
        self.assertEqual(self.load("name: x\ndescription: d\nwhen_to_use: soon"), ("x", "d", "soon"))

    def test_missing_name_is_unknown(self):
        self.assertEqual(self.load("description: d"), ("unknown", "d", ""))

    def test_no_frontmatter_raises(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "SKILL.md").write_text("# Body\n")
            with self.assertRaises(ValueError):
                load_skill_metadata(Path(directory))

    def test_onboarding(self):
        name, description, when_to_use = load_skill_metadata(SKILLS_DIR / "onboarding")
        self.assertEqual(name, "monte-carlo-onboarding")
        self.assertTrue(description.startswith("Connect warehouses"), description)
        self.assertTrue(description.endswith("Terraform or scripts."), description)
        self.assertEqual(when_to_use, "")


if __name__ == "__main__":
    unittest.main()
