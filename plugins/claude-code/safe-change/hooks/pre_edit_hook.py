#!/usr/bin/env python3
"""PreToolUse hook: once-per-table gate ensuring impact assessment runs before editing a dbt model."""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from lib.safe_run import safe_run
from lib.detect import is_dbt_model, extract_table_name
from lib.cache import (
    get_impact_check_state,
    mark_impact_check_injected,
    mark_impact_check_verified,
    get_impact_check_age_seconds,
)

GRACE_PERIOD_SECONDS = 120


def _scan_transcript_for_marker(transcript_path: str, table_name: str) -> bool:
    """Scan transcript for MC_IMPACT_CHECK_COMPLETE marker."""
    marker = f"MC_IMPACT_CHECK_COMPLETE: {table_name}"
    try:
        with open(transcript_path, "r", encoding="utf-8") as f:
            for line in f:
                if marker in line:
                    return True
    except (OSError, UnicodeDecodeError):
        pass
    return False


@safe_run
def main():
    input_data = json.load(sys.stdin)
    tool_input = input_data.get("tool_input", {})
    file_path = tool_input.get("file_path", "")

    if not is_dbt_model(file_path):
        return

    # New models have no blast radius — don't block, let SKILL.md handle Workflow 1
    if not os.path.exists(file_path):
        return

    table_name = extract_table_name(file_path)
    state = get_impact_check_state(table_name)

    if state == "verified":
        return

    if state == "injected":
        age = get_impact_check_age_seconds(table_name)
        if age < GRACE_PERIOD_SECONDS:
            return
        # Grace period expired — verify via transcript
        transcript_path = input_data.get("transcript_path", "")
        if _scan_transcript_for_marker(transcript_path, table_name):
            mark_impact_check_verified(table_name)
            return
        # Not found in transcript — re-inject (marker will be overwritten below)

    # No marker or failed verification — block the edit until impact assessment runs
    mark_impact_check_injected(table_name)
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": (
                f"BLOCKED: Before editing this file, run Workflow 4 "
                f"(change impact assessment) as defined in the Monte Carlo safe-change "
                f"skill for the table {table_name}. Present the full impact report and "
                f"synthesis step before making any edits. Then retry the edit."
            ),
        }
    }
    print(json.dumps(output))


if __name__ == "__main__":
    main()
