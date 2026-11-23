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
from lib.apply_patch import op_paths, parse_operations, patched_tables, recall_existing_models, resolve_path
from lib.cache import add_edited_table
from lib.protocol import HookInput, evaluate_post_edit
from apply_patch import applied_operations


def _track_patch(raw: dict, session_id: str) -> None:
    tool_input = raw.get("tool_input") or {}
    were_models = recall_existing_models(session_id, raw.get("tool_use_id"))
    ops = applied_operations(parse_operations(tool_input.get("input")), raw.get("tool_response"))
    paths = [resolve_path(p, raw.get("cwd")) for p in op_paths(ops)]
    for table in patched_tables(paths, were_models):
        add_edited_table(session_id, table)


@safe_run
def main():
    raw = json.load(sys.stdin)
    session_id = raw.get("session_id", "unknown")
    if raw.get("tool_name") == "apply_patch":
        _track_patch(raw, session_id)
        return
    evaluate_post_edit(HookInput(session_id=session_id, file_path=raw.get("tool_input", {}).get("file_path", "")))


if __name__ == "__main__":
    main()
