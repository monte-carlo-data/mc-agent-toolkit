"""Shared skills route Monte Carlo MCP tools without naming any client's tool-ID format.

Clients name the same MCP tool differently (Claude Code ``mcp__<server>__<tool>``, CoCo Desktop
``mcp_<label cut to 13>_<tool>``, opencode ``<server>_<tool>``), and a skill under ``skills/`` is read
by all of them, by standalone installs and by the MCP server's prompt renderer. The routing note's
contract lives in ``.claude/rules/skills.md`` § "Route Monte Carlo MCP calls".

Run: ``python3 -m unittest discover -s scripts/tests -p 'test_skill_tool_routing.py' -v``
"""

from __future__ import annotations

import importlib.util
import re
import subprocess
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SKILLS = REPO / "skills"
RULES = REPO / ".claude" / "rules" / "skills.md"
RULES_SECTION = "## Route Monte Carlo MCP calls"

_lint_spec = importlib.util.spec_from_file_location(
    "lint_skill", REPO / ".claude" / "skills" / "toolkit-skill-author" / "scripts" / "lint-skill.py"
)
lint_skill = importlib.util.module_from_spec(_lint_spec)
_lint_spec.loader.exec_module(lint_skill)

# Skills that call Monte Carlo MCP tools and must carry the routing note. Listed explicitly so
# deleting a note fails instead of silently removing the check's input. Onboarding is portable and
# keeps host routing in its command adapters instead.
ROUTED_SKILLS = (
    "account-analytics",
    "analyze-root-cause",
    "asset-health",
    "automated-triage",
    "context-detection",
    "incident-response",
    "instrument-agent",
    "manage-mac",
    "monitoring-advisor",
    "performance-diagnosis",
    "prevent",
    "reinforce-agent",
    "remediation",
    "storage-cost-analysis",
    "troubleshoot-agent-traces",
    "tune-monitor",
)

# Operations a skill tells the agent not to use, so its note must not offer them as examples.
FORBIDDEN_EXAMPLES = {"account-analytics": {"get_alerts", "get_monitors"}}

PORTABLE_LABEL = "**Monte Carlo tool routing (required):**"
PLUGIN_LABEL = "**With the Agent Toolkit plugin:**"
MARKER_START = "<!-- plugin-only:start -->"
MARKER_END = "<!-- plugin-only:end -->"

# The operation list is the one per-skill slot in the portable note.
_EXAMPLES_SLOT = re.compile(r"such as ((?:`[a-z][a-z0-9_]*`(?:, | and |, and ))*`[a-z][a-z0-9_]*`),")
_EXAMPLE_NAME = re.compile(r"`([a-z][a-z0-9_]*)`")

# Server labels a shared skill might name in CoCo Desktop's tool-ID form: Monte Carlo itself and the
# servers the skills discover. A generic ``mcp_<x>_<y>`` ban would hit ordinary identifiers.
_DESKTOP_LABELS = (
    "monte", "snowflake", "airflow", "dagster", "prefect", "dbt", "github", "gitlab",
    "bigquery", "databricks", "fivetran", "jira",
)
CLIENT_TOOL_ID_PATTERNS = {
    "Claude Code / Cortex Code CLI form (mcp__<server>__<tool>)": re.compile(r"mcp__"),
    "CoCo Desktop form (mcp_<label>_<tool>)": re.compile(
        r"(?<![\w-])mcp_(?:" + "|".join(_DESKTOP_LABELS) + r")[\w.-]*_[\w*<]", re.IGNORECASE
    ),
    "opencode form (<server>_<tool>)": re.compile(r"monte-carlo(?:-mcp)?_[\w*<]", re.IGNORECASE),
}


def client_tool_ids(text: str) -> list[str]:
    """Each client-specific tool-ID spelling in ``text``, as ``<form>: <match>``."""
    found = []
    for form, pattern in CLIENT_TOOL_ID_PATTERNS.items():
        for match in pattern.finditer(text):
            line = text.count("\n", 0, match.start()) + 1
            found.append(f"line {line}: {form}: {match.group(0)!r}")
    return found


def blockquotes(text: str) -> list[tuple[str, bool]]:
    """Every blockquote paragraph, unquoted and whitespace-collapsed, flagged True if plugin-only."""
    quotes: list[tuple[str, bool]] = []
    current: list[str] = []
    inside = False

    def flush() -> None:
        if current:
            quotes.append((" ".join(" ".join(current).split()), current_inside[0]))
            current.clear()

    current_inside = [False]
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped in (MARKER_START, MARKER_END):
            flush()
            inside = stripped == MARKER_START
            continue
        if stripped.startswith(">"):
            if not current:
                current_inside[0] = inside
            current.append(stripped[1:].strip())
        else:
            flush()
    flush()
    return quotes


def canonical_note() -> tuple[str, str]:
    """The portable and plugin-only paragraphs of the canonical block in the rules file."""
    rules = RULES.read_text(encoding="utf-8")
    if rules.count(RULES_SECTION) != 1:
        raise AssertionError(f"{RULES}: expected exactly one {RULES_SECTION!r} section")
    section = rules.split(RULES_SECTION, 1)[1].split("\n## ", 1)[0]
    fences = re.findall(r"```markdown\n(.*?)```", section, re.DOTALL)
    if len(fences) != 1:
        raise AssertionError(f"{RULES}: expected one ```markdown block in {RULES_SECTION!r}")
    quotes = blockquotes(fences[0])
    portable = [q for q, inside in quotes if q.startswith(PORTABLE_LABEL) and not inside]
    plugin = [q for q, inside in quotes if q.startswith(PLUGIN_LABEL) and inside]
    if len(quotes) != 2 or len(portable) != 1 or len(plugin) != 1:
        raise AssertionError(f"{RULES}: canonical block must be one portable and one marked paragraph")
    return portable[0], plugin[0]


def without_routing_note(text: str) -> str:
    """``text`` minus the blockquote paragraph that holds the routing note."""
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if "Monte Carlo tool routing" in line:
            start = i
            while start > 0 and lines[start - 1].strip().startswith(">"):
                start -= 1
            end = i
            while end + 1 < len(lines) and lines[end + 1].strip().startswith(">"):
                end += 1
            return "\n".join(lines[:start] + lines[end + 1 :])
    return text


def routing_errors(skill: str, text: str) -> list[str]:
    """Why ``text`` (a routed skill's SKILL.md) does not carry the canonical routing note."""
    errors = list(lint_skill.check_plugin_only_markers(text))
    if errors:
        return errors
    portable_ref, plugin_ref = canonical_note()
    quotes = blockquotes(text)

    portable = [(q, inside) for q, inside in quotes if "Monte Carlo tool routing" in q]
    if len(portable) != 1:
        errors.append(f"expected one 'Monte Carlo tool routing' note, found {len(portable)}")
    else:
        note, inside = portable[0]
        if inside:
            errors.append("the portable routing note is inside plugin-only markers")
        slot = _EXAMPLES_SLOT.search(note)
        if not slot:
            errors.append("the routing note's 'such as `op`, … and `op`,' example list is malformed")
        else:
            ref_slot = _EXAMPLES_SLOT.search(portable_ref)
            normalized = note.replace(slot.group(1), ref_slot.group(1), 1)
            if normalized != portable_ref:
                errors.append(f"routing note differs from {RULES.name}:\n  got:  {note}\n  want: {portable_ref}")
            examples = set(_EXAMPLE_NAME.findall(slot.group(1)))
            skill_dir = SKILLS / skill
            references = "".join(
                path.read_text(encoding="utf-8") for path in sorted(skill_dir.rglob("*.md"))
                if path.name != "SKILL.md"
            ) if skill_dir.is_dir() else ""
            outside_note = without_routing_note(text) + references
            unused = sorted(e for e in examples if f"`{e}" not in outside_note)
            if unused:
                errors.append(f"example operations the skill never names: {unused}")
            forbidden = sorted(examples & FORBIDDEN_EXAMPLES.get(skill, set()))
            if forbidden:
                errors.append(f"example operations the skill forbids: {forbidden}")

    plugin = [(q, inside) for q, inside in quotes if "Agent Toolkit plugin:**" in q]
    if len(plugin) != 1:
        errors.append(f"expected one plugin-only routing paragraph, found {len(plugin)}")
    else:
        note, inside = plugin[0]
        if not inside:
            errors.append("the plugin routing paragraph is outside plugin-only markers")
        if note != plugin_ref:
            errors.append(f"plugin routing paragraph differs from {RULES.name}:\n  got:  {note}\n  want: {plugin_ref}")
    return errors


def shared_skill_files() -> list[Path]:
    listed = subprocess.run(
        ["git", "-C", str(REPO), "ls-files", "-z", "--", "skills/"],
        capture_output=True, check=True,
    ).stdout.decode().split("\0")
    return [REPO / name for name in listed if name and (REPO / name).is_file()]


class ClientToolIdScanner(unittest.TestCase):
    """The scanner catches each client form and passes ordinary text."""

    def test_flags_each_client_form(self):
        for spelling in (
            "mcp__plugin_mc-agent-toolkit_monte-carlo-mcp__get_alerts",
            "mcp__monte-carlo-mcp__search",
            "scan for `mcp__*__*` patterns",
            "mcp__<server_name>__<tool_name>",
            "mcp__snowflake__query",
            "mcp_monte-carlo-m_search",
            "mcp_monte-carlo-m2_search",
            "mcp_snowflake_query",
            "monte-carlo-mcp_search",
            "monte-carlo_*",
        ):
            with self.subTest(spelling=spelling):
                self.assertTrue(client_tool_ids(spelling), spelling)

    def test_passes_ordinary_text(self):
        for text in (
            "call `get_alerts` then `search`",
            "the `monte-carlo-mcp` server",
            "https://mcp.getmontecarlo.com/mcp/toolkit",
            "Record `mcp_available = false`",
            "set mcp_server_url",
            "a Snowflake MCP server with a query tool",
        ):
            with self.subTest(text=text):
                self.assertEqual(client_tool_ids(text), [])


class SharedSkillsNameNoClientToolIds(unittest.TestCase):
    def test_no_client_tool_id_under_skills(self):
        files = shared_skill_files()
        self.assertGreater(len(files), 100, "git ls-files found too few skill files")
        hits = []
        for path in files:
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            hits += [f"{path.relative_to(REPO)} {hit}" for hit in client_tool_ids(text)]
        self.assertEqual(hits, [], "shared skills name client-specific MCP tool IDs:\n" + "\n".join(hits))


class RoutedSkillsCarryTheNote(unittest.TestCase):
    def test_canonical_block_parses(self):
        portable, plugin = canonical_note()
        self.assertTrue(_EXAMPLES_SLOT.search(portable))
        self.assertEqual(client_tool_ids(portable + plugin), [])

    def test_every_routed_skill(self):
        for skill in ROUTED_SKILLS:
            with self.subTest(skill=skill):
                text = (SKILLS / skill / "SKILL.md").read_text(encoding="utf-8")
                self.assertEqual(routing_errors(skill, text), [])


class RoutingCheckCanFail(unittest.TestCase):
    """Each way of breaking a correct note is caught (mutations of a real routed skill)."""

    SKILL = "asset-health"

    def setUp(self):
        self.text = (SKILLS / self.SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertEqual(routing_errors(self.SKILL, self.text), [], "baseline must pass")
        self.portable = next(
            line for line in self.text.split("\n") if PORTABLE_LABEL in line
        )
        start = self.text.index(MARKER_START)
        end = self.text.index(MARKER_END) + len(MARKER_END)
        self.marked = self.text[start:end]

    def assertBroken(self, text, skill=None):
        self.assertNotEqual(routing_errors(skill or self.SKILL, text), [])

    def test_note_deleted(self):
        self.assertBroken(self.text.replace(self.portable, ""))

    def test_label_renamed(self):
        self.assertBroken(self.text.replace("tool routing (required)", "tool usage (required)"))

    def test_note_duplicated(self):
        self.assertBroken(self.text.replace(self.portable, self.portable + "\n\n" + self.portable))

    def test_one_word_edited(self):
        self.assertBroken(self.text.replace("intended account", "current account", 1))

    def test_portable_note_hidden_in_markers(self):
        self.assertBroken(self.text.replace(self.portable, f"{MARKER_START}\n{self.portable}\n{MARKER_END}"))

    def test_plugin_paragraph_exposed(self):
        unmarked = self.marked.replace(MARKER_START + "\n", "").replace("\n" + MARKER_END, "")
        self.assertBroken(self.text.replace(self.marked, unmarked))

    def test_plugin_paragraph_deleted(self):
        self.assertBroken(self.text.replace(self.marked, ""))

    def test_unbalanced_markers(self):
        self.assertBroken(self.text.replace(MARKER_END, "", 1))

    def test_example_the_skill_never_names(self):
        self.assertNotIn("`get_queries`", self.text)
        self.assertBroken(self.text.replace(self.portable, self.portable.replace("`search`", "`get_queries`")))

    def test_forbidden_example(self):
        text = (SKILLS / "account-analytics" / "SKILL.md").read_text(encoding="utf-8")
        self.assertEqual(routing_errors("account-analytics", text), [])
        note = text[: len(text) - len(text.split(PORTABLE_LABEL, 1)[1])]  # up to the label
        rest = text[len(note) :]
        first = _EXAMPLE_NAME.search(rest).group(1)  # first example in the note
        self.assertBroken(note + rest.replace(f"`{first}`", "`get_alerts`", 1), "account-analytics")


if __name__ == "__main__":
    unittest.main()
