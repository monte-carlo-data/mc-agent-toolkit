#!/usr/bin/env python3
"""PreToolUse/bash hook (Cortex Code adapter): validation checkpoint before git commit.

CoCo Desktop and the Cortex Code CLI both drop a PreToolUse hook's
additionalContext before it reaches the model, but both pass a deny reason on.
So the checkpoint is delivered by denying the commit once; retrying the same
staged change goes through.
"""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from lib.safe_run import safe_run
from lib.protocol import HookInput, evaluate_pre_commit_once


@safe_run
def main():
    raw = json.load(sys.stdin)
    inp = HookInput(
        session_id=raw.get("session_id"),
        command=raw.get("tool_input", {}).get("command", ""),
        cwd=raw.get("cwd", "."),
    )
    result = evaluate_pre_commit_once(inp)
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
