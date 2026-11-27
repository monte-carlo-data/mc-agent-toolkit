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


class RepoFixture(unittest.TestCase):
    """A fixture repo with release v9.9.9 tagged locally, and an empty bare remote."""

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


class PublishTest(RepoFixture):
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

    def test_missing_branch_message_names_the_highest_version_pin(self):
        # The newest pin by date is 9.9.10, published after 9.10.0, but the branch belongs on 9.10.0.
        self.publish("v9.9.9")
        self.git("checkout", "-q", "-b", "hotfix", "v9.9.9")
        self.release("9.9.10")
        self.git("checkout", "-q", "main")
        self.release("9.10.0")
        self.publish("v9.10.0")
        self.publish("v9.9.10")
        self.remote_git("update-ref", "-d", "refs/heads/coco-desktop")
        with self.assertRaises(publish_mod.PublishError) as caught:
            self.publish("v9.10.0")
        message = str(caught.exception)
        self.assertIn("coco-desktop-v9.10.0", message)
        self.assertNotIn("coco-desktop-v9.9.10", message)

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

    def test_unreadable_manifest_is_a_publish_error(self):
        (self.plugin / ".cortex-plugin/plugin.json").write_text("{not json")
        self.git("commit", "-qam", "broken")
        self.git("tag", "-f", "v9.9.9")
        with self.assertRaisesRegex(publish_mod.PublishError, "unreadable"):
            self.publish("v9.9.9")

    def test_missing_build_input_is_a_publish_error(self):
        (self.repo / "LICENSE").unlink()
        self.git("commit", "-qam", "no license")
        self.git("tag", "-f", "v9.9.9")
        with self.assertRaisesRegex(publish_mod.PublishError, "git archive of v9.9.9 failed"):
            self.publish("v9.9.9")

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

LEGACY_KEYS = {"action", "tag", "commit", "branch_head_version", "refspecs", "dry_run"}

RULESET_HOOK = """#!/bin/sh
# The SEC-4320 rulesets: pins are never updated or deleted; the branch is never deleted or force-pushed.
ref="$1"; old="$2"; new="$3"; zero=0000000000000000000000000000000000000000
case "$ref" in
  refs/tags/coco-desktop-v*) [ "$old" = "$zero" ] || { echo "pin $ref is immutable" >&2; exit 1; } ;;
  refs/heads/coco-desktop)
    [ "$new" = "$zero" ] && { echo "branch deletion" >&2; exit 1; }
    if [ "$old" != "$zero" ] && ! git merge-base --is-ancestor "$old" "$new"; then
      echo "force push" >&2; exit 1
    fi ;;
esac
exit 0
"""


class BackfillTest(RepoFixture):
    """Each publish run also pins every release on main that is newer than the oldest pin and has none."""

    def ship(self, version: str, **kwargs):
        """Release on main (setUp already released 9.9.9) and push main and its tag, as the release job does."""
        exists = self.git("tag", "-l", f"v{version}")
        sha = self.git("rev-parse", f"v{version}^{{commit}}") if exists else self.release(version, **kwargs)
        self.git("push", "-q", "origin", "main", f"refs/tags/v{version}")
        return sha

    def backfill(self, tag, **kwargs):
        kwargs.setdefault("require_ancestor", "main")
        return publish_mod.publish_all(tag, repo=self.repo, remote="origin", **kwargs)

    def remote_refs(self):
        return self.remote_git("for-each-ref", "--format=%(refname) %(objectname)")

    def pins(self):
        return sorted(r.removeprefix("coco-desktop-v") for r in self.remote_git("tag", "-l", "coco-desktop-v*").split())

    def processed(self, result):
        return [r["source"] for r in result["results"]] + [f["source"] for f in result["failed"]]

    def chain(self):
        """Versions on the branch's history, head first."""
        commits = self.remote_git("rev-list", "refs/heads/coco-desktop").split()
        return [json.loads(self.remote_file(c, ".cortex-plugin/plugin.json"))["version"] for c in commits]

    def hook(self, script: str):
        path = self.remote / "hooks" / "update"
        path.write_text(script)
        path.chmod(0o755)
        return path

    def test_one_gap_is_pinned_on_the_branch_before_the_own_release(self):
        self.ship("9.9.9")
        self.publish("v9.9.9")
        self.ship("9.9.10")  # its publish was cancelled
        self.ship("9.9.11")
        result = self.backfill("v9.9.11")
        self.assertEqual(result["failed"], [])
        self.assertEqual(self.processed(result), ["v9.9.10", "v9.9.11"])
        self.assertEqual(self.chain(), ["9.9.11", "9.9.10", "9.9.9"])
        self.assertEqual(self.dist_tag("9.9.10"), self.remote_git("rev-parse", "refs/heads/coco-desktop^"))
        self.assertEqual(self.dist_tag("9.9.11"), self.dist_head())

    def test_several_gaps_go_oldest_first_by_number_not_by_string(self):
        self.ship("9.9.9")
        self.publish("v9.9.9")
        self.ship("9.9.10")
        self.ship("9.10.0")  # sorts before 9.9.10 as a string
        self.ship("9.10.1")
        result = self.backfill("v9.10.1")
        self.assertEqual(self.processed(result), ["v9.9.10", "v9.10.0", "v9.10.1"])
        self.assertEqual(self.chain(), ["9.10.1", "9.10.0", "9.9.10", "9.9.9"])

    def test_a_release_newer_than_the_own_one_is_pinned_too(self):
        # 9.9.11's publish was replaced by 9.9.10's, whose release job finished later.
        self.ship("9.9.9")
        self.publish("v9.9.9")
        self.ship("9.9.10")
        self.ship("9.9.11")
        result = self.backfill("v9.9.10")
        self.assertEqual(self.processed(result), ["v9.9.10", "v9.9.11"])
        self.assertEqual(self.chain(), ["9.9.11", "9.9.10", "9.9.9"])

    def test_a_gap_below_the_branch_head_gets_a_side_pin(self):
        self.ship("9.9.9")
        self.publish("v9.9.9")
        self.ship("9.9.10")  # its publish failed
        self.ship("9.10.0")
        self.publish("v9.10.0")
        old_head = self.dist_head()
        self.ship("9.10.1")
        result = self.backfill("v9.10.1")
        self.assertEqual(self.processed(result), ["v9.9.10", "v9.10.1"])
        self.assertEqual(result["results"][0]["action"], "pinned")
        self.assertEqual(self.remote_git("rev-list", "--count", self.dist_tag("9.9.10")), "1")
        self.assertEqual(self.remote_git("rev-parse", "refs/heads/coco-desktop^"), old_head)
        self.assertEqual(self.chain()[0], "9.10.1")

    def test_releases_older_than_the_oldest_pin_are_left_alone(self):
        self.ship("9.9.9")
        self.ship("9.9.20")  # newer than the first pin as a string, older as a version
        self.ship("9.10.0")
        self.publish("v9.10.0")
        self.ship("9.10.1")
        result = self.backfill("v9.10.1")
        self.assertEqual(self.processed(result), ["v9.10.1"])
        self.assertEqual(self.pins(), ["9.10.0", "9.10.1"])

    def test_only_release_tags_on_the_remote_and_on_main_count(self):
        self.ship("9.9.9")
        self.publish("v9.9.9")
        self.git("checkout", "-q", "-b", "hotfix")
        self.release("9.9.10")
        self.git("push", "-q", "origin", "refs/tags/v9.9.10")  # tag pushed, commit not on main
        self.git("checkout", "-q", "main")
        self.release("9.9.11")  # tagged locally, never pushed
        self.set_version("9.9.12")
        self.git("commit", "-qam", "branch named like a tag")
        self.git("push", "-q", "origin", "main", "HEAD:refs/heads/v9.9.12")
        self.set_version("9.9.13")
        self.git("commit", "-qam", "tag without the v")
        self.git("tag", "9.9.13")
        self.git("tag", "v9.9.13-rc1")
        self.git("push", "-q", "origin", "main", "refs/tags/9.9.13", "refs/tags/v9.9.13-rc1")
        self.ship("9.9.14")
        result = self.backfill("v9.9.14")
        self.assertEqual(self.processed(result), ["v9.9.14"])
        self.assertEqual(self.pins(), ["9.9.14", "9.9.9"])

    def test_no_pins_publishes_only_the_own_release(self):
        self.ship("9.9.9")
        self.ship("9.9.10")
        result = self.backfill("v9.9.10")
        self.assertEqual(self.processed(result), ["v9.9.10"])
        self.assertEqual(self.pins(), ["9.9.10"])

    def test_without_backfill_the_cli_publishes_only_its_tag_and_keeps_its_output(self):
        self.ship("9.9.9")
        self.publish("v9.9.9")
        self.ship("9.9.10")
        self.ship("9.9.11")
        code, out, _ = self.run_cli("v9.9.11", "--require-ancestor", "main")
        self.assertEqual(code, 0)
        self.assertEqual(set(json.loads(out)), LEGACY_KEYS)
        self.assertEqual(self.pins(), ["9.9.11", "9.9.9"])

    def test_failing_gaps_are_reported_and_the_own_release_still_publishes(self):
        self.ship("9.9.9")
        self.publish("v9.9.9")
        manifest = self.plugin / ".cortex-plugin/plugin.json"
        good_manifest = manifest.read_text()
        hooks = self.plugin / "hooks/hooks.json"
        command = self.plugin / "commands/y/nofront.md"
        good_command = command.read_text()

        hooks.write_text("{not json")
        self.ship("9.9.10")
        hooks.write_text('{"hooks": {}}\n')
        (self.repo / "LICENSE").unlink()  # git archive fails
        self.ship("9.9.11")
        (self.repo / "LICENSE").write_text("Apache License\n")
        self.release("9.9.12")
        manifest.write_text("[]\n")  # a manifest that isn't an object
        self.git("commit", "-qam", "bad manifest")
        self.git("tag", "-f", "v9.9.12")
        self.git("push", "-q", "origin", "main", "refs/tags/v9.9.12")
        manifest.write_text(good_manifest)
        self.set_version("9.9.13")
        data = json.loads(manifest.read_text())
        data["commands"] = 17  # wrong shape: the builder raises TypeError
        manifest.write_text(json.dumps(data) + "\n")
        self.git("commit", "-qam", "commands is a number")
        self.git("tag", "v9.9.13")
        self.git("push", "-q", "origin", "main", "refs/tags/v9.9.13")
        manifest.write_text(good_manifest)
        command.write_text("---\ndescription: Empty.\n---\n")  # the builder's BuildError
        self.ship("9.9.14")
        command.write_text(good_command)
        self.ship("9.9.15")

        summary = self.tmp / "step summary.md"
        code, out, err = self.run_cli(
            "v9.9.15", "--backfill", "--require-ancestor", "main", "--summary", str(summary)
        )
        self.assertEqual(code, 1)
        result = json.loads(out)
        self.assertEqual([f["source"] for f in result["failed"]],
                         ["v9.9.10", "v9.9.11", "v9.9.12", "v9.9.13", "v9.9.14"])
        self.assertEqual([r["source"] for r in result["results"]], ["v9.9.15"])
        self.assertEqual(self.pins(), ["9.9.15", "9.9.9"])
        self.assertEqual(self.remote_git("rev-parse", "refs/heads/coco-desktop^"), self.dist_tag("9.9.9"))
        self.assertEqual(err.count("::warning"), 5)
        text = summary.read_text()
        for version in ("9.9.10", "9.9.11", "9.9.12", "9.9.13", "9.9.14", "9.9.15"):
            self.assertIn(f"v{version}", text)
        self.assertIn("empty body", text)

    def test_an_invalid_own_release_writes_nothing(self):
        self.ship("9.9.9")
        self.publish("v9.9.9")
        self.ship("9.9.10")  # a gap that would be pinned
        self.git("checkout", "-q", "-b", "hotfix")
        self.release("9.9.11")
        self.git("push", "-q", "origin", "refs/tags/v9.9.11")
        self.git("checkout", "-q", "main")
        self.release("9.9.12")  # local only
        self.git("tag", "-a", "-m", "annotated", "v9.9.13", "v9.9.12")
        self.git("push", "-q", "origin", "refs/tags/v9.9.13")
        self.git("tag", "-f", "v9.9.13", "v9.9.12")  # local tag now differs from the remote's
        before = self.remote_refs()
        cases = [
            ("v9.9", {}, "v<major>"),
            ("v9.9.10", {"expect_sha": "0" * 40}, "expected"),
            ("v9.9.11", {}, "not on main"),
            ("v9.9.12", {}, "not on origin"),
            ("v9.9.13", {}, "differs"),
        ]
        for tag, kwargs, message in cases:
            with self.subTest(tag=tag), self.assertRaisesRegex(publish_mod.PublishError, message):
                self.backfill(tag, **kwargs)
            self.assertEqual(self.remote_refs(), before)

    def test_an_annotated_own_release_is_published(self):
        self.ship("9.9.9")
        self.publish("v9.9.9")
        self.release("9.9.10")
        self.git("tag", "-f", "-a", "-m", "annotated", "v9.9.10")
        self.git("push", "-q", "origin", "main", "refs/tags/v9.9.10")
        result = self.backfill("v9.9.10", expect_sha=self.git("rev-parse", "HEAD"))
        self.assertEqual(self.processed(result), ["v9.9.10"])

    def test_cli_preflight_failure_writes_the_summary(self):
        summary = self.tmp / "summary.md"
        code, _, err = self.run_cli("v9.9.9", "--backfill", "--require-ancestor", "main", "--summary", str(summary))
        self.assertEqual(code, 1)
        self.assertIn("not on origin", err)
        self.assertIn("not on origin", summary.read_text())
        self.assertEqual(self.remote_refs(), "")

    def test_backfill_needs_an_ancestor_ref(self):
        with self.assertRaises(SystemExit):
            self.run_cli("v9.9.9", "--backfill")
        self.ship("9.9.9")
        code, _, err = self.run_cli("v9.9.9", "--backfill", "--require-ancestor", "refs/heads/nope")
        self.assertEqual(code, 1)
        self.assertIn("nope", err)
        self.assertEqual(self.remote_refs().split("\n"), [
            f"refs/heads/main {self.git('rev-parse', 'main')}",
            f"refs/tags/v9.9.9 {self.git('rev-parse', 'v9.9.9')}",
        ])

    def test_a_rejected_gap_does_not_stop_the_run_and_a_rerun_pins_it(self):
        self.ship("9.9.9")
        self.publish("v9.9.9")
        self.ship("9.9.10")
        self.ship("9.9.11")
        self.ship("9.9.12")
        hook = self.hook('#!/bin/sh\n[ "$1" = refs/tags/coco-desktop-v9.9.11 ] && exit 1\nexit 0\n')
        result = self.backfill("v9.9.12")
        self.assertEqual([f["source"] for f in result["failed"]], ["v9.9.11"])
        self.assertEqual(self.pins(), ["9.9.10", "9.9.12", "9.9.9"])
        self.assertEqual(self.chain(), ["9.9.12", "9.9.10", "9.9.9"])
        hook.unlink()
        before = self.remote_refs()
        result = self.backfill("v9.9.12")
        self.assertEqual(result["failed"], [])
        self.assertEqual([(r["source"], r["action"]) for r in result["results"]],
                         [("v9.9.11", "pinned"), ("v9.9.12", "unchanged")])
        after = self.remote_refs().splitlines()
        self.assertEqual(sorted(set(after) - set(before.splitlines())),
                         [f"refs/tags/coco-desktop-v9.9.11 {self.dist_tag('9.9.11')}"])
        self.assertEqual(set(before.splitlines()) - set(after), set())

    def test_backfill_works_under_the_rulesets(self):
        self.ship("9.9.9")
        self.publish("v9.9.9")
        self.ship("9.9.10")  # below the head after 9.10.0
        self.ship("9.10.0")
        self.publish("v9.10.0")
        self.ship("9.10.1")
        self.ship("9.10.2")
        self.hook(RULESET_HOOK)
        result = self.backfill("v9.10.2")
        self.assertEqual(result["failed"], [])
        self.assertEqual(self.processed(result), ["v9.9.10", "v9.10.1", "v9.10.2"])
        again = self.backfill("v9.10.2")
        self.assertEqual(again["failed"], [])
        # The hook really enforces the rules.
        with self.assertRaises(subprocess.CalledProcessError):
            self.git("push", "-q", "origin", f"{self.dist_tag('9.9.9')}:refs/tags/coco-desktop-v9.10.2", "-f")
        with self.assertRaises(subprocess.CalledProcessError):
            self.git("push", "-q", "origin", ":refs/heads/coco-desktop")

    def test_dry_run_plans_the_gaps_and_pushes_nothing(self):
        self.ship("9.9.9")
        self.publish("v9.9.9")
        self.ship("9.9.10")
        self.ship("9.9.11")
        before = self.remote_refs()
        result = self.backfill("v9.9.11", dry_run=True)
        self.assertEqual(self.processed(result), ["v9.9.10", "v9.9.11"])
        self.assertEqual(self.remote_refs(), before)

    def test_a_gap_is_taken_from_the_remote_not_the_local_tag(self):
        self.ship("9.9.9")
        self.publish("v9.9.9")
        self.ship("9.9.10")
        self.git("tag", "-d", "v9.9.10")  # missing here: fetched from the remote
        self.ship("9.9.11")
        self.git("tag", "-f", "v9.9.11", "v9.9.9")  # differs here: not published
        self.ship("9.9.12")
        result = self.backfill("v9.9.12")
        self.assertEqual([r["source"] for r in result["results"]], ["v9.9.10", "v9.9.12"])
        self.assertEqual([f["source"] for f in result["failed"]], ["v9.9.11"])
        self.assertIn("differs", result["failed"][0]["error"])
        self.assertEqual(self.pins(), ["9.9.10", "9.9.12", "9.9.9"])

    def test_a_git_error_is_not_read_as_off_main(self):
        with self.assertRaisesRegex(publish_mod.PublishError, "merge-base"):
            publish_mod.is_ancestor(self.repo, "0" * 40, "main")

    def test_annotations_escape_newlines_and_percent(self):
        self.assertEqual(publish_mod.annotation("warning", "50% done\r\nnext"), "::warning::50%25 done%0D%0Anext")


if __name__ == "__main__":
    unittest.main()
