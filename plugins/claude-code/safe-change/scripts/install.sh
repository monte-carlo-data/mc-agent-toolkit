#!/bin/bash
set -e

echo "Installing Monte Carlo Safe Change plugin..."

# Remove standalone safe-change skill if present
SKILL_PATH="$HOME/.claude/skills/safe-change"
if [ -d "$SKILL_PATH" ]; then
  echo "Backing up and removing standalone safe-change skill..."
  cp -r "$SKILL_PATH" "$SKILL_PATH.backup"
  rm -rf "$SKILL_PATH"
  echo "Backup saved to $SKILL_PATH.backup"
fi

echo "✓ Monte Carlo Safe Change plugin installed."
echo "  Ensure MCD_ID and MCD_TOKEN are set in your shell profile."
echo "  Restart Claude Code to activate."
