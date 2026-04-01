#!/bin/bash
set -e

echo "Running post-install cleanup for Monte Carlo Prevent plugin..."

# Remove standalone prevent skill if present (superseded by plugin)
SKILL_PATH="$HOME/.claude/skills/prevent"
if [ -d "$SKILL_PATH" ]; then
  echo "Backing up and removing standalone prevent skill (now bundled in plugin)..."
  cp -r "$SKILL_PATH" "$SKILL_PATH.backup"
  rm -rf "$SKILL_PATH"
  echo "Backup saved to $SKILL_PATH.backup"
fi

# Clean up old safe-change skill left from the pre-rename plugin
OLD_SKILL_PATH="$HOME/.claude/skills/safe-change"
if [ -d "$OLD_SKILL_PATH" ]; then
  echo "Removing old safe-change skill (renamed to prevent)..."
  cp -r "$OLD_SKILL_PATH" "$OLD_SKILL_PATH.backup"
  rm -rf "$OLD_SKILL_PATH"
  echo "Backup saved to $OLD_SKILL_PATH.backup"
fi

# ---------------------------------------------------------------------------
# Grant MCP tool permissions for the standalone Monte Carlo server.
#
# Claude Code's plugin settings.json only supports the "agent" key today;
# "permissions" is silently ignored.  Work around this by merging the
# wildcard permission directly into the user's global settings.
# ---------------------------------------------------------------------------
MCP_PERM="mcp__monte-carlo-mcp__*"
SETTINGS_FILE="$HOME/.claude/settings.json"

if [ -f "$SETTINGS_FILE" ]; then
  # Idempotent merge — adds the permission only if not already present.
  python3 -c "
import json, sys, pathlib

path = pathlib.Path(sys.argv[1])
perm = sys.argv[2]

data = json.loads(path.read_text())
allow = data.setdefault('permissions', {}).setdefault('allow', [])

if perm not in allow:
    allow.append(perm)
    path.write_text(json.dumps(data, indent=2) + '\n')
    print(f'  Added \"{perm}\" to {path}')
else:
    print(f'  Permission \"{perm}\" already present in {path}')
" "$SETTINGS_FILE" "$MCP_PERM"
else
  echo "  ⚠ $SETTINGS_FILE not found — add the following permission manually:"
  echo "    \"$MCP_PERM\" in permissions.allow"
fi

echo "✓ Post-install cleanup complete."
echo "  Run /mcp in Claude Code to authenticate with Monte Carlo."
echo "  Restart Claude Code to activate."
