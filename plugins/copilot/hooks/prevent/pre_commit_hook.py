#!/usr/bin/env python3
"""preToolUse hook (Copilot CLI adapter): validation checkpoint before git commit."""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lib.safe_run import safe_run
from lib.protocol import HookInput, evaluate_pre_commit


@safe_run
def main():
    raw = json.load(sys.stdin)
    tool_name = raw.get("toolName", "")
    if tool_name != "bash":
        sys.exit(0)
    tool_args = json.loads(raw.get("toolArgs", "{}"))
    command = tool_args.get("command", "")
    inp = HookInput(
        session_id=str(os.getpid()),
        command=command,
        cwd=raw.get("cwd", "."),
    )
    result = evaluate_pre_commit(inp)
    if result.action == "context":
        print(json.dumps({
            "permissionDecision": "deny",
            "permissionDecisionReason": result.context,
        }))


if __name__ == "__main__":
    main()
