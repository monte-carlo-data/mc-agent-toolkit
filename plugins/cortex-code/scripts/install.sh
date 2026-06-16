#!/bin/bash
set -e

# Monte Carlo Agent Toolkit — Cortex Code (CoCo) plugin installer.
#
# `cortex plugin install` rejects skill symlinks that point outside the plugin
# directory (the skills/ entries symlink to the repo-shared ../../../skills), so
# we materialize a symlink-resolved copy and install that through Cortex's managed
# plugin registry.

PLUGIN_NAME="mc-agent-toolkit"
REPO_URL="https://github.com/monte-carlo-data/mc-agent-toolkit.git"
PLUGIN_SRC="plugins/cortex-code"

command -v cortex >/dev/null 2>&1 || {
  echo "ERROR: 'cortex' CLI not found on PATH. Install Cortex Code first."
  exit 1
}

echo "Installing $PLUGIN_NAME Cortex Code plugin..."

# --- Locate repo: use local checkout if available, otherwise clone ---
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

if [ -f "$REPO_ROOT/$PLUGIN_SRC/.cortex-plugin/plugin.json" ]; then
  echo "  Using local repo at $REPO_ROOT"
  CLONE_DIR="$REPO_ROOT"
  clone_cleanup() { :; }
else
  TMPDIR_ROOT="${TMPDIR:-/tmp}"
  CLONE_DIR="$TMPDIR_ROOT/mc-agent-toolkit-$$"
  clone_cleanup() { rm -rf "$CLONE_DIR"; }
  echo "  Cloning repository..."
  git clone --depth 1 --quiet "$REPO_URL" "$CLONE_DIR"
fi

if [ ! -f "$CLONE_DIR/$PLUGIN_SRC/.cortex-plugin/plugin.json" ]; then
  echo "ERROR: Plugin manifest not found at $PLUGIN_SRC/.cortex-plugin/plugin.json"
  clone_cleanup
  exit 1
fi

# --- Materialize a symlink-resolved staging copy ---
STAGING="${TMPDIR:-/tmp}/mc-agent-toolkit-cortex-$$"
cleanup() { rm -rf "$STAGING"; clone_cleanup; }
trap cleanup EXIT
rm -rf "$STAGING"
cp -RL "$CLONE_DIR/$PLUGIN_SRC" "$STAGING"

# --- Strip dev artifacts from the installed copy ---
rm -rf "$STAGING/tests" "$STAGING/scripts" \
       "$STAGING/hooks/prevent/lib/tests" "$STAGING/hooks/telemetry/tests" \
       "$STAGING/.DS_Store"
find "$STAGING" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find "$STAGING" -name "*.pyc" -delete 2>/dev/null || true

# --- Install via Cortex's managed plugin registry (idempotent) ---
echo "  Running cortex plugin install..."
cortex plugin uninstall "$PLUGIN_NAME" >/dev/null 2>&1 || true
cortex plugin install "$STAGING"

echo ""
echo "Done! Verify with: cortex plugin list"
echo ""
echo "Next steps:"
echo "  1. Authenticate the Monte Carlo MCP server: run /mcp inside Cortex Code"
echo "     (or 'cortex mcp' from the CLI) and complete the OAuth flow."
echo "  2. To update later, re-run this installer."
