#!/usr/bin/env python3
"""postToolUse hook (Copilot CLI adapter): silently accumulates edited dbt model files."""
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.safe_run import safe_run
from lib.protocol import HookInput, evaluate_post_edit


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
    )
    evaluate_post_edit(inp)


if __name__ == "__main__":
    main()
