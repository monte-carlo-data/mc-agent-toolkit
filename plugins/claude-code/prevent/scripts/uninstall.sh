#!/bin/bash
set -e

echo "Running post-uninstall cleanup for Monte Carlo Prevent plugin..."

SKILL_PATH="$HOME/.claude/skills/prevent"
BACKUP_PATH="$SKILL_PATH.backup"
if [ -d "$BACKUP_PATH" ]; then
  echo "Restoring standalone prevent skill from backup..."
  mv "$BACKUP_PATH" "$SKILL_PATH"
  echo "✓ Standalone skill restored."
else
  echo "No backup found. Install standalone skill from mcd-agent-toolkit/skills/ if needed."
fi

# Remove standalone MCP tool permission added by install.sh
MCP_PERM="mcp__monte-carlo-mcp__*"
SETTINGS_FILE="$HOME/.claude/settings.json"

if [ -f "$SETTINGS_FILE" ]; then
  python3 -c "
import json, sys, pathlib

path = pathlib.Path(sys.argv[1])
perm = sys.argv[2]

data = json.loads(path.read_text())
allow = data.get('permissions', {}).get('allow', [])

if perm in allow:
    allow.remove(perm)
    path.write_text(json.dumps(data, indent=2) + '\n')
    print(f'  Removed \"{perm}\" from {path}')
else:
    print(f'  Permission \"{perm}\" not found in {path} (nothing to remove)')
" "$SETTINGS_FILE" "$MCP_PERM"
fi

echo "✓ Post-uninstall cleanup complete."
echo "  Done."
