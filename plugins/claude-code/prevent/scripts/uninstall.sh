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

echo "✓ Post-uninstall cleanup complete."
echo "  Done."
