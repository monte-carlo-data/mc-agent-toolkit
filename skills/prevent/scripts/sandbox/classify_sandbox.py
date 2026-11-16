#!/usr/bin/env python3
"""
Classify a database name as personal / dev / shared-dev / prod / unknown.

Usage:
    python3 classify_sandbox.py <database_name>

Prints JSON: {"database": "<name>", "classification": "<label>"}
Exits 0 always; caller decides how to handle 'prod' / 'unknown'.

Rules (uppercase-insensitive):
    personal    -> starts with PERSONAL_
    dev         -> starts with DEV_ / SANDBOX_ / ends with _DEV
    shared-dev  -> starts with DBT_
    prod        -> exact match of any of: ANALYTICS, RAW, INGEST, MONTECARLODATA_SHARED
    unknown     -> everything else (empty string included)
"""

import argparse
import json
import sys

PROD_NAMES = {"ANALYTICS", "RAW", "INGEST", "MONTECARLODATA_SHARED"}


def classify(database: str) -> str:
    if not database:
        return "unknown"
    name = database.upper()
    if name in PROD_NAMES:
        return "prod"
    if name.startswith("PERSONAL_"):
        return "personal"
    if name.startswith("DEV_") or name.startswith("SANDBOX_") or name.endswith("_DEV"):
        return "dev"
    if name.startswith("DBT_"):
        return "shared-dev"
    return "unknown"


def main() -> int:
    p = argparse.ArgumentParser(
        description="Classify a database name as personal / dev / shared-dev / prod / unknown."
    )
    p.add_argument("database", help="Database name to classify")
    args = p.parse_args()
    print(json.dumps({"database": args.database, "classification": classify(args.database)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
