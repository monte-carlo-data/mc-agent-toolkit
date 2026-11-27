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

With --backfill, the run first checks its own tag, then also publishes every release tag on the
remote that is on --require-ancestor, newer than the oldest pin, and not pinned yet: GitHub cancels
a waiting publish when a newer one queues, so a release can be left without a pin. It goes oldest
first, one atomic push per version, and keeps going past a version that fails; the exit status is
1 if any did.

Usage: publish_coco_desktop.py <source tag> [--remote origin] [--expect-sha SHA] [--require-ancestor REF]
                               [--backfill] [--summary PATH] [--dry-run]
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
RELEASE_REF = re.compile(r"refs/tags/(v\d+\.\d+\.\d+)")
PIN_REF = re.compile(rf"refs/tags/{TAG_PREFIX}(\d+\.\d+\.\d+)")


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
        ["git", *args], cwd=repo, capture_output=True, text=True, env={**os.environ, **(env or {})}, check=False
    )
    if check and result.returncode != 0:
        raise PublishError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def version_tuple(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))


def is_ancestor(repo: Path, commit: str, ref: str) -> bool:
    """Whether commit is on ref. A git error is not a "no": it fails rather than skip a release."""
    result = subprocess.run(["git", "merge-base", "--is-ancestor", commit, ref], cwd=repo, capture_output=True, text=True,
                            check=False)
    if result.returncode not in (0, 1):
        raise PublishError(f"git merge-base --is-ancestor {commit} {ref} failed: {result.stderr.strip()}")
    return result.returncode == 0


def remote_tag_listing(repo: Path, remote: str) -> tuple[dict[str, str], set[tuple[int, ...]]]:
    """The remote's release tags (name -> tag object id) and pinned versions. --refs leaves out the
    peeled ^{} lines, so an annotated tag maps to its tag object, as `rev-parse refs/tags/<tag>` does."""
    releases, pinned = {}, set()
    # Split on git's own separators only: other tags' names can hold Unicode whitespace or line breaks.
    for line in git(repo, "ls-remote", "--refs", "--tags", remote).split("\n"):
        if not line:
            continue
        oid, ref = line.split("\t", 1)
        if match := RELEASE_REF.fullmatch(ref):
            releases[match.group(1)] = oid
        elif match := PIN_REF.fullmatch(ref):
            pinned.add(version_tuple(match.group(1)))
    return releases, pinned


def remote_ref(repo: Path, remote: str, ref: str) -> str | None:
    """Fetch a remote ref's object into the local repo and return its commit, or None."""
    listing = git(repo, "ls-remote", remote, ref)
    if not listing:
        return None
    git(repo, "fetch", "-q", "--no-tags", remote, ref)
    return git(repo, "rev-parse", "FETCH_HEAD^{commit}")


def highest_pin(listing: str) -> str | None:
    """The highest-version pin tag in an ls-remote listing, or None. Creation order doesn't count:
    an older release published late gets its pin after newer ones."""
    pins = {}
    for line in listing.splitlines():
        ref = line.split()[-1].removesuffix("^{}")
        name = ref.removeprefix("refs/tags/")
        version = name.removeprefix(TAG_PREFIX)
        if re.fullmatch(r"\d+\.\d+\.\d+", version):
            pins[version_tuple(version)] = name
    return pins[max(pins)] if pins else None


def build_tree(repo: Path, tag: str, commit: str, work: Path) -> str:
    """Build the plugin at the tag's commit and return the git tree id of the output."""
    archive = work / "source.tar"
    with archive.open("wb") as fh:
        result = subprocess.run(["git", "archive", "--format=tar", commit, *BUILD_INPUTS], cwd=repo, stdout=fh,
                                stderr=subprocess.PIPE, text=True, check=False)
    if result.returncode:
        raise PublishError(f"git archive of {tag} failed: {result.stderr.strip()}")
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


def check_source(tag: str, repo: Path, remote: str, expect_sha: str | None = None,
                 require_ancestor: str | None = None, remote_oid: str | None = None,
                 check_remote: bool = False, check_manifest: bool = True) -> str:
    """Check that tag is a release this run may publish and return its commit. With check_remote,
    the local tag must be the remote's (remote_oid, None if the remote has no such tag). Without
    check_manifest, the plugin version is left for publish() to check."""
    if not SOURCE_TAG.match(tag):
        raise PublishError(f"source tag {tag!r} is not v<major>.<minor>.<patch>")
    version = tag[1:]

    # Only a tag counts: a branch named like one must never be published as a release.
    local_oid = git(repo, "rev-parse", "-q", "--verify", f"refs/tags/{tag}", check=False)
    if not local_oid:
        raise PublishError(f"no tag {tag} in {repo}")
    if check_remote:
        # A pin never moves, so it must come from the release everyone sees, not a stale or private tag.
        if remote_oid is None:
            raise PublishError(f"{tag} is not on {remote}")
        if local_oid != remote_oid:
            raise PublishError(f"{tag} here is {local_oid} but {remote} has {remote_oid}; the local tag differs")
    source_sha = git(repo, "rev-parse", f"{local_oid}^{{commit}}")
    if expect_sha and source_sha != expect_sha:
        raise PublishError(f"{tag} is {source_sha}, expected {expect_sha}")
    if require_ancestor:
        if not git(repo, "rev-parse", "-q", "--verify", f"{require_ancestor}^{{commit}}", check=False):
            raise PublishError(f"no {require_ancestor} in {repo}")
        if not is_ancestor(repo, source_sha, require_ancestor):
            raise PublishError(f"{tag} is not on {require_ancestor}")
    if not check_manifest:
        return source_sha
    try:
        manifest = json.loads(git(repo, "show", f"{source_sha}:{PLUGIN}/.cortex-plugin/plugin.json"))
    except json.JSONDecodeError as exc:
        raise PublishError(f"{tag} has an unreadable {PLUGIN}/.cortex-plugin/plugin.json: {exc}") from exc
    found = manifest.get("version") if isinstance(manifest, dict) else None
    if found != version:
        raise PublishError(f"{tag} has plugin version {found}, not {version}")
    return source_sha


def publish(tag: str, repo: Path = Path("."), remote: str = "origin", expect_sha: str | None = None,
            require_ancestor: str | None = None, dry_run: bool = False, remote_oid: str | None = None) -> dict:
    """Publish one release tag. remote_oid, when given, is the remote's object for the tag, which the
    local tag must match."""
    repo = Path(repo).resolve()
    source_sha = check_source(tag, repo, remote, expect_sha, require_ancestor, remote_oid,
                              check_remote=remote_oid is not None)
    version = tag[1:]

    pin = f"{TAG_PREFIX}{version}"
    with tempfile.TemporaryDirectory() as tmp:
        tree = build_tree(repo, tag, source_sha, Path(tmp))

    head = remote_ref(repo, remote, f"refs/heads/{BRANCH}")
    if head is None:
        pins = highest_pin(git(repo, "ls-remote", "--tags", remote, f"refs/tags/{TAG_PREFIX}*"))
        if pins:
            # Published before, so the branch was deleted. Recreating it from this release could
            # move it back to an older version than a pin that already exists.
            raise PublishError(
                f"the {BRANCH} branch is missing but {TAG_PREFIX}* tags exist; push the commit of "
                f"{pins}, the highest version, to refs/heads/{BRANCH} by hand, then re-run"
            )
    existing_pin = remote_ref(repo, remote, f"refs/tags/{pin}")
    if existing_pin:
        if git(repo, "rev-parse", f"{existing_pin}^{{tree}}") != tree:
            raise PublishError(f"{pin} already exists with different files; bump the version instead of retagging")
        return {"action": "unchanged", "tag": pin, "commit": existing_pin}

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


def _failure(name: str, own: bool, exc: Exception) -> dict:
    error = str(exc) if isinstance(exc, PublishError) else f"{type(exc).__name__}: {exc}"
    return {"source": name, "tag": f"{TAG_PREFIX}{name[1:]}", "own": own, "error": error}


def _prepare_candidate(repo: Path, remote: str, name: str, oid: str, boundary: str) -> bool:
    """Fetch a release the remote lists and say whether it is on boundary. Raises PublishError if the
    remote's tag changed since it was listed: the build would otherwise use the listed object."""
    git(repo, "fetch", "-q", "--no-tags", remote, f"refs/tags/{name}")
    fetched = git(repo, "rev-parse", "FETCH_HEAD")
    if fetched != oid:
        raise PublishError(f"{name} moved on {remote} during this run (listed {oid}, now {fetched}); "
                           "the next run publishes it")
    if not is_ancestor(repo, git(repo, "rev-parse", f"{oid}^{{commit}}"), boundary):
        return False
    if not git(repo, "rev-parse", "-q", "--verify", f"refs/tags/{name}", check=False):
        git(repo, "update-ref", f"refs/tags/{name}", oid, "")
    return True


def publish_all(tag: str, repo: Path = Path("."), remote: str = "origin", expect_sha: str | None = None,
                require_ancestor: str | None = None, dry_run: bool = False) -> dict:
    """Publish tag and every release the remote is missing a pin for, oldest first.

    A release qualifies if its v<X.Y.Z> tag is on the remote, its commit is on require_ancestor,
    its version is newer than the oldest pin and it has no pin. With no pins yet, only tag is
    published. If tag itself isn't a valid release on the remote and on require_ancestor, or the
    remote's tags can't be listed, this raises PublishError before anything is pushed. After that,
    a release that fails, the run's own included, is recorded under "failed" and the rest still run.
    """
    if not require_ancestor:
        raise PublishError("backfill needs require_ancestor, the branch releases must be on")
    repo = Path(repo).resolve()
    releases, pinned = remote_tag_listing(repo, remote)
    check_source(tag, repo, remote, expect_sha, require_ancestor, releases.get(tag), check_remote=True,
                 check_manifest=False)
    boundary = git(repo, "rev-parse", f"{require_ancestor}^{{commit}}")

    sources, failed = [tag], []
    floor = min(pinned, default=None)
    for name, oid in releases.items():
        version = version_tuple(name[1:])
        if floor is None or version <= floor or version in pinned or name == tag:
            continue
        # One old release must not stop the others, or the release this run is for.
        try:
            if _prepare_candidate(repo, remote, name, oid, boundary):
                sources.append(name)
        except Exception as exc:  # noqa: BLE001
            failed.append(_failure(name, False, exc))
    sources.sort(key=lambda name: version_tuple(name[1:]))

    results = []
    for name in sources:
        own = name == tag
        try:
            result = publish(name, repo, remote, expect_sha=expect_sha if own else None,
                             require_ancestor=require_ancestor if own else boundary, dry_run=dry_run,
                             remote_oid=releases[name])
        except Exception as exc:  # noqa: BLE001
            failed.append(_failure(name, own, exc))
            continue
        results.append({"source": name, **result})
    return {"results": results, "failed": failed}


def annotation(level: str, message: str) -> str:
    """A GitHub Actions workflow command; the message is escaped so a multi-line error stays one."""
    escaped = message.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    return f"::{level}::{escaped}"


def _fenced(text: str) -> list[str]:
    longest = max((len(run) for run in re.findall(r"`+", text)), default=0)
    fence = "`" * max(3, longest + 1)
    return [fence, text, fence, ""]


def summary_markdown(tag: str, report: dict | None, error: str | None = None) -> str:
    lines = [f"### CoCo Desktop publish of {tag}", ""]
    if error is not None:
        return "\n".join(lines + ["Nothing was published:", "", *_fenced(error)])
    rows = [(r["source"], r["tag"], r["action"] + (" (dry run)" if r.get("dry_run") else ""), r["commit"][:12])
            for r in report["results"]]
    rows += [(f["source"], f["tag"], "failed", "") for f in report["failed"]]
    rows.sort(key=lambda row: version_tuple(row[0][1:]))
    lines += ["| Release | Pin | Result | Commit |", "| --- | --- | --- | --- |"]
    lines += [f"| {source} | {pin} | {action} | {commit} |" for source, pin, action, commit in rows]
    lines.append("")
    for f in report["failed"]:
        lines += [f"**{f['source']}** failed:", "", *_fenced(f["error"])]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("tag", help="source release tag, e.g. v1.32.0")
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--expect-sha", help="fail unless the tag points at this commit")
    parser.add_argument("--require-ancestor", metavar="REF", help="fail unless the tag's commit is on REF")
    parser.add_argument("--backfill", action="store_true",
                        help="also publish releases on --require-ancestor that have no pin yet")
    parser.add_argument("--summary", metavar="PATH", help="append a Markdown report to PATH, e.g. $GITHUB_STEP_SUMMARY")
    parser.add_argument("--dry-run", action="store_true",
                        help="build and plan, push nothing. With --backfill each version is planned against the "
                             "remote as it is now, so later versions' parents and commits are previews only")
    args = parser.parse_args(argv)
    if args.backfill and not args.require_ancestor:
        parser.error("--backfill needs --require-ancestor")

    def write_summary(text: str) -> None:
        if args.summary:
            with open(args.summary, "a", encoding="utf-8") as fh:
                fh.write(text + "\n")

    try:
        if args.backfill:
            report = publish_all(args.tag, remote=args.remote, expect_sha=args.expect_sha,
                                 require_ancestor=args.require_ancestor, dry_run=args.dry_run)
        else:
            result = publish(args.tag, remote=args.remote, expect_sha=args.expect_sha,
                             require_ancestor=args.require_ancestor, dry_run=args.dry_run)
            report = {"results": [{"source": args.tag, **result}], "failed": []}
    except PublishError as exc:
        print(f"error: {exc}", file=sys.stderr)
        if args.backfill:
            print(annotation("error", str(exc)), file=sys.stderr)
        write_summary(summary_markdown(args.tag, None, str(exc)))
        return 1
    write_summary(summary_markdown(args.tag, report))
    if not args.backfill:
        print(json.dumps(result, indent=2))
        return 0
    for f in report["failed"]:
        print(f"error: {f['source']}: {f['error']}", file=sys.stderr)
        print(annotation("error" if f["own"] else "warning", f"{f['source']}: {f['error']}"), file=sys.stderr)
    print(json.dumps(report, indent=2))
    return 1 if report["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
