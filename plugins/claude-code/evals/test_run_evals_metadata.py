"""Offline tests for reading a skill's frontmatter into the trigger-eval judge prompt.

Run: uv run python -m unittest test_run_evals_metadata
"""
import tempfile
import unittest
from pathlib import Path

import yaml

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

    def test_closing_fence_at_end_of_file(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "SKILL.md").write_text("---\nname: x\ndescription: d\n---")
            self.assertEqual(load_skill_metadata(Path(directory)), ("x", "d", ""))

    def test_frontmatter_that_is_not_a_mapping_raises(self):
        for frontmatter in ("[]", "- x"):
            with self.subTest(frontmatter):
                with self.assertRaisesRegex(ValueError, "SKILL.md"):
                    self.load(frontmatter)

    def test_onboarding_quoted_description_is_decoded(self):
        text = (SKILLS_DIR / "onboarding" / "SKILL.md").read_text()
        self.assertIn('\ndescription: "', text)
        expected = yaml.safe_load(text.split("\n---\n", 1)[0].removeprefix("---\n"))
        self.assertEqual(
            load_skill_metadata(SKILLS_DIR / "onboarding"),
            (expected["name"], expected["description"], ""),
        )


if __name__ == "__main__":
    unittest.main()
