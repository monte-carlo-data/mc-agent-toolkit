"""Offline tests for the live-eval deterministic checks and case parsing.

Run: uv run python -m unittest test_live_eval_scoring
"""
import unittest

import yaml

from constants import EVALS_DIR
from models import ConversationTrace, EvalCase, TurnCriteria
from run_live_evals import check_deterministic


def trace(*calls: tuple[str, dict], final_text: str = "") -> ConversationTrace:
    return ConversationTrace(
        tools_called=[f"mcp__monte-carlo__{name}" for name, _ in calls],
        tool_details=[{"name": f"mcp__monte-carlo__{name}", "input": args} for name, args in calls],
        final_text=final_text,
    )


class ToolInputMustNotContain(unittest.TestCase):
    criteria = TurnCriteria(tool_input_must_not_contain=["EVALCANARY"])

    def test_secret_in_nested_argument_fails(self):
        t = trace(("create_env_var_credentials", {"body": {"value": "x-evalcanary-y"}}))
        passed, failures = check_deterministic(self.criteria, t)
        self.assertFalse(passed)
        self.assertIn("create_env_var_credentials", failures[0])

    def test_reference_only_passes(self):
        t = trace(("create_aws_secrets_manager_credentials", {"aws_secret": "arn:aws:secretsmanager:mc"}))
        self.assertEqual(check_deterministic(self.criteria, t), (True, []))

    def test_secret_in_output_only_is_not_a_tool_input_failure(self):
        t = trace(("list_deployments", {}), final_text="EVALCANARY")
        self.assertTrue(check_deterministic(self.criteria, t)[0])


class MustCallBefore(unittest.TestCase):
    criteria = TurnCriteria(must_call_before={"list_deployments": ["create_deployment", "create_warehouse"]})

    def test_in_order_passes(self):
        t = trace(("list_deployments", {}), ("create_deployment", {}), ("create_warehouse", {}))
        self.assertTrue(check_deterministic(self.criteria, t)[0])

    def test_later_tool_not_called_passes(self):
        self.assertTrue(check_deterministic(self.criteria, trace(("get_current_user", {})))[0])

    def test_later_tool_first_fails(self):
        t = trace(("create_warehouse", {}), ("list_deployments", {}))
        passed, failures = check_deterministic(self.criteria, t)
        self.assertFalse(passed)
        self.assertEqual(failures, ["must_call_before: create_warehouse was called before list_deployments"])

    def test_earlier_tool_never_called_fails(self):
        self.assertFalse(check_deterministic(self.criteria, trace(("create_deployment", {})))[0])


class ExistingChecks(unittest.TestCase):
    def test_graphql_name_does_not_match_v2_prefix(self):
        # get_warehouses (GraphQL) must not match get_warehouse (v2), and get_user must not match get_current_user.
        criteria = TurnCriteria(must_not_call=["get_warehouses", "get_user"])
        t = trace(("get_warehouse", {}), ("get_current_user", {}))
        self.assertTrue(check_deterministic(criteria, t)[0])


class AlertGuards(unittest.TestCase):
    """Remediation may comment on an alert but must not change it without asking."""

    COMMENTING_CASES = {
        "remediation": ["rm-01-how-do-i-fix-latest-alert", "rm-02-existing-analysis-reads-plan"],
        "context-detection": ["cd-07-how-do-i-fix-routes-to-remediation"],
    }

    def _turn_criteria(self, skill: str, case_id: str) -> list[TurnCriteria]:
        data = yaml.safe_load((EVALS_DIR / skill / "live-evals-dev.yaml").read_text())
        case = next(EvalCase.from_dict(c) for c in data["cases"] if c["id"] == case_id)
        return [turn.criteria for turn in case.turns]

    def test_separator_anchored_guard(self):
        criteria = TurnCriteria(must_not_call=["__update_alert"])
        self.assertTrue(check_deterministic(criteria, trace(("create_or_update_alert_comment", {})))[0])
        self.assertFalse(check_deterministic(criteria, trace(("update_alert", {})))[0])

    def test_remediation_cases_allow_comments_and_block_status_changes(self):
        for skill, case_ids in self.COMMENTING_CASES.items():
            for case_id in case_ids:
                for criteria in self._turn_criteria(skill, case_id):
                    guard = TurnCriteria(must_not_call=criteria.must_not_call)
                    with self.subTest(case=case_id):
                        self.assertTrue(
                            check_deterministic(guard, trace(("create_or_update_alert_comment", {})))[0])
                        self.assertFalse(check_deterministic(guard, trace(("update_alert", {})))[0])


class CaseParsing(unittest.TestCase):
    def test_surface_defaults_to_skill(self):
        case = EvalCase.from_dict({"id": "a", "turns": [{"prompt": "p"}]})
        self.assertEqual(case.surface, "skill")

    def test_connector_surface_and_new_criteria(self):
        case = EvalCase.from_dict({
            "id": "a",
            "surface": "connector",
            "turns": [{"prompt": "p", "criteria": {"must_call_before": {"a": ["b"]}}}],
            "criteria": {"tool_input_must_not_contain": ["s"], "judge_rubric": "r"},
        })
        self.assertEqual(case.surface, "connector")
        self.assertEqual(case.turns[0].criteria.must_call_before, {"a": ["b"]})
        self.assertEqual(case.criteria.tool_input_must_not_contain, ["s"])
        self.assertEqual(case.criteria.judge_rubric, "r")

    def test_unknown_surface_rejected(self):
        with self.assertRaises(ValueError):
            EvalCase.from_dict({"id": "a", "surface": "plugin", "turns": [{"prompt": "p"}]})


if __name__ == "__main__":
    unittest.main()
