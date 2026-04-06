"""Platform-agnostic hook decision logic.

All business logic for the prevent hooks lives here.
Platform adapters (Claude Code, Cursor) call these functions
and translate the result to their platform's JSON format.
"""
import json
import os
import re
import subprocess

from lib.cache import (
    add_edited_table,
    cleanup_stale_cache,
    get_edited_tables,
    get_impact_check_age_seconds,
    get_impact_check_state,
    get_pending_validation_tables,
    has_monitor_gap,
    mark_impact_check_injected,
    mark_impact_check_verified,
    mark_monitor_gap,
    move_to_pending_validation,
)
from lib.detect import extract_table_name, is_dbt_model, is_dbt_schema_file


# --- Data types ---

class HookInput:
    """Platform-agnostic hook input."""

    __slots__ = ("session_id", "file_path", "command", "transcript_path",
                 "cwd", "tool_name", "stop_hook_active")

    def __init__(
        self,
        session_id: str,
        file_path: str | None = None,
        command: str | None = None,
        transcript_path: str | None = None,
        cwd: str | None = None,
        tool_name: str | None = None,
        stop_hook_active: bool = False,
    ):
        self.session_id = session_id
        self.file_path = file_path
        self.command = command
        self.transcript_path = transcript_path
        self.cwd = cwd
        self.tool_name = tool_name
        self.stop_hook_active = stop_hook_active


class HookOutput:
    """Platform-agnostic hook decision."""

    __slots__ = ("action", "reason", "context")

    def __init__(
        self,
        action: str = "noop",
        reason: str | None = None,
        context: str | None = None,
    ):
        self.action = action      # "deny", "context", "block", "noop"
        self.reason = reason
        self.context = context


# --- Shared helpers ---

GRACE_PERIOD_SECONDS = 120


def scan_transcript_for_markers(transcript_path: str, table_name: str) -> dict:
    """Scan transcript for MC_IMPACT_CHECK_COMPLETE and MC_MONITOR_GAP markers."""
    ic_pattern = re.compile(rf"MC_IMPACT_CHECK_COMPLETE: {re.escape(table_name)}\b")
    mg_pattern = re.compile(rf"MC_MONITOR_GAP: {re.escape(table_name)}\b")
    found = {"impact_check": False, "monitor_gap": False}
    try:
        with open(transcript_path, "r", encoding="utf-8") as f:
            for line in f:
                if ic_pattern.search(line):
                    found["impact_check"] = True
                if mg_pattern.search(line):
                    found["monitor_gap"] = True
    except (OSError, UnicodeDecodeError):
        pass
    return found


def _get_staged_model_tables(cwd: str) -> list[str]:
    """Get table names from staged dbt SQL files using the detect library."""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True, text=True, cwd=cwd, timeout=10,
        )
        tables = []
        for line in result.stdout.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            full_path = os.path.join(cwd, line)
            if is_dbt_model(full_path):
                tables.append(extract_table_name(full_path))
        return tables
    except (subprocess.SubprocessError, OSError):
        return []


# --- Decision functions ---

def evaluate_pre_edit(inp: HookInput) -> HookOutput:
    """Gate logic: should this file edit be allowed?

    Returns deny if impact assessment hasn't run for this table,
    noop if the edit should proceed.
    """
    cleanup_stale_cache()

    file_path = inp.file_path or ""
    if not is_dbt_model(file_path):
        return HookOutput()

    # New models have no blast radius — don't block
    if not os.path.exists(file_path):
        return HookOutput()

    session_id = inp.session_id
    table_name = extract_table_name(file_path)
    state = get_impact_check_state(session_id, table_name)

    if state == "verified":
        return HookOutput()

    if state == "injected":
        transcript_path = inp.transcript_path or ""
        markers = scan_transcript_for_markers(transcript_path, table_name)
        if markers["monitor_gap"] and not has_monitor_gap(session_id, table_name):
            mark_monitor_gap(session_id, table_name)
        if markers["impact_check"]:
            mark_impact_check_verified(session_id, table_name)
            return HookOutput()
        # Assessment not completed — block without re-injecting if within grace period
        age = get_impact_check_age_seconds(session_id, table_name)
        if age < GRACE_PERIOD_SECONDS:
            reason = (
                f"Monte Carlo Prevent: the impact assessment for {table_name} "
                f"has not completed yet. Complete the assessment before editing this file."
            )
            return HookOutput(action="deny", reason=reason)
        # Grace period expired and no marker — re-inject full instruction below

    elif state is None:
        transcript_path = inp.transcript_path or ""
        if transcript_path:
            markers = scan_transcript_for_markers(transcript_path, table_name)
            if markers["monitor_gap"] and not has_monitor_gap(session_id, table_name):
                mark_monitor_gap(session_id, table_name)
            if markers["impact_check"]:
                mark_impact_check_verified(session_id, table_name)
                return HookOutput()

    # No marker or failed verification — block the edit
    mark_impact_check_injected(session_id, table_name)

    hook_triggered_note = (
        "This assessment is hook-triggered — only emit MC_IMPACT_CHECK_COMPLETE "
        "markers for tables whose lineage and monitor coverage were fetched "
        "directly via Monte Carlo tools."
    )

    no_bypass_note = (
        "IMPORTANT: Do NOT bypass this check by using shell commands, git apply, "
        "or any other workaround. If Monte Carlo MCP tools are not available in "
        "this session, ask the user to authenticate the Monte Carlo MCP server "
        "in their editor settings before proceeding."
    )

    if table_name.startswith("macro:"):
        macro_name = table_name.removeprefix("macro:")
        reason = (
            f"Monte Carlo Prevent: this macro ({macro_name}) is inlined into "
            f"models at compile time — changes here affect every model that calls it. "
            f"Identify which models use this macro, then run the change impact "
            f"assessment for the affected models before editing this file. "
            f"{hook_triggered_note} {no_bypass_note}"
        )
    else:
        reason = (
            f"Monte Carlo Prevent: run the change impact assessment "
            f"for {table_name} before editing this file. Present the full "
            f"impact report and synthesis step, then ask the user whether to proceed before retrying the edit. "
            f"{hook_triggered_note} {no_bypass_note}"
        )

    return HookOutput(action="deny", reason=reason)


def evaluate_post_edit(inp: HookInput) -> HookOutput:
    """Track which tables were edited. Always returns noop (silent)."""
    file_path = inp.file_path or ""
    if not is_dbt_model(file_path) and not is_dbt_schema_file(file_path):
        return HookOutput()

    table_name = extract_table_name(file_path)
    add_edited_table(inp.session_id, table_name)
    return HookOutput()


def evaluate_pre_commit(inp: HookInput) -> HookOutput:
    """Commit checkpoint: prompt for validation if dbt models are staged."""
    command = inp.command or ""
    if "git commit" not in command:
        return HookOutput()

    cwd = inp.cwd or "."
    staged_tables = _get_staged_model_tables(cwd)
    if not staged_tables:
        return HookOutput()

    w4_tables = [t for t in staged_tables
                 if get_impact_check_state(inp.session_id, t) == "verified"]
    if not w4_tables:
        return HookOutput()

    table_list = ", ".join(w4_tables)
    gap_tables = [t for t in w4_tables if has_monitor_gap(inp.session_id, t)]

    message = (
        f"Committing changes to {table_list}. "
        f"Run validation queries before committing? (yes / no)"
    )
    if gap_tables:
        gap_list = ", ".join(gap_tables)
        message += (
            f"\n\nMonitor coverage: the impact assessment found no custom monitors "
            f"on {gap_list}. Generate monitor definitions before committing? (yes / no)"
        )

    return HookOutput(action="context", context=message)


def evaluate_turn_end(inp: HookInput) -> HookOutput:
    """End of turn: prompt for validation queries if dbt models were edited."""
    if inp.stop_hook_active:
        return HookOutput()

    session_id = inp.session_id
    tables = get_edited_tables(session_id)
    if not tables:
        return HookOutput()

    if get_pending_validation_tables(session_id):
        move_to_pending_validation(session_id)
        return HookOutput()

    w4_tables = [t for t in tables
                 if get_impact_check_state(session_id, t) in ("injected", "verified")]
    if not w4_tables:
        return HookOutput()

    gap_tables = [t for t in tables if has_monitor_gap(session_id, t)]

    table_list = ", ".join(tables)
    count = len(tables)
    reason = (
        f"You've changed {count} dbt model(s): {table_list}. "
        f"ASK THE USER whether they would like to run validation queries to "
        f"verify these changes behaved as intended. Present these options and "
        f"WAIT for the user to respond — do NOT answer on their behalf:\n\n"
        f"→ Yes: I'll generate and run queries for all changed models\n"
        f"→ No: You can use /mc-validate anytime to validate changes"
    )
    if gap_tables:
        gap_list = ", ".join(gap_tables)
        reason += (
            f"\n\nAlso ask about monitor coverage: the impact assessment found no "
            f"custom monitors on {gap_list}. Ask the user whether they would like "
            f"to generate monitor definitions:\n\n"
            f"→ Yes: I'll suggest monitors for the new or changed logic\n"
            f"→ No: Skip for now"
        )

    move_to_pending_validation(session_id)
    return HookOutput(action="block", reason=reason)


def evaluate_validate_command(inp: HookInput) -> HookOutput:
    """Handle /mc-validate slash command."""
    session_id = inp.session_id

    tables = get_pending_validation_tables(session_id)
    if not tables:
        tables = get_edited_tables(session_id)

    if not tables:
        return HookOutput(
            action="context",
            context="No dbt model changes detected in this session. Edit a dbt model first, then run /mc-validate.",
        )

    w4_tables = [t for t in tables
                 if get_impact_check_state(session_id, t) == "verified"]
    if not w4_tables:
        w4_tables = tables

    table_list = ", ".join(w4_tables)
    return HookOutput(
        action="context",
        context=(
            f"Generate validation queries for: {table_list}. "
            f"Use the validation query workflow from the Monte Carlo Prevent skill. "
            f"Save queries to validation/<table_name>_<timestamp>.sql."
        ),
    )
