#!/usr/bin/env python3
"""preToolUse hook (Copilot CLI adapter): gate ensuring impact assessment runs before editing dbt SQL."""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lib.safe_run import safe_run
from lib.protocol import HookInput, evaluate_pre_edit


@safe_run
def main():
    raw = json.load(sys.stdin)
    tool_name = raw.get("toolName", "")
    if tool_name not in ("edit", "create"):
        sys.exit(0)
    tool_args = json.loads(raw.get("toolArgs", "{}"))
    file_path = tool_args.get("file_path", tool_args.get("path", ""))
    inp = HookInput(
        session_id=str(os.getpid()),
        file_path=file_path,
        transcript_path="",
    )
    result = evaluate_pre_edit(inp)
    if result.action == "deny":
        print(json.dumps({
            "permissionDecision": "deny",
            "permissionDecisionReason": result.reason,
        }))


if __name__ == "__main__":
    main()
