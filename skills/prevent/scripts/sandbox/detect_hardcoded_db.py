#!/usr/bin/env python3
"""
Detect a hard-coded `database='...'` kwarg inside a dbt model's `{{ config(...) }}` block.

Usage:
    python3 detect_hardcoded_db.py <model.sql>

Prints JSON: {"database": "<value>"} or {"database": null}
Exits 1 if the file is missing.
"""

import argparse
import json
import re
import sys
from pathlib import Path


_CONFIG_RE = re.compile(r"\{\{\s*config\s*\((.*?)\)\s*\}\}", re.DOTALL)
_DB_KWARG_RE = re.compile(r"""\bdatabase\s*=\s*(['"])([^'"]+)\1""")


def detect(content: str) -> str | None:
    for config_match in _CONFIG_RE.finditer(content):
        kwargs = config_match.group(1)
        db_match = _DB_KWARG_RE.search(kwargs)
        if db_match:
            return db_match.group(2)
    return None


def main() -> int:
    p = argparse.ArgumentParser(
        description="Detect a hard-coded database='...' in a dbt model's config() block."
    )
    p.add_argument("path", type=Path, help="Path to the dbt model .sql file")
    args = p.parse_args()
    if not args.path.exists():
        print(f"error: file not found: {args.path}", file=sys.stderr)
        return 1
    result = detect(args.path.read_text())
    print(json.dumps({"database": result}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
