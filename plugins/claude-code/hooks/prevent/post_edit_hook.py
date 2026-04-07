#!/usr/bin/env python3
"""PostToolUse hook (Claude Code adapter): silently accumulates edited dbt model files."""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from lib.safe_run import safe_run
from lib.protocol import HookInput, evaluate_post_edit


@safe_run
def main():
    raw = json.load(sys.stdin)
    inp = HookInput(
        session_id=raw.get("session_id", "unknown"),
        file_path=raw.get("tool_input", {}).get("file_path", ""),
    )
    evaluate_post_edit(inp)


if __name__ == "__main__":
    main()
