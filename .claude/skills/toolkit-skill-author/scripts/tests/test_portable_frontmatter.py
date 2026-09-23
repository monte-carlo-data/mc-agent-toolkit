"""Portable metadata frontmatter remains compatible with legacy skill linting."""
import contextlib
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('lint_skill', Path(__file__).parents[1] / 'lint-skill.py')
linter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(linter)


class PortableFrontmatter(unittest.TestCase):
    def check(self, extra):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'example').mkdir()
            (root / 'example' / 'SKILL.md').write_text(
                '---\nname: monte-carlo-example\ndescription: Connect a warehouse.\n'
                + extra + '\n---\nWorkflow.\n')
            with contextlib.redirect_stdout(io.StringIO()):
                return linter.lint('example', root)

    def test_standard_metadata_without_vendor_extension(self):
        self.assertEqual(self.check('metadata:\n  bucket: Setup'), ([], []))

    def test_invalid_metadata_bucket(self):
        errors, _ = self.check('metadata:\n  bucket: Wrong')
        self.assertTrue(any('not a valid capability bucket' in e for e in errors))

    def test_legacy_bucket_and_trigger(self):
        self.assertEqual(self.check('bucket: Setup\nwhen_to_use: When connecting data.'), ([], []))

    def test_legacy_warning_preserved(self):
        errors, warnings = self.check('bucket: Setup')
        self.assertFalse(errors)
        self.assertTrue(any('when_to_use' in w for w in warnings))

    def test_missing_metadata_bucket_still_fails(self):
        errors, _ = self.check('metadata:\n  owner: example')
        self.assertTrue(any('bucket is missing' in e for e in errors))


if __name__ == '__main__':
    unittest.main()
