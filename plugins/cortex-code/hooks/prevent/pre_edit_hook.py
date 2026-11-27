#!/usr/bin/env python3
"""PreToolUse hook (Cortex Code adapter): gate ensuring impact assessment runs before editing dbt SQL.

Cortex stores the session message log in a sibling `<id>.history.jsonl`, while the
hook's `transcript_path` points at the `<id>.json` session-metadata file. We rewrite
the path to the history sibling and tell the shared scanner to read it as Anthropic
Messages-style JSONL, matching markers only in assistant text blocks — never in
tool_result blocks, where Cortex persists this gate's own deny reason.

Cortex Code's `apply_patch` (given to GPT and OpenAI models) can touch several files in
one call. Every file is checked, so each gets its own assessment state, and the patch is
denied as a whole when any of them needs an assessment.
"""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from lib.safe_run import safe_run
from lib.apply_patch import gate_and_remember
from lib.protocol import HookInput, evaluate_pre_edit


def _history_path(transcript_path: str) -> str:
    """Map Cortex's `<id>.json` metadata path to the sibling `<id>.history.jsonl`."""
    if transcript_path.endswith(".json"):
        return transcript_path[: -len(".json")] + ".history.jsonl"
    return transcript_path


def _deny(reason: str) -> None:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }))


def _hook_input(raw: dict, file_path: str) -> HookInput:
    return HookInput(
        session_id=raw.get("session_id", "unknown"),
        file_path=file_path,
        transcript_path=_history_path(raw.get("transcript_path", "")),
        transcript_format="messages_jsonl",
    )


def _gate_patch(raw: dict) -> None:
    tool_input = raw.get("tool_input") or {}
    reason = gate_and_remember(
        tool_input.get("input"), "cortex", cwd=raw.get("cwd"),
        session_id=raw.get("session_id", "unknown"), call_id=raw.get("tool_use_id"),
        make_input=lambda path: _hook_input(raw, path), evaluate=evaluate_pre_edit,
    )
    if reason:
        _deny(reason)


@safe_run
def main():
    raw = json.load(sys.stdin)
    if raw.get("tool_name") == "apply_patch":
        _gate_patch(raw)
        return
    result = evaluate_pre_edit(_hook_input(raw, raw.get("tool_input", {}).get("file_path", "")))
    if result.action == "deny":
        _deny(result.reason)


if __name__ == "__main__":
    main()
