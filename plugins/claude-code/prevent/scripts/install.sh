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

echo "✓ Post-install cleanup complete."
echo "  Run /mcp in Claude Code to authenticate with Monte Carlo."
echo "  Restart Claude Code to activate."
