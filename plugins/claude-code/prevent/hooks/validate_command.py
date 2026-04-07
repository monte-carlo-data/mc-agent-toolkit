#!/usr/bin/env python3
"""Handler for /mc-validate slash command (Claude Code adapter)."""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from lib.safe_run import safe_run
from lib.protocol import HookInput, evaluate_validate_command


@safe_run
def main():
    raw = json.load(sys.stdin)
    inp = HookInput(
        session_id=raw.get("session_id", "unknown"),
        validate_command="/mc-prevent:mc-validate",
    )
    result = evaluate_validate_command(inp)
    if result.action == "context":
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "additionalContext": result.context,
            }
        }))


if __name__ == "__main__":
    main()
