#!/bin/bash
set -e

echo "Running post-uninstall cleanup for Monte Carlo Agent Toolkit plugin..."

for skill_name in prevent generate-validation-notebook push-ingestion; do
  SKILL_PATH="$HOME/.claude/skills/$skill_name"
  BACKUP_PATH="$SKILL_PATH.backup"
  if [ -d "$BACKUP_PATH" ]; then
    echo "Restoring standalone $skill_name skill from backup..."
    mv "$BACKUP_PATH" "$SKILL_PATH"
    echo "✓ Standalone $skill_name skill restored."
  fi
done

echo "✓ Post-uninstall cleanup complete."
echo "  Install standalone skills from mc-agent-toolkit/skills/ if needed."
echo "  Done."
