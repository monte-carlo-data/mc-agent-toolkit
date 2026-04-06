#!/usr/bin/env python3
"""preToolUse hook (Cursor adapter): gate ensuring impact assessment runs before editing dbt SQL."""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from lib.safe_run import safe_run
from lib.protocol import HookInput, evaluate_pre_edit


@safe_run
def main():
    raw = json.load(sys.stdin)
    inp = HookInput(
        session_id=raw.get("conversation_id", "unknown"),
        file_path=raw.get("tool_input", {}).get("file_path", ""),
        transcript_path=raw.get("transcript_path", ""),
    )
    result = evaluate_pre_edit(inp)
    if result.action == "deny":
        print(json.dumps({
            "permission": "deny",
            "user_message": result.reason,
        }))


if __name__ == "__main__":
    main()
