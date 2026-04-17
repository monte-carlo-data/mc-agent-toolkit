#!/usr/bin/env python3
# ruff: noqa
"""
Live eval runner for mc-agent-toolkit skills.

Runs skill prompts through the real Claude Code harness via claude-agent-sdk,
then scores results with deterministic checks and an LLM judge.

Usage:
    uv run python run_live_evals.py --skill monitoring-advisor
    uv run python run_live_evals.py --skill monitoring-advisor --env prod
    uv run python run_live_evals.py --skill monitoring-advisor --case live-01-warehouse-discovery --verbose

Exit codes:
    0 — pass rate meets threshold
    1 — pass rate below threshold
"""

import argparse
import asyncio
import json
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import anthropic
import yaml

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    SystemMessage,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    query,
)

from constants import EVALS_DIR, get_mcp_server_config, load_skill_content
from models import CaseResult, ConversationTrace, EvalCase, Turn, TurnCriteria


# ---------------------------------------------------------------------------
# AgentRunner — wraps claude-agent-sdk, runs prompts, returns traces
# ---------------------------------------------------------------------------

class AgentRunner:
    def __init__(self, model: str, max_turns: int, skill_content: str, mcp_servers: dict) -> None:
        self._model = model
        self._max_turns = max_turns
        self._skill_content = skill_content
        self._mcp_servers = mcp_servers

    async def run(self, turns: list[Turn]) -> tuple[ConversationTrace, list[ConversationTrace]]:
        """Run a conversation (1+ turns). Returns (accumulated, per_turn) traces."""
        accumulated = ConversationTrace()
        per_turn_traces: list[ConversationTrace] = []

        for i, turn in enumerate(turns):
            options = ClaudeAgentOptions(
                system_prompt={"type": "preset", "preset": "claude_code", "append": self._skill_content},
                permission_mode="bypassPermissions",
                max_turns=self._max_turns,
                model=self._model,
                mcp_servers=self._mcp_servers,
                # Ignore user/project MCP config so globally-installed servers
                # don't leak into the eval and skew results.
                extra_args={"strict-mcp-config": None},
            )
            if i > 0 and accumulated.session_id:
                options.resume = accumulated.session_id

            turn_trace = self._collect_trace(turn.prompt, options)
            per_turn_traces.append(await turn_trace)

            # Accumulate
            latest = per_turn_traces[-1]
            accumulated.tools_called.extend(latest.tools_called)
            accumulated.tool_details.extend(latest.tool_details)
            accumulated.messages.extend(latest.messages)
            accumulated.stderr.extend(latest.stderr)
            accumulated.final_text = latest.final_text
            accumulated.total_cost_usd += latest.total_cost_usd
            accumulated.num_turns += latest.num_turns
            accumulated.session_id = latest.session_id

        return accumulated, per_turn_traces

    async def _collect_trace(self, prompt: str, options: ClaudeAgentOptions) -> ConversationTrace:
        """Run a single prompt through the agent and collect the trace."""
        trace = ConversationTrace()
        last_assistant_text = ""

        # Capture stderr via callback
        stderr_lines: list[str] = []
        options.stderr = lambda line: stderr_lines.append(line)

        async for message in query(prompt=prompt, options=options):
            trace.messages.append(self._serialize_message(message))

            if isinstance(message, AssistantMessage):
                text_parts = []
                for block in message.content:
                    if isinstance(block, ToolUseBlock):
                        trace.tools_called.append(block.name)
                        trace.tool_details.append({"name": block.name, "input": block.input})
                    elif isinstance(block, TextBlock):
                        text_parts.append(block.text)
                if text_parts:
                    last_assistant_text = "\n".join(text_parts)
            elif isinstance(message, ResultMessage):
                trace.session_id = message.session_id
                trace.total_cost_usd = getattr(message, "total_cost_usd", 0.0) or 0.0
                trace.num_turns = getattr(message, "num_turns", 0) or 0

        trace.final_text = last_assistant_text
        trace.stderr = stderr_lines
        return trace

    @staticmethod
    def _serialize_message(message: AssistantMessage | ResultMessage | SystemMessage) -> dict:
        """Convert an SDK message to a JSON-serializable dict."""
        if isinstance(message, AssistantMessage):
            blocks = []
            for block in message.content:
                if isinstance(block, TextBlock):
                    blocks.append({"type": "text", "text": block.text})
                elif isinstance(block, ToolUseBlock):
                    blocks.append({"type": "tool_use", "name": block.name, "input": block.input})
                elif isinstance(block, ToolResultBlock):
                    blocks.append({"type": "tool_result", "tool_use_id": block.tool_use_id, "content": str(block.content)})
                else:
                    blocks.append({"type": type(block).__name__, "raw": str(block)})
            return {"role": "assistant", "content": blocks}
        elif isinstance(message, ResultMessage):
            return {
                "role": "result",
                "session_id": message.session_id,
                "cost_usd": getattr(message, "total_cost_usd", 0.0) or 0.0,
                "num_turns": getattr(message, "num_turns", 0) or 0,
            }
        elif isinstance(message, SystemMessage):
            return {"role": "system", "content": str(getattr(message, "content", ""))}
        return {"role": "unknown", "raw": str(message)}


# ---------------------------------------------------------------------------
# Scorer — deterministic checks + LLM judge
# ---------------------------------------------------------------------------

class Scorer:
    JUDGE_SYSTEM_PROMPT = (
        "You are a strict evaluator scoring an AI agent's performance on a monitoring task.\n\n"
        "You will receive:\n"
        "1. The user prompt that was given to the agent\n"
        "2. The full conversation trace (tool calls and final output)\n"
        "3. A rubric describing what good performance looks like\n\n"
        "Score the agent's response on a scale of 0.0 to 1.0:\n"
        "- 1.0 = perfect, follows rubric completely\n"
        "- 0.7 = acceptable, minor issues\n"
        "- 0.5 = mediocre, significant issues\n"
        "- 0.0 = completely wrong or off-topic\n\n"
        'Respond with ONLY valid JSON: {"score": <float>, "reason": "<brief explanation>"}'
    )

    def __init__(self, judge_model: str, judge_threshold: float = 0.7) -> None:
        self._judge_model = judge_model
        self._judge_threshold = judge_threshold
        self._client = anthropic.Anthropic()

    def score_case(
        self, case: EvalCase, accumulated: ConversationTrace, per_turn: list[ConversationTrace],
    ) -> CaseResult:
        """Run all checks and return a structured result."""
        # Per-turn deterministic checks
        turn_failures: list[str] = []
        for i, turn in enumerate(case.turns):
            passed, failures = self._check_deterministic(turn.criteria, per_turn[i])
            if not passed:
                turn_failures.extend([f"turn-{i+1}: {f}" for f in failures])

        # Case-level deterministic checks
        case_passed, case_failures = self._check_deterministic(case.criteria, accumulated)
        all_failures = case_failures + turn_failures
        det_passed = case_passed and len(turn_failures) == 0

        # LLM judge
        judge_score = 1.0
        judge_reason = ""
        if case.criteria.judge_rubric:
            judge_score, judge_reason = self._judge(
                case.turns[-1].prompt, accumulated, case.criteria.judge_rubric,
            )

        passed = det_passed and judge_score >= self._judge_threshold

        return CaseResult(
            id=case.id,
            passed=passed,
            deterministic_passed=det_passed,
            deterministic_failures=all_failures,
            judge_score=judge_score,
            judge_reason=judge_reason,
            tools_called=accumulated.tools_called,
            num_turns=accumulated.num_turns,
            cost_usd=accumulated.total_cost_usd,
            final_text=accumulated.final_text,
            tool_details=accumulated.tool_details,
            messages=accumulated.messages,
            stderr=accumulated.stderr,
        )

    def _check_deterministic(self, criteria: TurnCriteria, trace: ConversationTrace) -> tuple[bool, list[str]]:
        """Run deterministic checks against a trace. Returns (passed, failures)."""
        failures: list[str] = []

        for tool in criteria.must_call:
            if not any(tool in called for called in trace.tools_called):
                failures.append(f"must_call: {tool} not found in trace")

        for tool in criteria.must_not_call:
            if any(tool in called for called in trace.tools_called):
                failures.append(f"must_not_call: {tool} was called")

        for substring in criteria.output_must_not_contain:
            if substring.lower() in trace.final_text.lower():
                failures.append(f"output_must_not_contain: found '{substring}'")

        return len(failures) == 0, failures

    def _judge(self, prompt: str, trace: ConversationTrace, rubric: str) -> tuple[float, str]:
        """Score a conversation trace with the LLM judge. Returns (score, reason)."""
        trace_summary = f"Tools called: {trace.tools_called}\n\nFinal output:\n{trace.final_text}"

        message = self._client.messages.create(
            model=self._judge_model,
            max_tokens=256,
            system=self.JUDGE_SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": (
                    f"## User prompt\n{prompt}\n\n"
                    f"## Conversation trace\n{trace_summary}\n\n"
                    f"## Rubric\n{rubric}\n\n"
                    "Score as JSON:"
                ),
            }],
        )

        raw = message.content[0].text.strip()
        try:
            result = json.loads(raw)
            return float(result["score"]), result.get("reason", "")
        except (json.JSONDecodeError, KeyError, ValueError):
            return 0.0, f"Judge returned invalid JSON: {raw}"


# ---------------------------------------------------------------------------
# EvalRunner — loads cases, orchestrates agent + scorer, reports results
# ---------------------------------------------------------------------------

class EvalRunner:
    def __init__(
        self, skill: str, env: str, agent: AgentRunner, scorer: Scorer, threshold: float,
    ) -> None:
        self._skill = skill
        self._env = env
        self._agent = agent
        self._scorer = scorer
        self._threshold = threshold
        self._eval_file = self._resolve_eval_file()
        self._output_dir = self._create_output_dir()

    def load_cases(self, case_filter: str | None = None) -> list[EvalCase]:
        """Load eval cases from YAML, optionally filtering to a single case."""
        data = yaml.safe_load(self._eval_file.read_text())
        cases = [EvalCase.from_dict(c) for c in data.get("cases", [])]
        if case_filter:
            cases = [c for c in cases if c.id == case_filter]
            if not cases:
                print(f"Error: Case '{case_filter}' not found in {self._eval_file}")
                sys.exit(1)
        return cases

    async def run(
        self, cases: list[EvalCase], verbose: bool = False, dry_run: bool = False,
        parallel: int = 1,
    ) -> list[CaseResult]:
        """Run all cases and return results. parallel=N runs N cases concurrently."""
        self._print_header(cases, parallel)

        if dry_run:
            self._print_dry_run(cases)
            sys.exit(0)

        print()
        start = time.monotonic()
        if parallel <= 1:
            results = await self._run_sequential(cases, verbose)
        else:
            results = await self._run_parallel(cases, parallel, verbose)
        elapsed = time.monotonic() - start

        self._print_summary(results, elapsed)
        return results

    async def _run_sequential(self, cases: list[EvalCase], verbose: bool) -> list[CaseResult]:
        results: list[CaseResult] = []
        for case in cases:
            print(f"  ▶ [{case.id}] started")
            started_at = datetime.now(timezone.utc)
            try:
                result = await self._run_and_score(case)
            except Exception as e:
                result = self._error_result(case, e, started_at)
            result_path = self._write_result_file(result)
            results.append(result)
            self._print_result(result, result_path, verbose)
        return results

    async def _run_parallel(self, cases: list[EvalCase], workers: int, verbose: bool) -> list[CaseResult]:
        """Run cases in parallel using a thread pool — each thread gets its own event loop."""
        started_times: dict[str, datetime] = {}

        def run_in_thread(case: EvalCase) -> CaseResult:
            started_times[case.id] = datetime.now(timezone.utc)
            print(f"  ▶ [{case.id}] started")
            loop = asyncio.new_event_loop()
            try:
                return loop.run_until_complete(self._run_and_score(case))
            finally:
                loop.close()

        results_by_id: dict[str, CaseResult] = {}
        with ThreadPoolExecutor(max_workers=workers) as pool:
            future_to_case = {pool.submit(run_in_thread, c): c for c in cases}
            for future in as_completed(future_to_case):
                case = future_to_case[future]
                try:
                    result = future.result()
                except Exception as e:
                    result = self._error_result(case, e, started_times.get(case.id, datetime.now(timezone.utc)))
                result_path = self._write_result_file(result)
                results_by_id[case.id] = result
                self._print_result(result, result_path, verbose)

        # Return in original case order
        return [results_by_id[c.id] for c in cases]

    @staticmethod
    def _error_result(case: EvalCase, error: Exception, started_at: datetime) -> CaseResult:
        finished_at = datetime.now(timezone.utc)
        return CaseResult(
            id=case.id, passed=False, deterministic_passed=False,
            deterministic_failures=[f"agent error: {error}"],
            judge_score=0.0, judge_reason="", tools_called=[],
            num_turns=0, cost_usd=0.0,
            error=traceback.format_exception(error)[-1].strip(),
            stderr=[traceback.format_exc()],
            started_at=started_at, finished_at=finished_at,
            elapsed_seconds=(finished_at - started_at).total_seconds(),
        )

    async def _run_and_score(self, case: EvalCase) -> CaseResult:
        started_at = datetime.now(timezone.utc)
        accumulated, per_turn = await self._agent.run(case.turns)
        result = self._scorer.score_case(case, accumulated, per_turn)
        result.started_at = started_at
        result.finished_at = datetime.now(timezone.utc)
        result.elapsed_seconds = (result.finished_at - result.started_at).total_seconds()
        return result

    def _create_output_dir(self) -> Path:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        output_dir = EVALS_DIR / "eval_results" / f"{self._skill}_{self._env}_{ts}"
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir

    def _write_result_file(self, result: CaseResult) -> Path:
        """Write a JSON result file for a single case."""
        output = {
            "id": result.id,
            "passed": result.passed,
            "deterministic_passed": result.deterministic_passed,
            "deterministic_failures": result.deterministic_failures,
            "judge_score": result.judge_score,
            "judge_reason": result.judge_reason,
            "tools_called": result.tools_called,
            "num_turns": result.num_turns,
            "cost_usd": result.cost_usd,
            "final_text": result.final_text,
            "tool_details": result.tool_details,
            "conversation": result.messages,
            "stderr": result.stderr,
            "error": result.error,
            "started_at": result.started_at.isoformat() if result.started_at else None,
            "finished_at": result.finished_at.isoformat() if result.finished_at else None,
            "elapsed_seconds": result.elapsed_seconds,
            "metadata": {
                "skill": self._skill,
                "env": self._env,
            },
        }
        path = self._output_dir / f"{result.id}.json"
        path.write_text(json.dumps(output, indent=2, default=str))
        return path.relative_to(EVALS_DIR)

    def _resolve_eval_file(self) -> Path:
        """Find the eval YAML: env-specific first, then generic fallback."""
        env_specific = EVALS_DIR / self._skill / f"live-evals-{self._env}.yaml"
        generic = EVALS_DIR / self._skill / "live-evals.yaml"
        if env_specific.exists():
            return env_specific
        if generic.exists():
            return generic
        print(f"Error: No eval file found. Tried:\n  {env_specific}\n  {generic}")
        sys.exit(1)

    def _print_header(self, cases: list[EvalCase], parallel: int = 1) -> None:
        print(f"Skill:      {self._skill}")
        print(f"Env:        {self._env}")
        print(f"Eval file:  {self._eval_file}")
        print(f"Output:     {self._output_dir}")
        print(f"Cases:      {len(cases)}")
        print(f"Parallel:   {parallel}")
        print(f"Threshold:  {self._threshold:.0%}")

    def _print_dry_run(self, cases: list[EvalCase]) -> None:
        print(f"\n[dry-run] Loaded {len(cases)} cases from {self._eval_file.name}")
        for case in cases:
            n = len(case.turns)
            label = f"{n} turn{'s' if n > 1 else ''}"
            print(f"  [{case.id}] ({label}) {case.turns[0].prompt[:75]}")

    def _print_result(self, result: CaseResult, result_path: Path, verbose: bool) -> None:
        status = "✓" if result.passed else "✗"
        cost = f"${result.cost_usd:.4f}" if result.cost_usd else "n/a"
        elapsed = f"{result.elapsed_seconds:.0f}s" if result.elapsed_seconds else "n/a"
        print(f"  {status} [{result.id}] judge={result.judge_score:.2f} turns={result.num_turns} cost={cost} elapsed={elapsed} → {result_path}")

        if not result.deterministic_passed:
            for f in result.deterministic_failures:
                print(f"      FAIL: {f}")

        if result.judge_score < 0.7:
            print(f"      JUDGE: {result.judge_reason}")

        if verbose and result.final_text:
            print(f"      --- final text ---")
            for line in result.final_text[:500].split("\n"):
                print(f"      {line}")
            if len(result.final_text) > 500:
                print(f"      ... ({len(result.final_text)} chars total)")

        if verbose and result.tool_details:
            print(f"      --- tool calls ---")
            for td in result.tool_details:
                print(f"      {td['name']}({json.dumps(td['input'], default=str)[:120]})")

    def _print_summary(self, results: list[CaseResult], elapsed: float = 0) -> None:
        total = len(results)
        passed = sum(r.passed for r in results)
        pass_rate = passed / total if total else 0
        total_cost = sum(r.cost_usd for r in results)

        elapsed_str = f"  elapsed={elapsed:.0f}s" if elapsed else ""
        print(f"\nResult: {passed}/{total} passed ({pass_rate:.0%})  total_cost=${total_cost:.4f}{elapsed_str}")

        if pass_rate >= self._threshold:
            print(f"✓ Pass rate meets threshold ({self._threshold:.0%})")
            sys.exit(0)
        else:
            print(f"✗ Pass rate below threshold ({self._threshold:.0%})")
            sys.exit(1)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Run live evals for an mc-agent-toolkit skill")
    parser.add_argument("--skill", required=True, help="Skill directory name (e.g. 'monitoring-advisor')")
    parser.add_argument("--env", default="dev", choices=["dev", "prod"], help="MCP environment (default: dev)")
    parser.add_argument("--model", default="claude-sonnet-4-6", help="Agent model (default: claude-sonnet-4-6)")
    parser.add_argument("--judge-model", default="claude-sonnet-4-6", help="Judge model (default: claude-sonnet-4-6)")
    parser.add_argument("--max-turns", type=int, default=30, help="Max agent turns (default: 30)")
    parser.add_argument("--threshold", type=float, default=0.80, help="Min pass rate (default: 0.80)")
    parser.add_argument("--case", default=None, help="Run a single case by ID")
    parser.add_argument("--parallel", type=int, default=1, help="Run N cases concurrently (default: 1)")
    parser.add_argument("--verbose", action="store_true", help="Print full traces")
    parser.add_argument("--dry-run", action="store_true", help="Validate cases only")
    parser.add_argument(
        "--skip-missing-skill", action="store_true",
        help="If SKILL.md is missing, warn and run without skill content (useful for baselines)",
    )
    args = parser.parse_args()

    mcp_servers = get_mcp_server_config(args.env)
    skill_content = load_skill_content(args.skill, skip_missing=args.skip_missing_skill)

    agent = AgentRunner(
        model=args.model,
        max_turns=args.max_turns,
        skill_content=skill_content,
        mcp_servers=mcp_servers,
    )
    scorer = Scorer(judge_model=args.judge_model)
    runner = EvalRunner(
        skill=args.skill,
        env=args.env,
        agent=agent,
        scorer=scorer,
        threshold=args.threshold,
    )

    cases = runner.load_cases(case_filter=args.case)
    asyncio.run(runner.run(cases, verbose=args.verbose, dry_run=args.dry_run, parallel=args.parallel))


if __name__ == "__main__":
    main()
