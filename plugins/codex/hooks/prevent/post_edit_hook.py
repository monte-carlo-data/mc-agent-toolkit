#!/usr/bin/env python3
"""PostToolUse hook (Codex adapter): silently accumulates edited dbt model files.

Codex 0.124.0+ sends PostToolUse for its `apply_patch` tool, only after the patch
succeeded; `tool_input.command` is the patch. A file the patch deleted, moved away or
overwrote with plain SQL counts if bash_hook.py saw it as a dbt model before the patch
ran; that hook records them per tool call. Other payloads are tracked by `file_path`.
"""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from lib.safe_run import safe_run
from lib.apply_patch import op_paths, parse_operations, patched_tables, recall_existing_models, resolve_path
from lib.cache import add_edited_table
from lib.protocol import HookInput, evaluate_post_edit


def _track_patch(raw: dict, session_id: str) -> None:
    were_models = recall_existing_models(session_id, raw.get("tool_use_id"))
    ops = parse_operations((raw.get("tool_input") or {}).get("command"), "codex")
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
