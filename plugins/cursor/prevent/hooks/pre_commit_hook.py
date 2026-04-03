#!/usr/bin/env python3
"""beforeShellExecution hook (Cursor adapter): validation checkpoint before git commit."""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from lib.safe_run import safe_run
from lib.protocol import HookInput, evaluate_pre_commit


@safe_run
def main():
    raw = json.load(sys.stdin)
    inp = HookInput(
        session_id=raw.get("conversation_id", "unknown"),
        command=raw.get("command", ""),
        cwd=raw.get("cwd", "."),
    )
    result = evaluate_pre_commit(inp)
    if result.action == "context":
        print(json.dumps({
            "agent_message": result.context,
        }))


if __name__ == "__main__":
    main()
