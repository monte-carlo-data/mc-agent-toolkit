"""The OpenCode copy of Prevent's deny reasons carries the same instructions as the Python copy.

plugins/opencode/src/prevent/index.ts is maintained by hand next to plugins/shared/prevent/lib/protocol.py,
and CI doesn't run the OpenCode bun tests, so wording added to one copy could silently miss the other.
This compares the text of the string literals in both files, so it only catches a phrase missing from a
copy, not wording that differs around it.

Run: ``python3 -m unittest discover -s scripts/tests -p 'test_prevent_reason_sync.py' -v``
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PYTHON_COPY = REPO / "plugins" / "shared" / "prevent" / "lib" / "protocol.py"
TS_COPY = REPO / "plugins" / "opencode" / "src" / "prevent" / "index.ts"

# Instruction phrases both copies of the deny reasons must contain.
SHARED_PHRASES = [
    "only once the edit is going ahead",
    "only after they say yes",
    "visible reply text",
    "not only in your reasoning",
    "not inside a tool call",
    "re-read the file",
    "in a later step, not in the same batch",
    "check that the marker line is in your reply text",
    "load the `monte-carlo-asset-health` skill",
    "then ask the user whether to proceed before retrying the edit",
    "If you already wrote the completion marker",
    "has not completed yet",
]

# Messages are written as one string literal per line, joined with "+" in TypeScript and by
# implicit concatenation in Python. Matching whole-line literals keeps quotes inside code and
# comments from throwing off the match.
_TAIL = r"\s*[+,)]*\s*;?\s*$"
PY_LITERAL = re.compile(r'^\s*f?"((?:[^"\\]|\\.)*)"' + _TAIL, re.M)
TS_LITERAL = re.compile(
    r'^\s*(?:"((?:[^"\\]|\\.)*)"|\'((?:[^\'\\]|\\.)*)\'|`((?:[^`\\]|\\.)*)`)' + _TAIL, re.M
)


def _normalize(parts: list[str]) -> str:
    joined = "".join(parts)
    joined = joined.replace("{table_name}", "{T}").replace("${tableName}", "{T}")
    return " ".join(joined.split())


def python_text(source: str) -> str:
    """String literals of the Python source, joined so split messages stay contiguous."""
    return _normalize(PY_LITERAL.findall(source))


def ts_text(source: str) -> str:
    """String literals of the TypeScript source, joined so split messages stay contiguous."""
    return _normalize(["".join(m) for m in TS_LITERAL.findall(source)])


def missing_phrases(text: str) -> list[str]:
    return [p for p in SHARED_PHRASES if p not in text]


class DenyReasonsStayInSync(unittest.TestCase):
    def test_both_copies_contain_every_shared_phrase(self):
        copies = {
            PYTHON_COPY: python_text(PYTHON_COPY.read_text(encoding="utf-8")),
            TS_COPY: ts_text(TS_COPY.read_text(encoding="utf-8")),
        }
        for path, text in copies.items():
            for phrase in SHARED_PHRASES:
                with self.subTest(file=path.name, phrase=phrase):
                    self.assertIn(
                        phrase, text,
                        f"{path.relative_to(REPO)} lacks the deny-reason phrase {phrase!r}",
                    )


class SyncCheckCanFail(unittest.TestCase):
    def test_removed_phrase_is_reported(self):
        for name, text in (
            ("python", python_text(PYTHON_COPY.read_text(encoding="utf-8"))),
            ("ts", ts_text(TS_COPY.read_text(encoding="utf-8"))),
        ):
            self.assertEqual(missing_phrases(text), [], f"{name} baseline must pass")
            for phrase in SHARED_PHRASES:
                with self.subTest(file=name, phrase=phrase):
                    self.assertEqual(missing_phrases(text.replace(phrase, "")), [phrase])


if __name__ == "__main__":
    unittest.main()
