#!/usr/bin/env python3
"""Check that every skill's SKILL.md frontmatter is valid YAML with a `name` and a `description`.

Hosts read the frontmatter with YAML parsers, and some are strict: one value PyYAML rejects can drop
the skill, or a whole skill catalog. The toolkit's own line-based readers accept such values, so only
a real parser catches them.

Usage: check_skill_frontmatter.py [ROOT ...]
  ROOT is a directory of skill folders (default: skills and .claude/skills in this repo). Every
  ROOT/*/SKILL.md must start with a `---` line, close with a standalone `---` line, parse with
  yaml.safe_load to a mapping, and hold `name` and `description` as non-blank strings.
  Exits 1 on any failure, including a ROOT that is missing or has no SKILL.md.
"""
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROOTS = (REPO_ROOT / "skills", REPO_ROOT / ".claude" / "skills")
REQUIRED = ("name", "description")


def check(path: Path) -> list[str]:
    try:
        lines = path.read_text(encoding="utf-8").split("\n")
    except UnicodeDecodeError as e:
        return [f"file is not valid UTF-8: {e}"]
    if lines[0] != "---":
        return ["no frontmatter (the first line must be ---)"]
    try:
        end = lines.index("---", 1)
    except ValueError:
        return ["frontmatter has no closing --- line"]
    try:
        data = yaml.safe_load("\n".join(lines[1:end]))
    except (yaml.YAMLError, ValueError) as e:  # ValueError: a value PyYAML can't build, e.g. 2026-02-30
        reason = " ".join(str(e).split())
        return [f"frontmatter is not valid YAML: {reason}. Quote a value that contains ': ' or ' #'."]
    if not isinstance(data, dict):
        return ["frontmatter is not a mapping of keys to values"]
    return [
        f"`{key}` must be a non-blank string"
        for key in REQUIRED
        if not isinstance(data.get(key), str) or not data[key].strip()
    ]


def main(argv: list[str]) -> int:
    roots = [Path(a) for a in argv] or list(DEFAULT_ROOTS)
    failed = False
    checked = 0
    for root in roots:
        if not root.is_dir():
            print(f"::error::{root} does not exist")
            failed = True
            continue
        files = sorted(root.glob("*/SKILL.md"))
        if not files:
            print(f"::error::{root} has no */SKILL.md")
            failed = True
        for path in files:
            checked += 1
            shown = path.relative_to(Path.cwd()) if path.is_relative_to(Path.cwd()) else path
            for problem in check(path):
                print(f"::error file={shown}::{problem}")
                failed = True
    if failed:
        return 1
    print(f"OK: {checked} skills checked")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
