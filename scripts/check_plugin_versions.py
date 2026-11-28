#!/usr/bin/env python3
"""Check that every editor plugin's manifest holds the same version.

The release workflow tags v<version> from the Claude Code manifest alone. If another manifest is
left behind, that release ships no matching build for that editor: the CoCo Desktop publish, for
one, has nothing to pin for a release whose Cortex Code manifest wasn't bumped.
scripts/bump-version.sh bumps them all; this catches a manifest edited by hand.

Usage: check_plugin_versions.py [ROOT]
  ROOT is the repo root (default: this repo). The manifests are the VERSION_FILES list in
  ROOT/scripts/bump-version.sh, so there is one list to keep up to date. Exits 1 if the list
  can't be read, a manifest is missing, unreadable or has no version, or the versions differ.
"""
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def manifest_paths(root: Path) -> list[str]:
    bump = (root / "scripts" / "bump-version.sh").read_text(encoding="utf-8")
    block = re.search(r"^VERSION_FILES=\(\n(.*?)\n\)", bump, re.DOTALL | re.MULTILINE)
    return re.findall(r'"([^"]+)"', block.group(1)) if block else []


def main(argv: list[str]) -> int:
    root = Path(argv[0]) if argv else REPO_ROOT
    paths = manifest_paths(root)
    if not paths:
        print("::error::no VERSION_FILES list in scripts/bump-version.sh")
        return 1
    versions, problems = {}, []
    for path in paths:
        try:
            data = json.loads((root / path).read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            problems.append(f"{path}: can't read: {exc}")
            continue
        version = data.get("version") if isinstance(data, dict) else None
        if not isinstance(version, str) or not version:
            problems.append(f"{path}: no version")
            continue
        versions[path] = version
    if not problems and len(set(versions.values())) == 1:
        print(f"OK: {len(versions)} plugin manifests are at {next(iter(versions.values()))}")
        return 0
    if len(set(versions.values())) > 1:
        problems += [f"{path}: {version}" for path, version in versions.items()]
    print("::error::Plugin manifests must all hold the same version; bump with ./scripts/bump-version.sh")
    for problem in problems:
        print(f"  {problem}")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
