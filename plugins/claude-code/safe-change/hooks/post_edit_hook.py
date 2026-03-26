#!/usr/bin/env python3
"""PostToolUse hook: silently accumulates edited dbt model files per turn."""
import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from lib.safe_run import safe_run
from lib.detect import is_dbt_model, is_dbt_schema_file, extract_table_name
from lib.cache import add_edited_table


@safe_run
def main():
    input_data = json.load(sys.stdin)
    tool_input = input_data.get("tool_input", {})
    file_path = tool_input.get("file_path", "")

    if not is_dbt_model(file_path) and not is_dbt_schema_file(file_path):
        return

    session_id = input_data.get("session_id", "unknown")
    table_name = extract_table_name(file_path)
    add_edited_table(session_id, table_name)


if __name__ == "__main__":
    main()
