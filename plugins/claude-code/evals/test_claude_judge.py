"""Offline tests for the CLI-backed judge and the verdict/score parsers.

Run: uv run python -m unittest test_claude_judge
"""
import asyncio
import unittest
from unittest.mock import patch

from claude_agent_sdk import AssistantMessage, ResultMessage, TextBlock

import claude_judge
from claude_judge import JudgeError
from run_evals import parse_verdict
from run_live_evals import parse_judge_score


class JudgeOptions(unittest.TestCase):
    def test_bare_completion(self):
        options = claude_judge.judge_options("sys", "claude-sonnet-4-6")
        self.assertEqual(options.system_prompt, "sys")
        self.assertEqual(options.tools, [])
        self.assertEqual(options.max_turns, 1)
        self.assertEqual(options.setting_sources, [])
        self.assertEqual(options.model, "claude-sonnet-4-6")
        self.assertIn("strict-mcp-config", options.extra_args)
        self.assertFalse(options.mcp_servers)


class Ask(unittest.TestCase):
    def test_joins_assistant_text(self):
        async def fake_query(prompt, options):
            yield AssistantMessage(content=[TextBlock(text="TRIG"), TextBlock(text="GER")], model="m")

        with patch.object(claude_judge, "query", fake_query):
            self.assertEqual(asyncio.run(claude_judge.ask("s", "p", "m")), "TRIG\nGER")

    def _result(self, is_error: bool, result: str = "") -> ResultMessage:
        return ResultMessage(
            subtype="error_during_execution" if is_error else "success", duration_ms=1,
            duration_api_ms=1, is_error=is_error, num_turns=1, session_id="s", result=result,
        )

    def test_error_result_raises(self):
        async def fake_query(prompt, options):
            yield AssistantMessage(content=[TextBlock(text="Invalid API key · Please run /login")], model="m")
            yield self._result(is_error=True, result="Invalid API key")

        with patch.object(claude_judge, "query", fake_query):
            with self.assertRaises(claude_judge.JudgeError):
                asyncio.run(claude_judge.ask("s", "p", "m"))

    def test_empty_reply_raises(self):
        async def fake_query(prompt, options):
            yield self._result(is_error=False)

        with patch.object(claude_judge, "query", fake_query):
            with self.assertRaises(claude_judge.JudgeError):
                asyncio.run(claude_judge.ask("s", "p", "m"))


class Parsers(unittest.TestCase):
    def test_verdict(self):
        self.assertEqual(parse_verdict("TRIGGER"), "trigger")
        self.assertEqual(parse_verdict("no_trigger"), "no-trigger")
        self.assertEqual(parse_verdict("NO-TRIGGER"), "no-trigger")
        self.assertEqual(parse_verdict("No trigger."), "no-trigger")

    def test_verdict_reads_the_first_word_only(self):
        # 'KNOW' and 'NOT' contain 'NO'; they must not flip a TRIGGER verdict.
        self.assertEqual(parse_verdict("TRIGGER - the user wants to know how, not monitoring"), "trigger")
        self.assertEqual(parse_verdict("**TRIGGER**"), "trigger")

    def test_unparseable_verdict_raises(self):
        for raw in ("", "Invalid API key · Please run /login", "Maybe"):
            with self.assertRaises(JudgeError, msg=raw):
                parse_verdict(raw)

    def test_score_plain_and_fenced(self):
        self.assertEqual(parse_judge_score('{"score": 0.8, "reason": "ok"}'), (0.8, "ok"))
        self.assertEqual(parse_judge_score('```json\n{"score": 1, "reason": "r"}\n```'), (1.0, "r"))

    def test_score_invalid(self):
        score, reason = parse_judge_score("not json")
        self.assertEqual(score, 0.0)
        self.assertIn("invalid JSON", reason)


if __name__ == "__main__":
    unittest.main()
