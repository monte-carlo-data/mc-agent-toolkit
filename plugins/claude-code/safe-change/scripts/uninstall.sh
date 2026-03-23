#!/bin/bash
set -e

SKILL_PATH="$HOME/.claude/skills/safe-change"
BACKUP_PATH="$SKILL_PATH.backup"
if [ -d "$BACKUP_PATH" ]; then
  echo "Restoring standalone safe-change skill..."
  mv "$BACKUP_PATH" "$SKILL_PATH"
  echo "✓ Standalone skill restored."
else
  echo "No backup found. Install standalone skill from mcd-agent-toolkit/skills/ if needed."
fi

echo "✓ Plugin uninstalled."
echo "  Remove MCD_ID and MCD_TOKEN from your shell profile manually."
