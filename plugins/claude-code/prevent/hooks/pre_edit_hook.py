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
    import re
    # Anchor with \b after table_name so client_hub doesn't match client_hub_master
    ic_pattern = re.compile(rf"MC_IMPACT_CHECK_COMPLETE: {re.escape(table_name)}\b")
    mg_pattern = re.compile(rf"MC_MONITOR_GAP: {re.escape(table_name)}\b")
    found = {"impact_check": False, "monitor_gap": False}

    debug_log = os.environ.get("MC_PREVENT_DEBUG")
    if debug_log:
        print(f"[DEBUG] Scanning {transcript_path} for table={table_name}", file=sys.stderr)
        print(f"[DEBUG] ic_pattern={ic_pattern.pattern}", file=sys.stderr)

    try:
        with open(transcript_path, "r", encoding="utf-8") as f:
            line_num = 0
            for line in f:
                line_num += 1
                if ic_pattern.search(line):
                    found["impact_check"] = True
                    if debug_log:
                        print(f"[DEBUG] Found impact_check marker at line {line_num}", file=sys.stderr)
                if mg_pattern.search(line):
                    found["monitor_gap"] = True
                    if debug_log:
                        print(f"[DEBUG] Found monitor_gap marker at line {line_num}", file=sys.stderr)
    except (OSError, UnicodeDecodeError) as e:
        if debug_log:
            print(f"[DEBUG] Error reading transcript: {e}", file=sys.stderr)
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

    session_id = input_data.get("session_id", "unknown")
    table_name = extract_table_name(file_path)
    state = get_impact_check_state(session_id, table_name)

    # DEBUG: Log state for troubleshooting
    debug_log = os.environ.get("MC_PREVENT_DEBUG")
    if debug_log:
        print(f"[DEBUG] session={session_id}, table={table_name}, state={state}, file={file_path}", file=sys.stderr)

    if state == "verified":
        return

    if state == "injected":
        # Always check transcript for completion marker before allowing edit
        transcript_path = input_data.get("transcript_path", "")
        if debug_log:
            print(f"[DEBUG] transcript_path={transcript_path}", file=sys.stderr)
        markers = _scan_transcript_for_markers(transcript_path, table_name)
        if debug_log:
            print(f"[DEBUG] markers={markers}", file=sys.stderr)
        if markers["monitor_gap"] and not has_monitor_gap(session_id, table_name):
            mark_monitor_gap(session_id, table_name)
        if markers["impact_check"]:
            mark_impact_check_verified(session_id, table_name)
            return
        # Assessment not completed — block without re-injecting if within grace period
        age = get_impact_check_age_seconds(session_id, table_name)
        if age < GRACE_PERIOD_SECONDS:
            reason = (
                f"Monte Carlo Prevent: the impact assessment for {table_name} "
                f"has not completed yet. Complete the assessment before editing this file."
            )
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": reason,
                }
            }
            print(json.dumps(output))
            return
        # Grace period expired and no marker — re-inject full instruction below

    elif state is None:
        # Skill may have been invoked voluntarily before any edit (no prior hook injection).
        # Check the transcript for the marker before blocking to avoid a spurious re-trigger.
        transcript_path = input_data.get("transcript_path", "")
        if transcript_path:
            markers = _scan_transcript_for_markers(transcript_path, table_name)
            if markers["monitor_gap"] and not has_monitor_gap(session_id, table_name):
                mark_monitor_gap(session_id, table_name)
            if markers["impact_check"]:
                mark_impact_check_verified(session_id, table_name)
                return

    # No marker or failed verification — block the edit until impact assessment runs
    mark_impact_check_injected(session_id, table_name)

    hook_triggered_note = (
        "This assessment is hook-triggered — only emit MC_IMPACT_CHECK_COMPLETE "
        "markers for tables whose lineage and monitor coverage were fetched "
        "directly via Monte Carlo tools."
    )

    if table_name.startswith("macro:"):
        macro_name = table_name.removeprefix("macro:")
        reason = (
            f"Monte Carlo Prevent: this macro ({macro_name}) is inlined into "
            f"models at compile time — changes here affect every model that calls it. "
            f"Identify which models use this macro, then run the change impact "
            f"assessment for the affected models before editing this file. "
            f"{hook_triggered_note}"
        )
    else:
        reason = (
            f"Monte Carlo Prevent: run the change impact assessment "
            f"for {table_name} before editing this file. Present the full "
            f"impact report and synthesis step, then retry the edit. "
            f"{hook_triggered_note}"
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
