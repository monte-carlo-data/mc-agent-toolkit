#!/usr/bin/env python3
"""Validate cross-skill `## Next` hand-offs against the authoritative chain map.

Source of truth: skills/CHAINING.md (the "## Chain map" table). This script checks:

  1. Map integrity — every From/To in the table is a real skill dir; no self-references;
     no cycles (A->B->A or longer); every mode is one of immediate/deferred/confirm (or
     "-" for terminal rows).
  2. Hand-off conformance — every `## Next` section in a skill's SKILL.md only references
     real skills, and every (source -> target) it declares exists in the chain map.

Rollout is incremental: a chain-map row whose source skill hasn't grown a `## Next` yet is
reported as "pending", not an error. Stdlib only (no pip install), mirroring the other CI
checks in .github/workflows/validate.yml.

Exit 0 if clean, 1 on any error.
"""
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"
CHAINING_MD = SKILLS_DIR / "CHAINING.md"

VALID_MODES = {"immediate", "deferred", "confirm"}
TERMINAL_TOKENS = {"(terminal)", "terminal", "—", "-", ""}
NEXT_TARGET_RE = re.compile(r"\.\./([a-z0-9][a-z0-9-]*)/SKILL\.md")
NEXT_MODE_RE = re.compile(r"\*\*\[(immediate|deferred|confirm)\]\*\*")


def existing_skills() -> set[str]:
    return {d.name for d in SKILLS_DIR.iterdir() if d.is_dir() and (d / "SKILL.md").is_file()}


def parse_chain_map(text: str) -> list[dict]:
    """Parse the markdown table under the '## Chain map' heading."""
    lines = text.splitlines()
    in_section = False
    rows = []
    for line in lines:
        if re.match(r"^##\s+Chain map\s*$", line):
            in_section = True
            continue
        if in_section and re.match(r"^##\s+\S", line):
            break  # next section
        if not in_section or not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 4:
            continue
        frm, cond, to, mode = cells[0], cells[1], cells[2], cells[3]
        if frm.lower() == "from":  # header row
            continue
        if set(frm) <= {"-", ":"} and set(to) <= {"-", ":"}:  # separator row
            continue
        rows.append({"from": frm, "cond": cond, "to": to, "mode": mode})
    return rows


def find_cycle(edges: list[tuple[str, str]]) -> list[str] | None:
    adj: dict[str, list[str]] = {}
    for a, b in edges:
        adj.setdefault(a, []).append(b)
    WHITE, GREY, BLACK = 0, 1, 2
    color: dict[str, int] = {}
    stack: list[str] = []

    def dfs(node: str) -> list[str] | None:
        color[node] = GREY
        stack.append(node)
        for nxt in adj.get(node, []):
            if color.get(nxt, WHITE) == GREY:
                return stack[stack.index(nxt):] + [nxt]
            if color.get(nxt, WHITE) == WHITE:
                cyc = dfs(nxt)
                if cyc:
                    return cyc
        stack.pop()
        color[node] = BLACK
        return None

    for n in list(adj):
        if color.get(n, WHITE) == WHITE:
            cyc = dfs(n)
            if cyc:
                return cyc
    return None


def parse_next_entries(skill_dir: Path) -> list[tuple[str | None, str]]:
    """Return (mode, target) pairs referenced in a skill's `## Next` section.

    `mode` is the bracketed tag (immediate/deferred/confirm) on the same bullet as the
    target, or None if the bullet carries no tag. Parses per-line so each target is
    associated with its own bullet's mode. Stops at the next `##` or `###` heading.
    """
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        return []
    entries: list[tuple[str | None, str]] = []
    in_next = False
    for line in skill_md.read_text(encoding="utf-8").splitlines():
        if re.match(r"^##\s+Next\b", line):
            in_next = True
            continue
        if in_next and re.match(r"^###?\s+\S", line):
            break  # next section (level-2 or level-3 heading)
        if not in_next:
            continue
        mode_match = NEXT_MODE_RE.search(line)
        mode = mode_match.group(1) if mode_match else None
        for target in NEXT_TARGET_RE.findall(line):
            entries.append((mode, target))
    return entries


def main() -> int:
    errors: list[str] = []
    skills = existing_skills()

    if not CHAINING_MD.is_file():
        print(f"::error::missing {CHAINING_MD.relative_to(REPO_ROOT)}")
        return 1

    rows = parse_chain_map(CHAINING_MD.read_text(encoding="utf-8"))
    if not rows:
        print("::error::no chain-map rows parsed from skills/CHAINING.md '## Chain map' table")
        return 1

    edges: list[tuple[str, str]] = []
    map_modes: dict[tuple[str, str], str] = {}
    for r in rows:
        frm, to, mode = r["from"], r["to"], r["mode"]
        if frm not in skills:
            errors.append(f"chain map: unknown source skill '{frm}'")
            continue  # don't treat an invalid row as a real edge (avoids misleading follow-on errors)
        terminal = to in TERMINAL_TOKENS or to.lower().startswith("(terminal")
        if terminal:
            continue
        if to not in skills:
            errors.append(f"chain map: '{frm}' -> unknown target skill '{to}'")
        if frm == to:
            errors.append(f"chain map: '{frm}' hands off to itself")
        if mode not in VALID_MODES:
            errors.append(f"chain map: '{frm}' -> '{to}' has invalid mode '{mode}' "
                          f"(expected one of {sorted(VALID_MODES)})")
        edges.append((frm, to))
        map_modes[(frm, to)] = mode

    cyc = find_cycle(edges)
    if cyc:
        errors.append("chain map: cycle detected: " + " -> ".join(cyc))

    # Conformance: every `## Next` reference is a real skill, declared in the map, with a matching mode.
    implemented_sources: set[str] = set()
    for skill_dir in sorted(SKILLS_DIR.iterdir()):
        if not skill_dir.is_dir():
            continue
        src = skill_dir.name
        entries = parse_next_entries(skill_dir)
        if entries:
            implemented_sources.add(src)
        for mode, tgt in entries:
            if tgt not in skills:
                errors.append(f"{src}/SKILL.md '## Next' references unknown skill '{tgt}'")
            elif (src, tgt) not in map_modes:
                errors.append(f"{src}/SKILL.md '## Next' -> '{tgt}' is not in the CHAINING.md map")
            elif mode is not None and mode != map_modes[(src, tgt)]:
                errors.append(f"{src}/SKILL.md '## Next' -> '{tgt}' tagged [{mode}] "
                              f"but the map says [{map_modes[(src, tgt)]}]")

    # Informational: map sources not yet implemented as `## Next` (rollout in progress).
    map_sources = {frm for (frm, _to) in map_modes}
    pending = sorted(map_sources - implemented_sources)

    if errors:
        for e in errors:
            print(f"::error::{e}")
        print(f"\nFAIL: {len(errors)} chain-map / hand-off error(s).")
        return 1

    print(f"OK: {len(rows)} chain-map rows, {len(edges)} hand-offs, no cycles.")
    print(f"     {len(implemented_sources)} skill(s) with a '## Next'; {len(pending)} pending: "
          f"{', '.join(pending) if pending else 'none'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
