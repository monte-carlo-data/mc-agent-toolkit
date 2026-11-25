"""The Prevent skill tells the model where and when to write the impact-check completion marker.

The edit gate unlocks only on a marker it can read in the saved conversation, in the model's reply
text. CoCo Desktop saves an assistant message only after its edit's PreToolUse hook has run, so a
marker in the same message as the edit isn't seen in time, and a marker kept in the model's
reasoning or inside a tool call is never read. These tests pin the skill's instructions; they
can't show that a model follows them (live runs do that).

Run: ``python3 -m unittest discover -s scripts/tests -p 'test_prevent_skill_markers.py' -v``
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SKILL = REPO / "skills" / "prevent" / "SKILL.md"
WORKFLOWS = REPO / "skills" / "prevent" / "references" / "workflows.md"


def section(text: str, heading: str) -> str:
    """Body of a markdown section, up to the next heading of the same or higher level."""
    level = len(heading) - len(heading.lstrip("#"))
    start = text.index(heading + "\n") + len(heading) + 1
    nxt = re.compile(rf"^#{{1,{level}}} ", re.M).search(text, start)
    return text[start: nxt.start() if nxt else len(text)]


def flatten(text: str) -> str:
    """Collapse whitespace so line wrapping in the prose doesn't matter."""
    return " ".join(text.split())


def marker_errors(body: str) -> list[str]:
    """What the 'Impact check complete' section is missing."""
    required = {
        "timing": "only once the edit is going ahead",
        "after yes": "only after they say yes",
        "denied retry": "check that the marker line is in your reply text",
        "open question": "wait for its answer first",
        "decline": "don't write the marker",
        "visible text": "visible reply text",
        "not reasoning": "not only in your reasoning",
        "not a tool call": "not inside a tool call",
        "re-read": "re-read the file",
        "later step": "in a later step, not in the same batch",
    }
    flat = flatten(body)
    errors = [name for name, phrase in required.items() if phrase not in flat]
    if not re.search(r"```\w*\nMC_IMPACT_CHECK_COMPLETE: <table_name>\n```", body):
        errors.append("plain fenced example")
    if "After the engineer confirms (High/Medium) or after presenting the synthesis (Low)" in flat:
        errors.append("old timing line")
    return errors


class ImpactCheckMarkerRule(unittest.TestCase):
    def setUp(self):
        self.text = SKILL.read_text(encoding="utf-8")
        self.body = section(self.text, "### Impact check complete")

    def test_marker_section(self):
        self.assertEqual(marker_errors(self.body), [])

    def test_pre_edit_gate_points_to_the_rule(self):
        gate = section(self.text, "## Pre-edit gate — check before modifying any file")
        yes_item = re.search(r"\*\*If YES\*\*.*?(?=\n\d+\. )", gate, re.S).group(0)
        self.assertIn("writing the completion marker first", flatten(yes_item))
        self.assertIn("Impact check complete", yes_item)

    def test_editor_note_doesnt_excuse_a_denial(self):
        # "Denied once" read as "a deny is expected, retry": a model claimed a marker it never
        # wrote and retried. The note must say a deny after the marker means it wasn't found.
        note = flatten(re.search(
            r"<!-- plugin-only:start -->\n(.*?)<!-- plugin-only:end -->", self.body, re.S).group(1))
        self.assertNotIn("denied once", note)
        self.assertIn("don't retry as if the denial were a timing glitch", note)
        self.assertIn("didn't find the marker in your saved reply text", note)

    def test_no_old_confirmation_wording(self):
        # "Any required confirmation" read as "none needed" on Low risk, even after asking.
        self.assertNotIn("any required confirmation", flatten(self.text))

    def test_confirmation_rules_point_to_the_rule(self):
        rules = section(self.text, "## Post-synthesis confirmation rules")
        self.assertIn("Impact check complete", rules)

    def test_monitor_offer_is_not_edit_approval(self):
        text = WORKFLOWS.read_text(encoding="utf-8")
        self.assertIn("The answer to the monitor offer is not approval to edit", flatten(text))


class MarkerCheckCanFail(unittest.TestCase):
    """Each requirement is caught when it is removed from the real section."""

    def setUp(self):
        self.body = section(SKILL.read_text(encoding="utf-8"), "### Impact check complete")
        self.assertEqual(marker_errors(self.body), [], "baseline must pass")

    def test_each_phrase(self):
        for phrase, name in [
            ("only once the edit is going ahead", "timing"),
            ("only after they say yes", "after yes"),
            ("check that the marker line is in your reply text", "denied retry"),
            ("visible reply text", "visible text"),
            ("not only in your reasoning", "not reasoning"),
            ("re-read the file", "re-read"),
            ("in a later step, not in the same batch", "later step"),
        ]:
            with self.subTest(name=name):
                self.assertIn(name, marker_errors(flatten(self.body).replace(phrase, "")))

    def test_html_comment_only_example(self):
        mutated = self.body.replace(
            "```\nMC_IMPACT_CHECK_COMPLETE: <table_name>\n```",
            "<!-- MC_IMPACT_CHECK_COMPLETE: <table_name> -->",
        )
        self.assertIn("plain fenced example", marker_errors(mutated))

    def test_old_timing_line(self):
        mutated = self.body + (
            "\nAfter the engineer confirms (High/Medium) or after presenting the synthesis (Low),\n"
        )
        self.assertIn("old timing line", marker_errors(mutated))


if __name__ == "__main__":
    unittest.main()
