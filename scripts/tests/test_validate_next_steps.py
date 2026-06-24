#!/usr/bin/env python3
"""Unit + integration tests for scripts/validate-next-steps.py (stdlib only).

Run directly: `python3 scripts/tests/test_validate_next_steps.py`
Mirrors the skills/instrument-agent/tests pattern — no pytest, no pip install.
"""
import contextlib
import importlib.util
import io
import sys
import tempfile
from pathlib import Path

# Load the hyphenated script as a module.
_SCRIPT = Path(__file__).resolve().parent.parent / "validate-next-steps.py"
_spec = importlib.util.spec_from_file_location("validate_next_steps", _SCRIPT)
vns = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vns)

_failures: list[str] = []


def check(name: str, cond: bool) -> None:
    print(f"  {'PASS' if cond else 'FAIL'}: {name}")
    if not cond:
        _failures.append(name)


# ── parse_chain_map ────────────────────────────────────────────────────────
def test_parse_chain_map():
    text = """
## Chain map

| From | Condition | To | Mode |
|------|-----------|----|------|
| asset-health | active alerts | incident-response | immediate |
| asset-health | healthy | (terminal) | — |
| monitoring-advisor | yaml ready | manage-mac | confirm |

## Next section
| not | a | chain | row |
"""
    rows = vns.parse_chain_map(text)
    check("parse_chain_map: 3 data rows (header+separator skipped)", len(rows) == 3)
    check("parse_chain_map: stops at next ## heading", all(r["from"] != "not" for r in rows))
    check("parse_chain_map: terminal row preserved", rows[1]["to"] == "(terminal)")
    check("parse_chain_map: mode captured", rows[2]["mode"] == "confirm")


# ── find_cycle ─────────────────────────────────────────────────────────────
def test_find_cycle():
    check("find_cycle: direct A->B->A", vns.find_cycle([("a", "b"), ("b", "a")]) is not None)
    check("find_cycle: longer A->B->C->A",
          vns.find_cycle([("a", "b"), ("b", "c"), ("c", "a")]) is not None)
    check("find_cycle: acyclic", vns.find_cycle([("a", "b"), ("b", "c"), ("a", "c")]) is None)
    check("find_cycle: empty", vns.find_cycle([]) is None)
    check("find_cycle: self-loop", vns.find_cycle([("a", "a")]) is not None)


# ── parse_next_entries ─────────────────────────────────────────────────────
def test_parse_next_entries():
    with tempfile.TemporaryDirectory() as d:
        skill = Path(d) / "src-skill"
        skill.mkdir()
        (skill / "SKILL.md").write_text(
            "# Skill\n\nbody\n\n## Next\n\n"
            "- **[immediate]** go: read and follow `../incident-response/SKILL.md`.\n"
            "- **[confirm]** apply: read and follow `../manage-mac/SKILL.md`.\n"
            "- If healthy → nothing to do. (terminal)\n\n"
            "### Sub note\n"
            "- ignore `../should-not-capture/SKILL.md`\n\n"
            "## Other\n"
            "- also ignore `../nope/SKILL.md`\n",
            encoding="utf-8",
        )
        entries = vns.parse_next_entries(skill)
        targets = [t for _m, t in entries]
        check("parse_next_entries: captures 2 tagged targets", len(entries) == 2)
        check("parse_next_entries: mode paired with target",
              ("immediate", "incident-response") in entries and ("confirm", "manage-mac") in entries)
        check("parse_next_entries: stops at ### subheading (excludes should-not-capture)",
              "should-not-capture" not in targets)
        check("parse_next_entries: excludes content after ## Other", "nope" not in targets)


def test_parse_next_entries_none():
    with tempfile.TemporaryDirectory() as d:
        skill = Path(d) / "no-next"
        skill.mkdir()
        (skill / "SKILL.md").write_text("# Skill\n\nbody, no Next section\n", encoding="utf-8")
        check("parse_next_entries: empty when no ## Next", vns.parse_next_entries(skill) == [])


# ── main() integration via monkeypatched module globals ────────────────────
@contextlib.contextmanager
def fake_repo(chaining_table: str, skills_with_next: dict[str, str], exclude: frozenset = frozenset()):
    """Build a tmp repo: skills/<name>/SKILL.md for every name appearing, plus CHAINING.md.

    Names in `exclude` are intentionally NOT created (to simulate an unknown skill).
    """
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        skills_dir = root / "skills"
        skills_dir.mkdir()
        # every skill named in the table or in skills_with_next gets a dir + SKILL.md
        names = set(skills_with_next)
        for line in chaining_table.splitlines():
            if line.strip().startswith("|"):
                cells = [c.strip() for c in line.strip().strip("|").split("|")]
                if len(cells) >= 3 and cells[0].lower() != "from" and not set(cells[0]) <= {"-", ":"}:
                    names.add(cells[0])
                    if not (cells[2].startswith("(terminal") or cells[2] == "—"):
                        names.add(cells[2])
        for name in names - set(exclude):
            sdir = skills_dir / name
            sdir.mkdir(exist_ok=True)
            (sdir / "SKILL.md").write_text(skills_with_next.get(name, "# " + name + "\n"), encoding="utf-8")
        (skills_dir / "CHAINING.md").write_text("## Chain map\n\n" + chaining_table, encoding="utf-8")
        orig = (vns.REPO_ROOT, vns.SKILLS_DIR, vns.CHAINING_MD)
        vns.REPO_ROOT, vns.SKILLS_DIR, vns.CHAINING_MD = root, skills_dir, skills_dir / "CHAINING.md"
        try:
            yield
        finally:
            vns.REPO_ROOT, vns.SKILLS_DIR, vns.CHAINING_MD = orig


def run_main() -> int:
    with contextlib.redirect_stdout(io.StringIO()):
        return vns.main()


def test_main_valid():
    table = ("| From | Condition | To | Mode |\n|--|--|--|--|\n"
             "| asset-health | alerts | incident-response | immediate |\n")
    nxt = {"asset-health": "## Next\n- **[immediate]** read and follow `../incident-response/SKILL.md`.\n"}
    with fake_repo(table, nxt):
        check("main: valid map+next → 0", run_main() == 0)


def test_main_mode_mismatch():
    # F1: prose says immediate, map says confirm → must fail
    table = ("| From | Condition | To | Mode |\n|--|--|--|--|\n"
             "| monitoring-advisor | yaml | manage-mac | confirm |\n")
    nxt = {"monitoring-advisor": "## Next\n- **[immediate]** read and follow `../manage-mac/SKILL.md`.\n"}
    with fake_repo(table, nxt):
        check("main: mode mismatch (immediate vs confirm) → 1", run_main() == 1)


def test_main_unknown_source_single_error():
    # F4: unknown source row should not also produce a spurious conformance error
    table = ("| From | Condition | To | Mode |\n|--|--|--|--|\n"
             "| typo-skill | x | manage-mac | immediate |\n")
    with fake_repo(table, {}, exclude=frozenset({"typo-skill"})):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            rc = vns.main()
        errs = [l for l in out.getvalue().splitlines() if "::error::" in l]
        check("main: unknown source → 1", rc == 1)
        check("main: unknown source produces exactly one error (no fall-through)", len(errs) == 1)


def test_main_cycle():
    table = ("| From | Condition | To | Mode |\n|--|--|--|--|\n"
             "| a | x | b | immediate |\n| b | y | a | immediate |\n")
    with fake_repo(table, {}):
        check("main: cycle → 1", run_main() == 1)


def main() -> int:
    for fn in [test_parse_chain_map, test_find_cycle, test_parse_next_entries,
               test_parse_next_entries_none, test_main_valid, test_main_mode_mismatch,
               test_main_unknown_source_single_error, test_main_cycle]:
        print(fn.__name__)
        fn()
    print()
    if _failures:
        print(f"FAILED: {len(_failures)} check(s): {', '.join(_failures)}")
        return 1
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
