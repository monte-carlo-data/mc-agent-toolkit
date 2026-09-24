"""Offline tests for the CLI-backed judge and the verdict/score parsers.

Run: uv run python -m unittest test_claude_judge
"""
import asyncio
import unittest
from unittest.mock import patch

from claude_agent_sdk import AssistantMessage, TextBlock

import claude_judge
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


class Parsers(unittest.TestCase):
    def test_verdict(self):
        self.assertEqual(parse_verdict("TRIGGER"), "trigger")
        self.assertEqual(parse_verdict("no_trigger"), "no-trigger")
        self.assertEqual(parse_verdict(""), "no-trigger")

    def test_score_plain_and_fenced(self):
        self.assertEqual(parse_judge_score('{"score": 0.8, "reason": "ok"}'), (0.8, "ok"))
        self.assertEqual(parse_judge_score('```json\n{"score": 1, "reason": "r"}\n```'), (1.0, "r"))

    def test_score_invalid(self):
        score, reason = parse_judge_score("not json")
        self.assertEqual(score, 0.0)
        self.assertIn("invalid JSON", reason)


if __name__ == "__main__":
    unittest.main()
