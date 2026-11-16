#!/usr/bin/env python3
"""
Tests for patch_agent_spec.py: the new spec keeps every untouched field byte for byte, and
the report names exactly the paths the patch changed.

Run:
    python3 skills/reinforce-agent/tests/test_patch_agent_spec.py
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parent.parent / "scripts" / "patch_agent_spec.py"

LONG_DESCRIPTION = (
    "MONITOR_RECOMMENDATION_TABLE:\n- Database: SMOKE_TESTS\n"
    "- LIST OF COLUMNS: CLIENT_NAME (name), TEST_BOOLEAN (flag) — “quoted” ünïcode"
)

SPEC = {
    "models": {"orchestration": "claude-opus-4-6"},
    "orchestration": {},
    "instructions": {"sample_questions": [{"question": "how far is the sun"}]},
    "tools": [
        {
            "tool_spec": {
                "type": "cortex_analyst_text_to_sql",
                "name": "client_test_tool",
                "description": LONG_DESCRIPTION,
            }
        },
        {"tool_spec": {"type": "cortex_search", "name": "client_search_tool"}},
    ],
    "skills": [],
    "tool_resources": {
        "client_search_tool": {"max_results": 4, "search_service": "DB.S.SEARCH"},
        "client_test_tool": {
            "execution_environment": {"query_timeout": 200, "type": "warehouse", "warehouse": ""},
            "semantic_view": "DB.S.VIEW",
        },
    },
}

RULE = "Summary requests: answer from aggregate queries."


def run(spec: object, patch: object) -> tuple[int, dict | None, dict | None, str]:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        (tmp_path / "spec.json").write_text(json.dumps(spec, ensure_ascii=False))
        (tmp_path / "patch.json").write_text(json.dumps(patch, ensure_ascii=False))
        out = tmp_path / "new.json"
        proc = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--spec",
                str(tmp_path / "spec.json"),
                "--patch",
                str(tmp_path / "patch.json"),
                "--out",
                str(out),
            ],
            capture_output=True,
            text=True,
        )
        report = json.loads(proc.stdout) if proc.returncode == 0 else None
        new_spec = json.loads(out.read_text()) if out.exists() else None
        return proc.returncode, report, new_spec, proc.stderr


class PatchAgentSpecTest(unittest.TestCase):
    def test_adds_a_nested_key_and_keeps_everything_else(self) -> None:
        code, report, new_spec, _ = run(SPEC, {"instructions": {"orchestration": RULE}})

        self.assertEqual(code, 0)
        self.assertEqual(
            report["changed"],
            [{"path": "instructions.orchestration", "before": None, "after": RULE}],
        )
        expected = json.loads(json.dumps(SPEC))
        expected["instructions"]["orchestration"] = RULE
        self.assertEqual(new_spec, expected)
        self.assertEqual(new_spec["tools"][0]["tool_spec"]["description"], LONG_DESCRIPTION)

    def test_replacing_a_string_reports_before_and_after(self) -> None:
        spec = json.loads(json.dumps(SPEC))
        spec["instructions"]["orchestration"] = "Old rule."
        code, report, _, _ = run(spec, {"instructions": {"orchestration": f"Old rule. {RULE}"}})

        self.assertEqual(code, 0)
        self.assertEqual(
            report["changed"],
            [
                {
                    "path": "instructions.orchestration",
                    "before": "Old rule.",
                    "after": f"Old rule. {RULE}",
                }
            ],
        )

    def test_null_deletes_and_arrays_replace_whole(self) -> None:
        code, report, new_spec, _ = run(
            SPEC, {"orchestration": None, "skills": [{"name": "s"}]}
        )

        self.assertEqual(code, 0)
        self.assertNotIn("orchestration", new_spec)
        self.assertEqual(new_spec["skills"], [{"name": "s"}])
        self.assertEqual(
            [change["path"] for change in report["changed"]], ["orchestration", "skills"]
        )

    def test_reports_a_change_of_json_type_alone(self) -> None:
        spec = {"flag": True, "count": 0, "name": "a"}
        code, report, _, _ = run(spec, {"flag": 1, "count": False})

        self.assertEqual(code, 0)
        self.assertEqual(
            report["changed"],
            [
                {"path": "count", "before": 0, "after": False},
                {"path": "flag", "before": True, "after": 1},
            ],
        )

    def test_reports_a_change_of_json_type_beside_another_change(self) -> None:
        code, report, _, _ = run({"flag": True, "name": "a"}, {"flag": 1, "name": "b"})

        self.assertEqual(code, 0)
        self.assertEqual([change["path"] for change in report["changed"]], ["flag", "name"])

    def test_a_patch_that_changes_nothing_fails(self) -> None:
        code, _, new_spec, stderr = run(SPEC, {"models": {"orchestration": "claude-opus-4-6"}})

        self.assertEqual(code, 3)
        self.assertIsNone(new_spec)
        self.assertIn("changes nothing", stderr)

    def test_inputs_must_be_json_objects(self) -> None:
        code, _, new_spec, stderr = run(["not", "an", "object"], {"a": 1})

        self.assertEqual(code, 1)
        self.assertIsNone(new_spec)
        self.assertIn("must be a JSON object", stderr)


if __name__ == "__main__":
    unittest.main()
