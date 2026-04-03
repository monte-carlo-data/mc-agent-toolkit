#!/bin/bash
set -euo pipefail

# Monte Carlo Agent Toolkit — VS Code / GitHub Copilot Plugin Installer
#
# Installs hooks, skills, commands, and MCP config into a target project
# for use with GitHub Copilot in VS Code.
#
# Usage:
#   ./install.sh [TARGET_DIR]
#
# TARGET_DIR defaults to the current working directory.
# Can also be run via:
#   bash <(curl -fsSL https://raw.githubusercontent.com/monte-carlo-data/mcd-agent-toolkit/main/plugins/vscode/scripts/install.sh)

TARGET_DIR="${1:-.}"
TARGET_DIR="$(cd "$TARGET_DIR" && pwd)"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# When run via curl|bash, clone the repo first
if [ ! -f "$PLUGIN_DIR/hooks/hooks.json" ]; then
  REPO_URL="https://github.com/monte-carlo-data/mcd-agent-toolkit.git"
  TMPDIR_ROOT="${TMPDIR:-/tmp}"
  CLONE_DIR="$TMPDIR_ROOT/mcd-agent-toolkit-$$"

  cleanup() { rm -rf "$CLONE_DIR"; }
  trap cleanup EXIT

  echo "  Cloning repository..."
  git clone --depth 1 --quiet "$REPO_URL" "$CLONE_DIR"

  PLUGIN_DIR="$CLONE_DIR/plugins/vscode"
  SCRIPT_DIR="$PLUGIN_DIR/scripts"
fi

REPO_ROOT="$(cd "$PLUGIN_DIR/../.." && pwd)"
SKILL_SRC="$REPO_ROOT/skills/prevent"

# --- Preflight checks ---

if ! command -v python3 &>/dev/null; then
  echo "Error: python3 is required but not installed." >&2
  exit 1
fi

if [ ! -f "$PLUGIN_DIR/hooks/hooks.json" ]; then
  echo "Error: hooks.json not found at $PLUGIN_DIR/hooks/hooks.json" >&2
  exit 1
fi

if [ ! -f "$SKILL_SRC/SKILL.md" ]; then
  echo "Error: skill not found at $SKILL_SRC/SKILL.md" >&2
  exit 1
fi

echo "Installing Monte Carlo Agent Toolkit for VS Code into: $TARGET_DIR"

# --- 1. Hooks ---

HOOKS_DEST="$TARGET_DIR/.github/hooks"
mkdir -p "$HOOKS_DEST"

# Copy hooks.json
cp "$PLUGIN_DIR/hooks/hooks.json" "$HOOKS_DEST/"

# Copy hook adapters (resolve symlinks)
cp -rL "$PLUGIN_DIR/hooks/prevent" "$HOOKS_DEST/"

# Copy shared lib (resolve symlink)
cp -rL "$PLUGIN_DIR/hooks/lib" "$HOOKS_DEST/"

# Clean dev artifacts from copied files
rm -rf "$HOOKS_DEST/lib/tests" "$HOOKS_DEST/lib/__pycache__"
find "$HOOKS_DEST" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find "$HOOKS_DEST" -name "*.pyc" -delete 2>/dev/null || true

echo "  ✓ Hooks copied to .github/hooks/"

# --- 2. Skills ---

SKILL_DEST="$TARGET_DIR/.github/skills/prevent"
mkdir -p "$SKILL_DEST"
cp -rL "$SKILL_SRC/"* "$SKILL_DEST/"
echo "  ✓ Skill copied to .github/skills/prevent/"

# --- 3. Commands ---

COMMAND_DEST="$TARGET_DIR/.github/commands"
mkdir -p "$COMMAND_DEST"
cp "$PLUGIN_DIR/commands/mc-validate.md" "$COMMAND_DEST/"
echo "  ✓ Command copied to .github/commands/mc-validate.md"

# --- 4. MCP server config ---

VSCODE_DIR="$TARGET_DIR/.vscode"
MCP_JSON="$VSCODE_DIR/mcp.json"

mkdir -p "$VSCODE_DIR"

if [ -f "$MCP_JSON" ]; then
  if grep -q '"monte-carlo"' "$MCP_JSON" 2>/dev/null; then
    echo "  ✓ MCP server already configured in .vscode/mcp.json"
  else
    echo "  ⚠ .vscode/mcp.json exists but monte-carlo MCP is not configured."
    echo "    Add under \"servers\":"
    echo '    "monte-carlo": { "type": "http", "url": "https://integrations.getmontecarlo.com/mcp" }'
    echo ""
    echo "  Tip: delete .vscode/mcp.json and re-run this script to get a fresh config."
  fi
else
  cp "$PLUGIN_DIR/mcp.json" "$MCP_JSON"
  echo "  ✓ Created .vscode/mcp.json with Monte Carlo MCP server config"
fi

# --- Done ---

echo ""
echo "Installation complete. Next steps:"
echo "  1. Open the project in VS Code"
echo "  2. Start a Copilot Agent Mode session (Ctrl+Shift+I / Cmd+Shift+I)"
echo "  3. The Monte Carlo MCP server will prompt for OAuth authentication on first use"
echo ""
echo "Note: VS Code Copilot hooks are currently in Preview."
echo "      Ensure you have the latest GitHub Copilot extension installed."
