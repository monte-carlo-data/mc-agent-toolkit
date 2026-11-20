#!/usr/bin/env python3
"""PostToolUse hook (Cortex Code adapter): silently accumulates edited dbt model files.

For `apply_patch`, tracks the files of the operations the tool's result says may have
run, so a patch that failed before writing doesn't count as an edit. A file the patch
deleted or moved away is tracked only if the pre-edit gate saw it as a dbt model: once it
is gone, the classifier can no longer tell a model from any other `.sql` file.
"""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from lib.safe_run import safe_run
from lib.cache import get_impact_check_state
from lib.detect import extract_table_name
from lib.protocol import HookInput, evaluate_post_edit
from apply_patch import applied_operations, op_paths, parse_operations, resolve_path


def _patch_paths(raw: dict, session_id: str) -> list[str]:
    tool_input = raw.get("tool_input") or {}
    ops = applied_operations(parse_operations(tool_input.get("input")), raw.get("tool_response"))
    paths = [resolve_path(p, raw.get("cwd")) for p in op_paths(ops)]
    return [p for p in paths
            if os.path.exists(p) or get_impact_check_state(session_id, extract_table_name(p))]


@safe_run
def main():
    raw = json.load(sys.stdin)
    session_id = raw.get("session_id", "unknown")
    if raw.get("tool_name") == "apply_patch":
        paths = _patch_paths(raw, session_id)
    else:
        paths = [raw.get("tool_input", {}).get("file_path", "")]
    for path in paths:
        evaluate_post_edit(HookInput(session_id=session_id, file_path=path))


if __name__ == "__main__":
    main()
