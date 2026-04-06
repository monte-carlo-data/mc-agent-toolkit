#!/bin/bash
set -e

# Monte Carlo Agent Toolkit — Cursor plugin installer
# Clones the repo (or uses an existing clone) and copies the plugin
# into ~/.cursor/plugins/local/mc-agent-toolkit with symlinks resolved.

PLUGIN_NAME="mc-agent-toolkit"
REPO_URL="https://github.com/monte-carlo-data/mcd-agent-toolkit.git"
PLUGIN_SRC="plugins/cursor"

# --- Determine target directory (macOS/Linux vs Windows Git Bash) ---
if [ -n "$USERPROFILE" ]; then
  CURSOR_PLUGINS="$USERPROFILE/.cursor/plugins/local"
else
  CURSOR_PLUGINS="$HOME/.cursor/plugins/local"
fi
TARGET="$CURSOR_PLUGINS/$PLUGIN_NAME"

echo "Installing $PLUGIN_NAME Cursor plugin..."
echo "  Target: $TARGET"

# --- Clone or update repo in a temp directory ---
TMPDIR_ROOT="${TMPDIR:-/tmp}"
CLONE_DIR="$TMPDIR_ROOT/mcd-agent-toolkit-$$"

cleanup() { rm -rf "$CLONE_DIR"; }
trap cleanup EXIT

echo "  Cloning repository..."
git clone --depth 1 --quiet "$REPO_URL" "$CLONE_DIR"

# --- Verify plugin source exists ---
if [ ! -f "$CLONE_DIR/$PLUGIN_SRC/.cursor-plugin/plugin.json" ]; then
  echo "ERROR: Plugin manifest not found at $PLUGIN_SRC/.cursor-plugin/plugin.json"
  exit 1
fi

# --- Remove previous installation ---
if [ -d "$TARGET" ]; then
  echo "  Removing previous installation..."
  rm -rf "$TARGET"
fi

# --- Copy plugin files with symlinks resolved ---
mkdir -p "$CURSOR_PLUGINS"
cp -rL "$CLONE_DIR/$PLUGIN_SRC" "$TARGET"

# --- Remove test files and dev artifacts from installation ---
rm -rf "$TARGET/tests" "$TARGET/scripts" "$TARGET/hooks/prevent/lib/tests" \
       "$TARGET/__pycache__" "$TARGET/.DS_Store" "$TARGET/.git"
find "$TARGET" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find "$TARGET" -name "*.pyc" -delete 2>/dev/null || true

echo ""
echo "Done! $PLUGIN_NAME installed to $TARGET"
echo ""
echo "Next steps:"
echo "  1. Restart Cursor (or run 'Developer: Reload Window' from the Command Palette)"
echo "  2. The Monte Carlo MCP server will prompt for OAuth authentication on first use"
