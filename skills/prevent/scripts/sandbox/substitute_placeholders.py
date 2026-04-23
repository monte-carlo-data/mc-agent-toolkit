#!/usr/bin/env python3
"""
Substitute <YOUR_DEV_DATABASE> in a validation .sql file with a confirmed dev database
and report any remaining literal fully-qualified database references.

Usage:
    python3 substitute_placeholders.py <path.sql> --dev-db <NAME> [--output <path>]

Writes the substituted SQL to `<input>.run.sql` by default (or `--output`) and prints JSON:
    {
      "output_path": "<path>",
      "dev_db": "<NAME>",
      "replaced_count": <int>,
      "literal_databases": ["analytics", ...]
    }

Exits 1 if the input file is missing.
"""

import argparse
import json
import re
import sys
from pathlib import Path


_PLACEHOLDER = "<YOUR_DEV_DATABASE>"

_FQ_RE = re.compile(
    r"\b([A-Za-z_][A-Za-z0-9_]*)\.[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*\b"
)
_LINE_COMMENT_RE = re.compile(r"--[^\n]*")
_BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)


def _strip_comments(sql: str) -> str:
    return _LINE_COMMENT_RE.sub(" ", _BLOCK_COMMENT_RE.sub(" ", sql))


def substitute(sql: str, dev_db: str) -> tuple[str, int]:
    count = sql.count(_PLACEHOLDER)
    return sql.replace(_PLACEHOLDER, dev_db), count


def find_literal_databases(sql: str, dev_db: str) -> list[str]:
    """Return distinct database names used in fully-qualified refs, excluding dev_db."""
    code_only = _strip_comments(sql)
    dbs = {m.group(1) for m in _FQ_RE.finditer(code_only)}
    dbs.discard(dev_db)
    return sorted(dbs)


def main() -> int:
    p = argparse.ArgumentParser(
        description=(
            "Substitute <YOUR_DEV_DATABASE> in a validation .sql file with a confirmed "
            "dev database; report any remaining literal fully-qualified database references."
        )
    )
    p.add_argument("path", type=Path, help="Path to the validation .sql file")
    p.add_argument("--dev-db", required=True, help="Dev database name to substitute in")
    p.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output path (default: <input_dir>/run/<input_stem>.run.sql)",
    )
    args = p.parse_args()
    if not args.path.exists():
        print(f"error: file not found: {args.path}", file=sys.stderr)
        return 1
    original = args.path.read_text()
    substituted, replaced_count = substitute(original, args.dev_db)
    literals = find_literal_databases(substituted, args.dev_db)
    if args.output is not None:
        out_path = args.output
    else:
        run_dir = args.path.parent / "run"
        run_dir.mkdir(parents=True, exist_ok=True)
        out_path = run_dir / (args.path.stem + ".run.sql")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(substituted)
    print(json.dumps({
        "output_path": str(out_path),
        "dev_db": args.dev_db,
        "replaced_count": replaced_count,
        "literal_databases": literals,
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
