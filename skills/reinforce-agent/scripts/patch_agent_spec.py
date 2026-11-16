#!/usr/bin/env python3
"""
Apply a fix to a Cortex Agent specification without retyping it.

Snowflake's SET SPECIFICATION replaces the whole spec, so the new spec must carry every
field of the current one. Retyping a long spec by hand can silently change a tool
description or drop a tool resource. This script builds the new spec from the current one
and a small JSON Merge Patch (RFC 7396) holding only what the fix changes, then reports
every path that changed so the user approves the exact difference.

Merge patch rules: an object merges key by key, `null` deletes a key, and any other value
(including an array) replaces the old value whole.

Usage:
    python3 patch_agent_spec.py --spec current.json --patch fix.json --out new.json

Prints a JSON report to stdout:
    {"changed": [{"path": "instructions.orchestration", "before": null, "after": "..."}],
     "out": "new.json"}

Exits 1 when the inputs aren't JSON objects, 2 when the patch changes nothing.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_MISSING = object()


def merge_patch(target: Any, patch: Any) -> Any:
    """RFC 7396 JSON Merge Patch."""
    if not isinstance(patch, dict):
        return patch
    result = dict(target) if isinstance(target, dict) else {}
    for key, value in patch.items():
        if value is None:
            result.pop(key, None)
        else:
            result[key] = merge_patch(result.get(key), value)
    return result


def changed_paths(before: Any, after: Any, prefix: str = "") -> list[dict[str, Any]]:
    """Every leaf path whose value differs, objects walked key by key."""
    if isinstance(before, dict) and isinstance(after, dict):
        changes: list[dict[str, Any]] = []
        for key in sorted(set(before) | set(after)):
            path = f"{prefix}.{key}" if prefix else key
            old = before.get(key, _MISSING)
            new = after.get(key, _MISSING)
            if old is _MISSING or new is _MISSING:
                changes.append(
                    {
                        "path": path,
                        "before": None if old is _MISSING else old,
                        "after": None if new is _MISSING else new,
                    }
                )
            else:
                changes.extend(changed_paths(old, new, path))
        return changes
    if before == after:
        return []
    return [{"path": prefix or "(root)", "before": before, "after": after}]


def load_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as error:
        raise SystemExit(f"error: can't read the {label} as JSON: {error}") from None
    if not isinstance(value, dict):
        raise SystemExit(f"error: the {label} must be a JSON object")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--spec", required=True, type=Path, help="current spec, JSON")
    parser.add_argument("--patch", required=True, type=Path, help="JSON Merge Patch")
    parser.add_argument("--out", required=True, type=Path, help="where to write the new spec")
    args = parser.parse_args(argv)

    try:
        spec = load_object(args.spec, "spec")
        patch = load_object(args.patch, "patch")
    except SystemExit as error:
        print(error, file=sys.stderr)
        return 1

    new_spec = merge_patch(spec, patch)
    changes = changed_paths(spec, new_spec)
    if not changes:
        print("error: the patch changes nothing in the spec", file=sys.stderr)
        return 2

    args.out.write_text(json.dumps(new_spec, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"changed": changes, "out": str(args.out)}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
