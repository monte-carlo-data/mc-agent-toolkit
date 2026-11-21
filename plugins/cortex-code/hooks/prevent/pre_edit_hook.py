#!/usr/bin/env python3
"""PreToolUse hook (Cortex Code adapter): gate ensuring impact assessment runs before editing dbt SQL.

Cortex stores the session message log in a sibling `<id>.history.jsonl`, while the
hook's `transcript_path` points at the `<id>.json` session-metadata file. We rewrite
the path to the history sibling and tell the shared scanner to read it as Anthropic
Messages-style JSONL, matching markers only in assistant text blocks — never in
tool_result blocks, where Cortex persists this gate's own deny reason.

Cortex Code's `apply_patch` (given to GPT and OpenAI models) can touch several files in
one call. Every file is checked, so each gets its own assessment state, and the patch is
denied as a whole when any of them needs an assessment.
"""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from lib.safe_run import safe_run
from lib.detect import extract_table_name
from lib.protocol import HookInput, evaluate_pre_edit
from apply_patch import parse_operations, resolve_path


def _history_path(transcript_path: str) -> str:
    """Map Cortex's `<id>.json` metadata path to the sibling `<id>.history.jsonl`."""
    if transcript_path.endswith(".json"):
        return transcript_path[: -len(".json")] + ".history.jsonl"
    return transcript_path


def _deny(reason: str) -> None:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }))


def _hook_input(raw: dict, file_path: str) -> HookInput:
    return HookInput(
        session_id=raw.get("session_id", "unknown"),
        file_path=file_path,
        transcript_path=_history_path(raw.get("transcript_path", "")),
        transcript_format="messages_jsonl",
    )


def _patch_deny_reason(denied: dict[str, str], file_count: int, other_files: bool) -> str:
    """One reason for a denied patch: the tables, then each table's own instructions.

    Names tables bare (never after a marker token), so the reason can't unlock the gate
    when Cortex records it in the transcript.
    """
    if len(denied) == 1 and not other_files:
        return next(iter(denied.values()))
    names = ", ".join(denied)
    retry = (
        "Retry the patch after the assessment, or split out the changes to other files."
        if other_files else "Retry the patch after the assessment."
    )
    lead = (
        f"Monte Carlo Prevent: this patch touches {file_count} files. Run the change "
        f"impact assessment first for: {names}. The whole patch was blocked and no "
        f"file in it was changed. {retry}"
    )
    return "\n\n".join([lead, *denied.values()])


def _gate_patch(raw: dict) -> None:
    tool_input = raw.get("tool_input") or {}
    cwd = raw.get("cwd")
    ops = parse_operations(tool_input.get("input"))
    op_files = [[resolve_path(p, cwd) for p in (op.path, op.move_to) if p] for op in ops]

    denied: dict[str, str] = {}
    denied_paths: set[str] = set()
    checked: set[str] = set()
    for files in op_files:
        for path in files:
            if path in checked:
                continue
            checked.add(path)
            # One file's error must not drop denials already found for others.
            try:
                result = evaluate_pre_edit(_hook_input(raw, path))
                if result.action == "deny":
                    # Keep the first file's reason: it carries the assessment instructions
                    # and starts the grace period, so a later file of the same table only
                    # gets the short "not completed yet" text.
                    denied.setdefault(extract_table_name(path), result.reason)
                    denied_paths.add(path)
            except Exception:
                continue
    if denied:
        other_files = any(denied_paths.isdisjoint(files) for files in op_files)
        _deny(_patch_deny_reason(denied, len(checked), other_files))


@safe_run
def main():
    raw = json.load(sys.stdin)
    if raw.get("tool_name") == "apply_patch":
        _gate_patch(raw)
        return
    result = evaluate_pre_edit(_hook_input(raw, raw.get("tool_input", {}).get("file_path", "")))
    if result.action == "deny":
        _deny(result.reason)


if __name__ == "__main__":
    main()
