#!/usr/bin/env python3
"""
Parse a dbt profiles.yml and emit the active target's resolved context.

Usage:
    python3 parse_profiles.py <profiles.yml path> [--profile <name>] [--target <name>]

On success prints JSON:
    {
      "profile": "default",
      "target_name": "prod",
      "database": "personal_alice",
      "schema": "prod",
      "role": "DATA_ANALYST",
      "warehouse": "research",
      "account": "dka87615.us-east-1"
    }

On error: exits 1 with a human message on stderr; stdout is empty.
"""

import argparse
import json
import sys
from pathlib import Path

try:
    import yaml  # type: ignore
except ImportError:
    print("error: pyyaml not installed; run `pip3 install pyyaml`", file=sys.stderr)
    sys.exit(1)


def _select_profile(doc: dict, name: str | None) -> tuple[str, dict]:
    """Return (profile_name, profile_doc).

    If *name* is given it must match a top-level profile key; otherwise
    the first profile in the file is selected.
    """
    if not isinstance(doc, dict) or not doc:
        raise ValueError("profiles.yml has no profiles defined")
    first = next(iter(doc))
    if name:
        if name in doc:
            return name, doc[name]
        raise ValueError(f"profile '{name}' not found in profiles.yml")
    return first, doc[first]


def _select_target(profile: dict, target: str | None) -> tuple[str, dict]:
    outputs = profile.get("outputs") or {}
    if not outputs:
        raise ValueError("profile has no 'outputs' defined")
    target_name = target or profile.get("target")
    if not target_name:
        raise ValueError("profile has no 'target' and --target not given")
    if target_name not in outputs:
        raise ValueError(f"target '{target_name}' not defined in profile outputs")
    return target_name, outputs[target_name]


def parse(profiles_path: Path, profile: str | None, target: str | None) -> dict:
    if not profiles_path.exists():
        raise FileNotFoundError(f"profiles.yml not found: {profiles_path}")
    try:
        raw = yaml.safe_load(profiles_path.read_text())
    except yaml.YAMLError as exc:
        raise ValueError(f"could not parse yaml: {exc}") from exc
    profile_name, profile_doc = _select_profile(raw, profile)
    target_name, target_doc = _select_target(profile_doc, target)
    return {
        "profile": profile_name,
        "target_name": target_name,
        "database": target_doc.get("database"),
        "schema": target_doc.get("schema"),
        "role": target_doc.get("role"),
        "warehouse": target_doc.get("warehouse"),
        "account": target_doc.get("account"),
    }


def main() -> int:
    p = argparse.ArgumentParser(
        description="Parse a dbt profiles.yml and emit the active target's resolved context as JSON."
    )
    p.add_argument("profiles_path", type=Path, help="Path to profiles.yml")
    p.add_argument("--profile", default=None, help="Profile name (default: first profile in file)")
    p.add_argument("--target", default=None, help="Target name (default: profile's 'target' field)")
    args = p.parse_args()
    try:
        result = parse(args.profiles_path, args.profile, args.target)
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
