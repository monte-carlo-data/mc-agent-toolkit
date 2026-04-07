#!/bin/bash
set -euo pipefail

# Monte Carlo Agent Toolkit — OpenCode Plugin Installer
#
# Installs the plugin, skill, and command into a target dbt project.
# Also merges the MCP server config into opencode.json.
#
# Usage:
#   ./install.sh [TARGET_DIR]
#
# TARGET_DIR defaults to the current working directory.

TARGET_DIR="${1:-.}"
TARGET_DIR="$(cd "$TARGET_DIR" && pwd)"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SKILL_SRC="$REPO_ROOT/skills/prevent"

# --- Preflight checks ---

if ! command -v bun &>/dev/null; then
  echo "Error: bun is required but not installed. Install from https://bun.sh" >&2
  exit 1
fi

if [ ! -f "$SCRIPT_DIR/src/index.ts" ]; then
  echo "Error: plugin source not found at $SCRIPT_DIR/src/index.ts" >&2
  exit 1
fi

if [ ! -f "$SKILL_SRC/SKILL.md" ]; then
  echo "Error: skill not found at $SKILL_SRC/SKILL.md" >&2
  exit 1
fi

echo "Installing MC Agent Toolkit for OpenCode into: $TARGET_DIR"

# --- 1. Plugin ---

PLUGIN_DEST="$TARGET_DIR/.opencode/plugins/mc-agent-toolkit"
mkdir -p "$PLUGIN_DEST"

# Copy plugin files (exclude node_modules, tests, symlinks)
for item in src package.json tsconfig.json; do
  cp -r "$SCRIPT_DIR/$item" "$PLUGIN_DEST/"
done

echo "  ✓ Plugin copied to .opencode/plugins/mc-agent-toolkit/"

# Install dependencies
(cd "$PLUGIN_DEST" && bun install --silent)
echo "  ✓ Dependencies installed"

# --- 2. Skill ---

SKILL_DEST="$TARGET_DIR/.opencode/skills/prevent"
mkdir -p "$SKILL_DEST"
cp -r "$SKILL_SRC/"* "$SKILL_DEST/"
echo "  ✓ Skill copied to .opencode/skills/prevent/"

# --- 3. Command ---

COMMAND_DEST="$TARGET_DIR/.opencode/commands"
mkdir -p "$COMMAND_DEST"
cp "$SCRIPT_DIR/commands/mc-validate.md" "$COMMAND_DEST/"
echo "  ✓ Command copied to .opencode/commands/mc-validate.md"

# --- 4. opencode.json (plugin registration + MCP server config) ---

OPENCODE_JSON="$TARGET_DIR/opencode.json"

if [ -f "$OPENCODE_JSON" ]; then
  NEEDS_GUIDANCE=false

  # Check plugin registration
  if grep -q '"\.opencode/plugins/mc-agent-toolkit"' "$OPENCODE_JSON" 2>/dev/null; then
    echo "  ✓ Plugin already registered in opencode.json"
  else
    echo "  ⚠ opencode.json exists but mc-agent-toolkit plugin is not registered."
    echo "    Add to your opencode.json:"
    echo '    "plugin": [".opencode/plugins/mc-agent-toolkit"]'
    NEEDS_GUIDANCE=true
  fi

  # Check MCP config
  if grep -q '"monte-carlo"' "$OPENCODE_JSON" 2>/dev/null; then
    echo "  ✓ MCP server already configured in opencode.json"
  else
    echo "  ⚠ monte-carlo MCP is not configured."
    echo '    Add under "mcp": { "monte-carlo": { "type": "remote", "url": "https://integrations.getmontecarlo.com/mcp" } }'
    NEEDS_GUIDANCE=true
  fi

  if [ "$NEEDS_GUIDANCE" = true ]; then
    echo ""
    echo "  Tip: delete opencode.json and re-run this script to get a fresh config."
  fi
else
  cp "$SCRIPT_DIR/opencode.json" "$OPENCODE_JSON"
  echo "  ✓ Created opencode.json with plugin registration and MCP server config"
fi

# --- Done ---

echo ""
echo "Installation complete. Next steps:"
echo "  1. Authenticate:  opencode mcp auth monte-carlo"
echo "  2. Launch:        opencode"
