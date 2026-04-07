#!/usr/bin/env python3
"""agentStop hook (Copilot CLI adapter): updates cache state when dbt models were edited.

Note: Copilot CLI ignores agentStop output — this hook performs side effects only
(moving edited tables from turn cache to pending validation).
"""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lib.safe_run import safe_run
from lib.protocol import HookInput, evaluate_turn_end


@safe_run
def main():
    raw = json.load(sys.stdin)
    inp = HookInput(
        session_id=str(os.getpid()),
        stop_hook_active=False,
    )
    evaluate_turn_end(inp)


if __name__ == "__main__":
    main()
