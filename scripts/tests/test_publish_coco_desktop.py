"""Tests for scripts/publish_coco_desktop.py against a local bare remote. Stdlib only."""

import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, REPO_ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


publish_mod = load("publish_coco_desktop")
build_tests = importlib.util.spec_from_file_location(
    "test_build_coco_desktop", REPO_ROOT / "scripts" / "tests" / "test_build_coco_desktop.py"
)
fixture_mod = importlib.util.module_from_spec(build_tests)
build_tests.loader.exec_module(fixture_mod)

GIT_ENV = {
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_AUTHOR_NAME": "Test",
    "GIT_AUTHOR_EMAIL": "test@example.com",
    "GIT_COMMITTER_NAME": "Test",
    "GIT_COMMITTER_EMAIL": "test@example.com",
}


class PublishTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self._env = os.environ.copy()
        os.environ.update(GIT_ENV)
        self.repo = self.tmp / "repo"
        self.plugin = fixture_mod.make_fixture(self.repo)
        self.remote = self.tmp / "remote.git"
        self.git("init", "-q", "-b", "main")
        self.git("init", "-q", "--bare", str(self.remote), cwd=self.tmp)
        self.git("remote", "add", "origin", str(self.remote))
        self.release("9.9.9")

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env)
        self._tmp.cleanup()

    def git(self, *args, cwd=None):
        return subprocess.run(
            ["git", *args], cwd=cwd or self.repo, check=True, capture_output=True, text=True
        ).stdout.strip()

    def remote_git(self, *args):
        return self.git(*args, cwd=self.remote)

    def set_version(self, version: str):
        path = self.plugin / ".cortex-plugin/plugin.json"
        manifest = json.loads(path.read_text())
        manifest["version"] = version
        path.write_text(json.dumps(manifest, indent=2) + "\n")

    def release(self, version: str):
        self.set_version(version)
        self.git("add", "-A")
        self.git("commit", "-q", "-m", f"release {version}")
        self.git("tag", f"v{version}")
        return self.git("rev-parse", "HEAD")

    def publish(self, tag, **kwargs):
        return publish_mod.publish(tag, repo=self.repo, remote="origin", **kwargs)

    def dist_head(self):
        return self.remote_git("rev-parse", "refs/heads/coco-desktop")

    def dist_tag(self, version):
        return self.remote_git("rev-parse", f"refs/tags/coco-desktop-v{version}^{{commit}}")

    def remote_file(self, ref, path):
        return self.remote_git("show", f"{ref}:{path}")

    def test_first_publish_creates_parentless_branch_and_tag(self):
        result = self.publish("v9.9.9")
        self.assertEqual(result["action"], "published")
        head = self.dist_head()
        self.assertEqual(self.dist_tag("9.9.9"), head)
        self.assertEqual(self.remote_git("rev-list", "--count", head), "1")
        manifest = json.loads(self.remote_file(head, ".cortex-plugin/plugin.json"))
        self.assertEqual(manifest["version"], "9.9.9")
        self.assertNotIn("commands", manifest)
        mode = self.remote_git("ls-tree", head, "skills/alpha/scripts/run.sh").split()[0]
        self.assertEqual(mode, "100755")
        self.assertIn("v9.9.9", self.remote_git("log", "-1", "--format=%B", head))

    def test_rerun_is_a_no_op(self):
        self.publish("v9.9.9")
        head = self.dist_head()
        result = self.publish("v9.9.9")
        self.assertEqual(result["action"], "unchanged")
        self.assertEqual(self.dist_head(), head)

    def test_branch_named_like_a_tag_is_rejected(self):
        self.git("tag", "-d", "v9.9.9")
        self.git("branch", "v9.9.9")
        with self.assertRaisesRegex(publish_mod.PublishError, "no tag v9.9.9"):
            self.publish("v9.9.9", dry_run=True)

    def test_tag_wins_over_a_branch_of_the_same_name(self):
        tagged = self.git("rev-parse", "HEAD")
        self.set_version("9.9.10")
        self.git("commit", "-qam", "unreleased")
        self.git("branch", "v9.9.9")
        result = self.publish("v9.9.9", expect_sha=tagged)
        self.assertEqual(result["action"], "published")
        manifest = json.loads(self.remote_file(self.dist_head(), ".cortex-plugin/plugin.json"))
        self.assertEqual(manifest["version"], "9.9.9")

    def test_rerun_fails_when_the_branch_is_missing(self):
        self.publish("v9.9.9")
        self.remote_git("update-ref", "-d", "refs/heads/coco-desktop")
        with self.assertRaisesRegex(publish_mod.PublishError, "coco-desktop branch is missing"):
            self.publish("v9.9.9")

    def test_second_release_fast_forwards_and_drops_removed_files(self):
        self.publish("v9.9.9")
        first = self.dist_head()
        (self.plugin / "settings.json").unlink()
        self.release("9.10.0")
        self.publish("v9.10.0")
        head = self.dist_head()
        self.assertEqual(self.remote_git("rev-parse", f"{head}^"), first)
        self.assertEqual(self.dist_tag("9.10.0"), head)
        self.assertEqual(self.dist_tag("9.9.9"), first)
        self.assertNotIn("settings.json", self.remote_git("ls-tree", "--name-only", head).split())

    def test_late_older_release_gets_a_pin_but_does_not_move_the_branch(self):
        self.git("checkout", "-q", "-b", "hotfix", "v9.9.9")
        self.release("9.9.10")
        self.git("checkout", "-q", "main")
        self.release("9.10.0")
        self.publish("v9.10.0")
        head = self.dist_head()
        result = self.publish("v9.9.10")
        self.assertEqual(result["action"], "pinned")
        self.assertEqual(self.dist_head(), head)
        pin = self.dist_tag("9.9.10")
        manifest = json.loads(self.remote_file(pin, ".cortex-plugin/plugin.json"))
        self.assertEqual(manifest["version"], "9.9.10")
        # A side commit with no parents, so the branch's history never shows the older build.
        self.assertEqual(self.remote_git("rev-list", "--count", pin), "1")

    def test_missing_branch_is_not_recreated_at_an_older_version(self):
        self.git("checkout", "-q", "-b", "hotfix", "v9.9.9")
        self.release("9.9.10")
        self.git("checkout", "-q", "main")
        self.release("9.10.0")
        self.publish("v9.10.0")
        self.remote_git("update-ref", "-d", "refs/heads/coco-desktop")
        with self.assertRaisesRegex(publish_mod.PublishError, "coco-desktop branch is missing"):
            self.publish("v9.9.10")
        self.assertNotIn("coco-desktop-v9.9.10", self.remote_git("tag"))

    def test_branch_holding_this_version_with_different_files_fails(self):
        self.publish("v9.9.9")
        self.remote_git("tag", "-d", "coco-desktop-v9.9.9")
        (self.plugin / "settings.json").write_text('{"changed": true}\n')
        self.git("commit", "-qam", "same version, different files")
        self.git("tag", "-f", "v9.9.9")
        with self.assertRaisesRegex(publish_mod.PublishError, "already holds 9.9.9 with different files"):
            self.publish("v9.9.9")

    def test_branch_holding_this_version_restores_a_missing_pin(self):
        self.publish("v9.9.9")
        head = self.dist_head()
        self.remote_git("tag", "-d", "coco-desktop-v9.9.9")
        result = self.publish("v9.9.9")
        self.assertEqual(result["action"], "pinned")
        self.assertEqual(self.dist_tag("9.9.9"), head)

    def test_release_off_the_required_branch_is_refused(self):
        self.git("checkout", "-q", "-b", "hotfix", "v9.9.9")
        self.release("9.9.10")
        with self.assertRaisesRegex(publish_mod.PublishError, "not on main"):
            self.publish("v9.9.10", require_ancestor="main", dry_run=True)
        self.git("checkout", "-q", "main")
        self.assertEqual(self.publish("v9.9.9", require_ancestor="main", dry_run=True)["action"], "published")

    def run_cli(self, *args):
        import contextlib
        import io
        out, err = io.StringIO(), io.StringIO()
        cwd = os.getcwd()
        os.chdir(self.repo)
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = publish_mod.main(list(args))
        finally:
            os.chdir(cwd)
        return code, out.getvalue(), err.getvalue()

    def test_cli_flags_the_workflow_uses(self):
        sha = self.git("rev-parse", "v9.9.9^{commit}")
        code, _, err = self.run_cli("v9.9.9", "--remote", "origin", "--expect-sha", "0" * 40, "--dry-run")
        self.assertEqual(code, 1)
        self.assertIn("expected", err)
        code, _, err = self.run_cli("v9.9.9", "--require-ancestor", "refs/heads/nope", "--dry-run")
        self.assertEqual(code, 1)
        code, out, _ = self.run_cli(
            "v9.9.9", "--remote", "origin", "--expect-sha", sha, "--require-ancestor", "main", "--dry-run"
        )
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["action"], "published")

    def test_conflicting_existing_tag_fails(self):
        self.publish("v9.9.9")
        self.git("push", "-q", "origin", "main")
        self.remote_git("tag", "-f", "coco-desktop-v9.9.9", self.git("rev-parse", "HEAD"))
        with self.assertRaisesRegex(publish_mod.PublishError, "different"):
            self.publish("v9.9.9")

    def test_rejected_push_leaves_no_refs(self):
        # Reject only the tag: without an atomic push the branch would still land.
        hook = self.remote / "hooks" / "update"
        hook.write_text('#!/bin/sh\ncase "$1" in refs/tags/*) exit 1 ;; esac\nexit 0\n')
        hook.chmod(0o755)
        with self.assertRaises(publish_mod.PublishError):
            self.publish("v9.9.9")
        refs = self.remote_git("for-each-ref", "--format=%(refname)")
        self.assertEqual(refs, "")

    def test_version_must_match_tag(self):
        self.git("tag", "v1.2.3")
        with self.assertRaisesRegex(publish_mod.PublishError, "9.9.9"):
            self.publish("v1.2.3")

    def test_expected_sha_must_match(self):
        with self.assertRaisesRegex(publish_mod.PublishError, "expected"):
            self.publish("v9.9.9", expect_sha="0" * 40)

    def test_dry_run_pushes_nothing(self):
        result = self.publish("v9.9.9", dry_run=True)
        self.assertEqual(result["action"], "published")
        self.assertEqual(self.remote_git("for-each-ref", "--format=%(refname)"), "")

    def test_bad_tag(self):
        with self.assertRaisesRegex(publish_mod.PublishError, "v<major>"):
            self.publish("release-1")


if __name__ == "__main__":
    unittest.main()
