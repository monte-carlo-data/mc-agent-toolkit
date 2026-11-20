#!/usr/bin/env python3
"""PostToolUse hook (Cortex Code adapter): silently accumulates edited dbt model files.

For CoCo Desktop's `apply_patch`, tracks the files of the operations the tool's result
says may have run, so a patch that failed before writing doesn't count as an edit.
"""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from lib.safe_run import safe_run
from lib.protocol import HookInput, evaluate_post_edit
from apply_patch import applied_operations, op_paths, parse_operations, resolve_path


def _patch_paths(raw: dict) -> list[str]:
    tool_input = raw.get("tool_input") or {}
    ops = applied_operations(parse_operations(tool_input.get("input")), raw.get("tool_response"))
    return [resolve_path(p, raw.get("cwd")) for p in op_paths(ops)]


@safe_run
def main():
    raw = json.load(sys.stdin)
    session_id = raw.get("session_id", "unknown")
    if raw.get("tool_name") == "apply_patch":
        paths = _patch_paths(raw)
    else:
        paths = [raw.get("tool_input", {}).get("file_path", "")]
    for path in paths:
        evaluate_post_edit(HookInput(session_id=session_id, file_path=path))


if __name__ == "__main__":
    main()
