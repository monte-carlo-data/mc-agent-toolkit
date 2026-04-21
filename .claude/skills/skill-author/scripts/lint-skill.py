#!/usr/bin/env python3
"""Lint a skill's SKILL.md frontmatter against mc-agent-toolkit standards.

Parses YAML frontmatter (handles scalar, block, and folded forms), then checks:
- name matches directory and is kebab-case
- description present, <= 1024 chars, no first-person opener
- when_to_use present (strongly recommended per CONTRIBUTING)
- combined description + when_to_use <= 1400 chars (headroom under 1536 truncation)

Exits 0 if clean, 1 on any ERROR, 2 on usage / file errors.
"""
import re
import sys
from pathlib import Path

MAX_DESCRIPTION = 1024
MAX_COMBINED = 1400
FIRST_PERSON_RE = re.compile(r"^\s*(this skill|use this skill)", re.IGNORECASE)
KEBAB_RE = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")


def parse_frontmatter(text: str) -> dict[str, str]:
    m = re.match(r"^---\s*\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return {}
    lines = m.group(1).split("\n")
    result: dict[str, str] = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.lstrip().startswith("#"):
            i += 1
            continue
        km = re.match(r"^([a-zA-Z_][a-zA-Z0-9_-]*)\s*:\s*(.*)$", line)
        if not km:
            i += 1
            continue
        key, rest = km.group(1), km.group(2).rstrip()
        if rest in ("|", ">", "|-", "|+", ">-", ">+"):
            i += 1
            block: list[str] = []
            while i < len(lines):
                bline = lines[i]
                if bline.startswith("  "):
                    block.append(bline[2:])
                    i += 1
                elif bline.strip() == "":
                    block.append("")
                    i += 1
                else:
                    break
            joined = "\n".join(block).rstrip("\n")
            if rest.startswith(">"):
                joined = re.sub(r"\n(?!\n)", " ", joined)
            result[key] = joined
        else:
            val = rest
            if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                val = val[1:-1]
            result[key] = val
            i += 1
    return result


def lint(name: str, skills_root: Path) -> tuple[list[str], list[str]]:
    path = skills_root / name / "SKILL.md"
    if not path.is_file():
        print(f"ERROR: {path} not found", file=sys.stderr)
        sys.exit(2)
    text = path.read_text()
    fm = parse_frontmatter(text)

    errors: list[str] = []
    warnings: list[str] = []

    actual_name = fm.get("name", "")
    if actual_name != name:
        errors.append(f"name '{actual_name}' does not match directory '{name}'")
    if actual_name and not KEBAB_RE.match(actual_name):
        errors.append(f"name '{actual_name}' is not kebab-case")

    desc = fm.get("description", "")
    if not desc:
        errors.append("description is missing (required)")
    else:
        if len(desc) > MAX_DESCRIPTION:
            errors.append(f"description is {len(desc)} chars (max {MAX_DESCRIPTION})")
        if FIRST_PERSON_RE.match(desc):
            errors.append(f"description opens with first-person phrasing (\"{desc[:40]}...\")")

    wtu = fm.get("when_to_use", "")
    if not wtu:
        warnings.append("when_to_use is missing (strongly recommended per CONTRIBUTING)")

    combined = len(desc) + len(wtu)
    if combined > MAX_COMBINED:
        errors.append(
            f"description + when_to_use = {combined} chars "
            f"(max {MAX_COMBINED} for headroom under 1536 truncation)"
        )

    print(f"skill: {name}")
    print(f"  description: {len(desc)} chars")
    print(f"  when_to_use: {len(wtu)} chars")
    print(f"  combined:    {combined} chars  (limit {MAX_COMBINED})")
    for w in warnings:
        print(f"  WARN:  {w}")
    for e in errors:
        print(f"  ERROR: {e}")

    return errors, warnings


def main() -> None:
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print("Usage: lint-skill.py <skill-name> [skills-root]", file=sys.stderr)
        sys.exit(2)
    name = sys.argv[1]
    skills_root = Path(sys.argv[2]) if len(sys.argv) == 3 else Path("skills")
    errors, _ = lint(name, skills_root)
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
