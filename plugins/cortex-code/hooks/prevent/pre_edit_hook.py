#!/usr/bin/env python3
"""PreToolUse hook (Cortex Code adapter): gate ensuring impact assessment runs before editing dbt SQL.

Cortex stores the session message log in a sibling `<id>.history.jsonl`, while the
hook's `transcript_path` points at the `<id>.json` session-metadata file. We rewrite
the path to the history sibling and tell the shared scanner to read it as Anthropic
Messages-style JSONL, matching markers only in assistant text blocks — never in
tool_result blocks, where Cortex persists this gate's own deny reason.
"""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from lib.safe_run import safe_run
from lib.protocol import HookInput, evaluate_pre_edit


def _history_path(transcript_path: str) -> str:
    """Map Cortex's `<id>.json` metadata path to the sibling `<id>.history.jsonl`."""
    if transcript_path.endswith(".json"):
        return transcript_path[: -len(".json")] + ".history.jsonl"
    return transcript_path


@safe_run
def main():
    raw = json.load(sys.stdin)
    inp = HookInput(
        session_id=raw.get("session_id", "unknown"),
        file_path=raw.get("tool_input", {}).get("file_path", ""),
        transcript_path=_history_path(raw.get("transcript_path", "")),
        transcript_format="messages_jsonl",
    )
    result = evaluate_pre_edit(inp)
    if result.action == "deny":
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": result.reason,
            }
        }))


if __name__ == "__main__":
    main()
