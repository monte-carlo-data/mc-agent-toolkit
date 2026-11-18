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


def compare(spec: object, other: object, *extra: str) -> tuple[int, dict | None, list[str], str]:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        (tmp_path / "spec.json").write_text(json.dumps(spec, ensure_ascii=False))
        (tmp_path / "other.json").write_text(json.dumps(other, ensure_ascii=False))
        proc = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--spec",
                str(tmp_path / "spec.json"),
                "--compare",
                str(tmp_path / "other.json"),
                *extra,
            ],
            capture_output=True,
            text=True,
        )
        report = json.loads(proc.stdout) if proc.returncode == 0 else None
        return proc.returncode, report, sorted(p.name for p in tmp_path.iterdir()), proc.stderr


class PatchAgentSpecTest(unittest.TestCase):
    def test_adds_a_nested_key_and_keeps_everything_else(self) -> None:
        code, report, new_spec, _ = run(SPEC, {"instructions": {"orchestration": RULE}})

        self.assertEqual(code, 0)
        self.assertEqual(
            report["changed"],
            [{"path": "instructions.orchestration", "change": "added", "before": None, "after": RULE}],
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

    def test_reports_a_change_of_json_type_inside_an_array(self) -> None:
        code, report, _, _ = run({"flags": [True]}, {"flags": [1]})

        self.assertEqual(code, 0)
        self.assertEqual(report["changed"], [{"path": "flags[0]", "before": True, "after": 1}])

    def test_reports_each_changed_field_inside_an_array(self) -> None:
        tools = json.loads(json.dumps(SPEC["tools"]))
        tools[0]["tool_spec"]["description"] = "New description."
        tools[1]["tool_spec"]["description"] = "Added by mistake."
        code, report, _, _ = run(SPEC, {"tools": tools})

        self.assertEqual(code, 0)
        self.assertEqual(
            report["changed"],
            [
                {
                    "path": "tools[0].tool_spec.description",
                    "before": LONG_DESCRIPTION,
                    "after": "New description.",
                },
                {
                    "path": "tools[1].tool_spec.description",
                    "change": "added",
                    "before": None,
                    "after": "Added by mistake.",
                },
            ],
        )

    def test_an_array_that_changes_length_is_reported_whole(self) -> None:
        code, report, _, _ = run(SPEC, {"skills": [{"name": "s"}]})

        self.assertEqual(code, 0)
        self.assertEqual(
            report["changed"], [{"path": "skills", "before": [], "after": [{"name": "s"}]}]
        )

    def test_compare_reports_each_difference_and_writes_nothing(self) -> None:
        other = json.loads(json.dumps(SPEC))
        other["instructions"]["orchestration"] = RULE
        other["tools"][1]["tool_spec"]["name"] = "renamed_search_tool"
        del other["skills"]

        code, report, files, _ = compare(SPEC, other)

        self.assertEqual(code, 0)
        self.assertEqual(
            report,
            {
                "changed": [
                    {
                        "path": "instructions.orchestration",
                        "change": "added",
                        "before": None,
                        "after": RULE,
                    },
                    {"path": "skills", "change": "removed", "before": [], "after": None},
                    {
                        "path": "tools[1].tool_spec.name",
                        "before": "client_search_tool",
                        "after": "renamed_search_tool",
                    },
                ]
            },
        )
        self.assertEqual(files, ["other.json", "spec.json"])

    def test_compare_tells_a_missing_key_from_an_explicit_null(self) -> None:
        with_null = {"models": {"orchestration": None}}
        without = {"models": {}}

        _, added, _, _ = compare(without, with_null)
        _, removed, _, _ = compare(with_null, without)

        self.assertEqual(
            added,
            {"changed": [{"path": "models.orchestration", "change": "added", "before": None, "after": None}]},
        )
        self.assertEqual(
            removed,
            {"changed": [{"path": "models.orchestration", "change": "removed", "before": None, "after": None}]},
        )

    def test_compare_of_equal_specs_reports_no_changes(self) -> None:
        code, report, _, _ = compare(SPEC, json.loads(json.dumps(SPEC)))

        self.assertEqual(code, 0)
        self.assertEqual(report, {"changed": []})

    def test_compare_cannot_be_combined_with_a_patch(self) -> None:
        code, _, _, stderr = compare(SPEC, SPEC, "--patch", "x.json", "--out", "y.json")

        self.assertEqual(code, 2)
        self.assertIn("not both", stderr)

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
