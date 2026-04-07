#!/usr/bin/env python3
"""Stop hook (Codex adapter): prompts for validation once per turn if dbt models were edited."""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from lib.safe_run import safe_run
from lib.protocol import HookInput, evaluate_turn_end


@safe_run
def main():
    raw = json.load(sys.stdin)
    inp = HookInput(
        session_id=raw.get("session_id", "unknown"),
        stop_hook_active=raw.get("stop_hook_active", False),
    )
    result = evaluate_turn_end(inp)
    if result.action == "block":
        print(json.dumps({"decision": "block", "reason": result.reason}))


if __name__ == "__main__":
    main()
