#!/usr/bin/env python3
"""Handler for /mc-validate slash command."""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from lib.safe_run import safe_run
from lib.cache import (
    get_pending_validation_tables,
    get_edited_tables,
    get_workflow4_state,
)


@safe_run
def main():
    input_data = json.load(sys.stdin)
    session_id = input_data.get("session_id", "unknown")

    # Check pending validation first, then current turn
    tables = get_pending_validation_tables(session_id)
    if not tables:
        tables = get_edited_tables(session_id)

    if not tables:
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "additionalContext": "No dbt model changes detected in this session. Edit a dbt model first, then run /mc-validate.",
            }
        }
        print(json.dumps(output))
        return

    # Filter to tables that had Workflow 4
    w4_tables = [t for t in tables if get_workflow4_state(t) == "verified"]
    if not w4_tables:
        w4_tables = tables  # Fall back to all tables if no W4 tracking

    table_list = ", ".join(w4_tables)
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": (
                f"Generate validation queries for: {table_list}. "
                f"Use Workflow 5 from the Monte Carlo safe-change skill. "
                f"Save queries to validation/<table_name>_<timestamp>.sql."
            ),
        }
    }
    print(json.dumps(output))


if __name__ == "__main__":
    main()
