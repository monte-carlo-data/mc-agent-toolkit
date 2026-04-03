#!/usr/bin/env python3
"""PreToolUse hook (VS Code adapter): validation checkpoint before git commit."""
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.safe_run import safe_run
from lib.protocol import HookInput, evaluate_pre_commit


@safe_run
def main():
    raw = json.load(sys.stdin)
    inp = HookInput(
        session_id=raw.get("sessionId", "unknown"),
        command=raw.get("tool_input", {}).get("command", ""),
        cwd=raw.get("cwd", "."),
    )
    result = evaluate_pre_commit(inp)
    if result.action == "context":
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "additionalContext": result.context,
            }
        }))


if __name__ == "__main__":
    main()
