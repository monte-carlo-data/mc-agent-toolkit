#!/usr/bin/env python3
"""PreToolUse hook (VS Code adapter): gate ensuring impact assessment runs before editing dbt SQL."""
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.safe_run import safe_run
from lib.protocol import HookInput, evaluate_pre_edit


@safe_run
def main():
    raw = json.load(sys.stdin)
    inp = HookInput(
        session_id=raw.get("sessionId", "unknown"),
        file_path=raw.get("tool_input", {}).get("filePath", ""),
        transcript_path=raw.get("transcript_path", ""),
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
