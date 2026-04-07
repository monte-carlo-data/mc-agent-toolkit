#!/bin/bash
set -e

echo "Running post-install cleanup for Monte Carlo Agent Toolkit plugin..."

# Remove standalone skills if present (superseded by plugin)
for skill_name in prevent generate-validation-notebook push-ingestion; do
  SKILL_PATH="$HOME/.claude/skills/$skill_name"
  if [ -d "$SKILL_PATH" ]; then
    echo "Backing up and removing standalone $skill_name skill (now bundled in plugin)..."
    cp -r "$SKILL_PATH" "$SKILL_PATH.backup"
    rm -rf "$SKILL_PATH"
    echo "Backup saved to $SKILL_PATH.backup"
  fi
done

# Clean up old safe-change skill left from the pre-rename plugin
OLD_SKILL_PATH="$HOME/.claude/skills/safe-change"
if [ -d "$OLD_SKILL_PATH" ]; then
  echo "Removing old safe-change skill (renamed to prevent)..."
  cp -r "$OLD_SKILL_PATH" "$OLD_SKILL_PATH.backup"
  rm -rf "$OLD_SKILL_PATH"
  echo "Backup saved to $OLD_SKILL_PATH.backup"
fi

echo "✓ Post-install cleanup complete."
echo "  Run /mcp in Claude Code to authenticate with Monte Carlo."
echo "  Restart Claude Code to activate."
