#!/usr/bin/env python3
"""Publish the CoCo Desktop build of a release tag to the `coco-desktop` branch.

For source tag v<X.Y.Z>, builds plugins/cortex-code at that tag with
scripts/build_coco_desktop.py (from this checkout, so a builder fix applies to any tag)
and publishes it as:

- branch `coco-desktop`: what "Add from GitHub" and Sync install. It has its own
  history, one commit per release, and only moves forward in version;
- tag `coco-desktop-v<X.Y.Z>`: an immutable pin of that version.

Re-running is safe. If the pin tag already holds the same files, nothing happens; if it
holds different files, the run fails rather than retagging. A release older than the
branch head gets its pin tag on a side commit and leaves the branch alone. Branch and
tag are pushed atomically.

Usage: publish_coco_desktop.py <source tag> [--remote origin] [--expect-sha SHA] [--dry-run]
"""

import argparse
import importlib.util
import json
import os
import re
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

BRANCH = "coco-desktop"
TAG_PREFIX = "coco-desktop-v"
PLUGIN = "plugins/cortex-code"
BUILD_INPUTS = [PLUGIN, "skills", "LICENSE"]
SOURCE_TAG = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")


class PublishError(Exception):
    pass


def _load_builder():
    spec = importlib.util.spec_from_file_location(
        "build_coco_desktop", Path(__file__).resolve().parent / "build_coco_desktop.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git(repo: Path, *args: str, env: dict | None = None, check: bool = True) -> str:
    result = subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, env={**os.environ, **(env or {})}
    )
    if check and result.returncode != 0:
        raise PublishError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def version_tuple(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))


def remote_ref(repo: Path, remote: str, ref: str) -> str | None:
    """Fetch a remote ref's object into the local repo and return its commit, or None."""
    listing = git(repo, "ls-remote", remote, ref)
    if not listing:
        return None
    git(repo, "fetch", "-q", "--no-tags", remote, ref)
    return git(repo, "rev-parse", "FETCH_HEAD^{commit}")


def build_tree(repo: Path, tag: str, work: Path) -> str:
    """Build the tag's plugin and return the git tree id of the output."""
    archive = work / "source.tar"
    with archive.open("wb") as fh:
        subprocess.run(["git", "archive", "--format=tar", tag, *BUILD_INPUTS], cwd=repo, stdout=fh, check=True)
    source = work / "source"
    with tarfile.open(archive) as tar:
        tar.extractall(source, filter="tar") if hasattr(tarfile, "data_filter") else tar.extractall(source)
    out = work / "out"
    builder = _load_builder()
    try:
        builder.build(source / PLUGIN, out, ref=tag)
    except builder.BuildError as exc:
        raise PublishError(f"build of {tag} failed: {exc}") from exc
    env = {"GIT_INDEX_FILE": str(work / "index")}
    git(repo, f"--work-tree={out}", "add", "-A", "-f", ".", env=env)
    return git(repo, "write-tree", env=env)


def publish(tag: str, repo: Path = Path("."), remote: str = "origin", expect_sha: str | None = None,
            dry_run: bool = False) -> dict:
    match = SOURCE_TAG.match(tag)
    if not match:
        raise PublishError(f"source tag {tag!r} is not v<major>.<minor>.<patch>")
    version = tag[1:]
    repo = Path(repo).resolve()

    source_sha = git(repo, "rev-parse", f"{tag}^{{commit}}")
    if expect_sha and source_sha != expect_sha:
        raise PublishError(f"{tag} is {source_sha}, expected {expect_sha}")
    manifest = json.loads(git(repo, "show", f"{tag}:{PLUGIN}/.cortex-plugin/plugin.json"))
    if manifest.get("version") != version:
        raise PublishError(f"{tag} has plugin version {manifest.get('version')}, not {version}")

    pin = f"{TAG_PREFIX}{version}"
    with tempfile.TemporaryDirectory() as tmp:
        tree = build_tree(repo, tag, Path(tmp))

    existing_pin = remote_ref(repo, remote, f"refs/tags/{pin}")
    if existing_pin:
        if git(repo, "rev-parse", f"{existing_pin}^{{tree}}") == tree:
            return {"action": "unchanged", "tag": pin, "commit": existing_pin}
        raise PublishError(f"{pin} already exists with different files; bump the version instead of retagging")

    head = remote_ref(repo, remote, f"refs/heads/{BRANCH}")
    head_version = None
    if head:
        head_manifest = json.loads(git(repo, "show", f"{head}:.cortex-plugin/plugin.json"))
        head_version = head_manifest.get("version")

    message = (
        f"CoCo Desktop build of {tag}\n\n"
        f"Built by scripts/build_coco_desktop.py from {PLUGIN} at {source_sha}.\n"
    )
    advance = head is None or version_tuple(version) > version_tuple(head_version)
    if not advance and version == head_version:
        if git(repo, "rev-parse", f"{head}^{{tree}}") != tree:
            raise PublishError(f"{BRANCH} already holds {version} with different files; bump the version")
        commit, refspecs, action = head, [f"{head}:refs/tags/{pin}"], "pinned"
    else:
        parents = ["-p", head] if advance and head else []
        commit = git(repo, "commit-tree", tree, *parents, "-m", message)
        if advance:
            refspecs = [f"{commit}:refs/heads/{BRANCH}", f"{commit}:refs/tags/{pin}"]
            action = "published"
        else:
            refspecs, action = [f"{commit}:refs/tags/{pin}"], "pinned"

    if not dry_run:
        git(repo, "push", "--atomic", remote, *refspecs)
    return {"action": action, "tag": pin, "commit": commit, "branch_head_version": head_version,
            "refspecs": refspecs, "dry_run": dry_run}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("tag", help="source release tag, e.g. v1.31.0")
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--expect-sha", help="fail unless the tag points at this commit")
    parser.add_argument("--dry-run", action="store_true", help="build and plan, push nothing")
    args = parser.parse_args(argv)
    try:
        result = publish(args.tag, remote=args.remote, expect_sha=args.expect_sha, dry_run=args.dry_run)
    except PublishError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
