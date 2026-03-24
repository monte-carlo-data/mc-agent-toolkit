#!/usr/bin/env python3
"""PreToolUse (Bash) hook: validation checkpoint before git commit."""
import json
import subprocess
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from lib.safe_run import safe_run
from lib.cache import get_impact_check_state


def _get_staged_model_tables(cwd: str) -> list[str]:
    """Get table names from staged .sql files under models/."""
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
            if "/models/" in line and line.endswith(".sql"):
                name = os.path.splitext(os.path.basename(line))[0]
                tables.append(name)
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
    message = f"Committing changes to {table_list}. Run validation queries before committing? (yes / no)"

    # Monitor coverage reminder: The spec says to include a passive nudge
    # ("impact assessment found no monitor coverage...") when W4 found a gap and
    # the engineer declined the offer. In Phase 1, the hook has no reliable
    # way to detect this from cache alone (the gap info lives in the
    # transcript/conversation context, not in temp files). Deferred until
    # we add transcript scanning for monitor coverage state.

    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": message,
        }
    }
    print(json.dumps(output))


if __name__ == "__main__":
    main()
