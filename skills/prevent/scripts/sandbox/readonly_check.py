#!/usr/bin/env python3
"""
Verify a .sql file contains only read-only statements.

Usage:
    python3 readonly_check.py <path.sql>

Exit 0 with {"ok": true, "rejected": null} if safe.
Exit 1 with {"ok": false, "rejected": "<KEYWORD>"} if not.

Rejects any write-like keyword: INSERT, UPDATE, DELETE, MERGE, CREATE, DROP,
TRUNCATE, ALTER, COPY, PUT, GET, LIST, REMOVE, UNLOAD, GRANT, REVOKE, CALL,
EXECUTE, USE, SET.

Multi-statement files (several SELECTs separated by `;`) are accepted —
the keyword scan catches a rogue write statement regardless of how many
statements share the file. The caller is expected to split statements in
memory and send them to the warehouse one at a time.
"""

import argparse
import json
import re
import sys
from pathlib import Path


REJECTED_KEYWORDS = [
    # Most-specific first: MERGE before UPDATE so "MERGE ... UPDATE SET" reports MERGE.
    "INSERT", "DELETE", "MERGE", "UPDATE", "CREATE", "DROP", "TRUNCATE",
    "ALTER", "COPY", "PUT", "GET", "LIST", "REMOVE", "UNLOAD",
    "GRANT", "REVOKE", "CALL", "EXECUTE", "USE", "SET",
]

_LINE_COMMENT_RE = re.compile(r"--[^\n]*")
_BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)


def _strip_sql(src: str) -> str:
    """Remove comments and string literals so keyword scan is false-positive-free."""
    no_block = _BLOCK_COMMENT_RE.sub(" ", src)
    no_line = _LINE_COMMENT_RE.sub(" ", no_block)
    no_strings = re.sub(r"'(?:[^'\\]|\\.)*'", "''", no_line)
    no_strings = re.sub(r'"(?:[^"\\]|\\.)*"', '""', no_strings)
    return no_strings


def check(sql: str) -> tuple[bool, str | None]:
    cleaned = _strip_sql(sql)
    upper = cleaned.upper()
    for kw in REJECTED_KEYWORDS:
        if re.search(rf"\b{kw}\b", upper):
            return False, kw
    return True, None


def main() -> int:
    p = argparse.ArgumentParser(
        description="Verify a .sql file contains only read-only statements."
    )
    p.add_argument("path", type=Path, help="Path to the .sql file to check")
    args = p.parse_args()
    if not args.path.exists():
        print(f"error: file not found: {args.path}", file=sys.stderr)
        return 1
    ok, rejected = check(args.path.read_text())
    print(json.dumps({"ok": ok, "rejected": rejected}))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
