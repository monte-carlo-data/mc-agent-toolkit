#!/usr/bin/env python3
"""PreToolUse hook: once-per-table gate ensuring impact assessment runs before editing dbt SQL."""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from lib.safe_run import safe_run
from lib.detect import is_dbt_model, extract_table_name
from lib.cache import (
    cleanup_stale_cache,
    get_impact_check_state,
    mark_impact_check_injected,
    mark_impact_check_verified,
    get_impact_check_age_seconds,
    has_monitor_gap,
    mark_monitor_gap,
)

GRACE_PERIOD_SECONDS = 120


def _scan_transcript_for_markers(transcript_path: str, table_name: str) -> dict:
    """Scan transcript for MC_IMPACT_CHECK_COMPLETE and MC_MONITOR_GAP markers."""
    ic_marker = f"MC_IMPACT_CHECK_COMPLETE: {table_name}"
    mg_marker = f"MC_MONITOR_GAP: {table_name}"
    found = {"impact_check": False, "monitor_gap": False}
    try:
        with open(transcript_path, "r", encoding="utf-8") as f:
            for line in f:
                if ic_marker in line:
                    found["impact_check"] = True
                if mg_marker in line:
                    found["monitor_gap"] = True
    except (OSError, UnicodeDecodeError):
        pass
    return found


@safe_run
def main():
    cleanup_stale_cache()

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
        markers = _scan_transcript_for_markers(transcript_path, table_name)
        if markers["monitor_gap"] and not has_monitor_gap(table_name):
            mark_monitor_gap(table_name)
        if markers["impact_check"]:
            mark_impact_check_verified(table_name)
            return
        # Not found in transcript — re-inject (marker will be overwritten below)

    # No marker or failed verification — block the edit until impact assessment runs
    mark_impact_check_injected(table_name)

    if table_name.startswith("macro:"):
        macro_name = table_name.removeprefix("macro:")
        reason = (
            f"Monte Carlo safe-change: this macro ({macro_name}) is inlined into "
            f"models at compile time — changes here affect every model that calls it. "
            f"Identify which models use this macro, then run the change impact "
            f"assessment for the affected models before editing this file."
        )
    else:
        reason = (
            f"Monte Carlo safe-change: run the change impact assessment "
            f"for {table_name} before editing this file. Present the full "
            f"impact report and synthesis step, then retry the edit."
        )

    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }
    print(json.dumps(output))


if __name__ == "__main__":
    main()
