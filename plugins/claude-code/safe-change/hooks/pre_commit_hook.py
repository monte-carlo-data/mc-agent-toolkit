#!/usr/bin/env python3
"""PreToolUse (Bash) hook: validation checkpoint before git commit."""
import json
import subprocess
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from lib.safe_run import safe_run
from lib.cache import get_impact_check_state, has_monitor_gap
from lib.detect import is_dbt_model, extract_table_name


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


@safe_run
def main():
    input_data = json.load(sys.stdin)
    tool_input = input_data.get("tool_input", {})
    command = tool_input.get("command", "")

    if "git commit" not in command:
        return

    cwd = input_data.get("cwd", ".")
    staged_tables = _get_staged_model_tables(cwd)

    if not staged_tables:
        return

    # Only prompt if impact assessment ran for at least one staged table
    w4_tables = [t for t in staged_tables if get_impact_check_state(t) == "verified"]
    if not w4_tables:
        return

    table_list = ", ".join(w4_tables)
    gap_tables = [t for t in w4_tables if has_monitor_gap(t)]

    message = f"Committing changes to {table_list}. Run validation queries before committing? (yes / no)"

    if gap_tables:
        gap_list = ", ".join(gap_tables)
        message += (
            f"\n\nMonitor coverage: the impact assessment found no custom monitors "
            f"on {gap_list}. Generate monitor definitions before committing? (yes / no)"
        )

    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": message,
        }
    }
    print(json.dumps(output))


if __name__ == "__main__":
    main()
