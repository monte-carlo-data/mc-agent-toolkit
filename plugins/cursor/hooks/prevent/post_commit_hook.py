#!/usr/bin/env python3
"""postToolUse/Shell hook (Cursor adapter): offer a Bayes follow-up after a commit."""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from lib.safe_run import safe_run
from lib.protocol import HookInput, evaluate_post_commit


@safe_run
def main():
    raw = json.load(sys.stdin)
    inp = HookInput(
        session_id=raw.get("conversation_id", "unknown"),
        command=(raw.get("tool_input") or {}).get("command", ""),
    )
    result = evaluate_post_commit(inp)
    if result.action == "context":
        print(json.dumps({"additional_context": result.context}))


if __name__ == "__main__":
    main()
