#!/usr/bin/env python3
"""PostToolUse hook (Cortex Code adapter): silently accumulates edited dbt model files.

For `apply_patch`, tracks the files of the operations the tool's result says may have
run, so a patch that failed before writing doesn't count as an edit. A file the patch
deleted, moved away or overwrote with plain SQL counts if the pre-edit hook saw it as a
dbt model before the patch ran; that hook records them per tool call.
"""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from lib.safe_run import safe_run
from lib.apply_patch import track_patch
from lib.protocol import HookInput, evaluate_post_edit
from patch_result import applied_operations


@safe_run
def main():
    raw = json.load(sys.stdin)
    session_id = raw.get("session_id", "unknown")
    if raw.get("tool_name") == "apply_patch":
        track_patch((raw.get("tool_input") or {}).get("input"), "cortex", cwd=raw.get("cwd"),
                    session_id=session_id, call_id=raw.get("tool_use_id"),
                    keep_ops=lambda ops: applied_operations(ops, raw.get("tool_response")))
        return
    evaluate_post_edit(HookInput(session_id=session_id, file_path=raw.get("tool_input", {}).get("file_path", "")))


if __name__ == "__main__":
    main()
