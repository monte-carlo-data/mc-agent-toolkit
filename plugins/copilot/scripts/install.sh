#!/bin/bash
set -euo pipefail

# Monte Carlo Agent Toolkit — Copilot CLI Hook Installer
#
# Installs MC Prevent hooks into a target project's .github/hooks/ directory.
# Skills and MCP are delivered via the plugin (`copilot plugin install`).
#
# Usage:
#   ./install.sh [TARGET_DIR]
#
# TARGET_DIR defaults to the current working directory.

TARGET_DIR="${1:-.}"
TARGET_DIR="$(cd "$TARGET_DIR" && pwd)"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd "$PLUGIN_DIR/../.." && pwd)"
HOOKS_SRC="$PLUGIN_DIR/hooks/prevent"
LIB_SRC="$REPO_ROOT/hooks/prevent/lib"

# --- Preflight checks ---

if ! command -v python3 &>/dev/null; then
  echo "Error: python3 is required but not installed." >&2
  exit 1
fi

if [ ! -f "$HOOKS_SRC/pre_edit_hook.py" ]; then
  echo "Error: hook scripts not found at $HOOKS_SRC/" >&2
  exit 1
fi

if [ ! -f "$LIB_SRC/protocol.py" ]; then
  echo "Error: shared lib not found at $LIB_SRC/" >&2
  exit 1
fi

echo "Installing MC Prevent hooks for Copilot CLI into: $TARGET_DIR"

# --- 1. Hook scripts ---

SCRIPTS_DEST="$TARGET_DIR/.github/hooks/scripts"
mkdir -p "$SCRIPTS_DEST"

# Copy hook adapter scripts
for script in pre_edit_hook.py post_edit_hook.py pre_commit_hook.py turn_end_hook.py; do
  cp "$HOOKS_SRC/$script" "$SCRIPTS_DEST/"
done
chmod +x "$SCRIPTS_DEST"/*.py

echo "  ✓ Hook scripts copied to .github/hooks/scripts/"

# --- 2. Shared lib (resolve symlinks) ---

LIB_DEST="$SCRIPTS_DEST/lib"
mkdir -p "$LIB_DEST"
cp -rL "$LIB_SRC/"* "$LIB_DEST/"

# Clean dev artifacts
rm -rf "$LIB_DEST/tests" "$LIB_DEST/__pycache__"
find "$LIB_DEST" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find "$LIB_DEST" -name "*.pyc" -delete 2>/dev/null || true

echo "  ✓ Shared lib copied to .github/hooks/scripts/lib/"

# --- 3. Hook registration ---

HOOKS_DEST="$TARGET_DIR/.github/hooks"
cp "$SCRIPT_DIR/mc-prevent.json" "$HOOKS_DEST/"

echo "  ✓ Hook registration copied to .github/hooks/mc-prevent.json"

# --- 4. User-global session-start telemetry hook (install beacon) ---
# Unlike the project-level Prevent hooks above, the install beacon is registered
# at the user level (~/.copilot/hooks/) so the toolkit installation is counted
# once per machine, regardless of which repo a session runs in. Fail-open: the
# beacon never blocks a session and the marker dedups it to one POST per machine.
COPILOT_HOME_DIR="${COPILOT_HOME:-$HOME/.copilot}"
COPILOT_HOOKS_DIR="$COPILOT_HOME_DIR/hooks"
TELEMETRY_DEST="$COPILOT_HOOKS_DIR/mc-agent-toolkit"

mkdir -p "$TELEMETRY_DEST/hooks"
# Copy the telemetry tree (scripts + synced lib) and the manifest, preserving the
# layout so ensure-toolkit-ids.sh resolves ../../../plugin.json for the version.
rm -rf "$TELEMETRY_DEST/hooks/telemetry"
cp -R "$PLUGIN_DIR/hooks/telemetry" "$TELEMETRY_DEST/hooks/"
cp "$PLUGIN_DIR/plugin.json" "$TELEMETRY_DEST/plugin.json"
rm -rf "$TELEMETRY_DEST/hooks/telemetry/tests"
ENSURE_IDS="$TELEMETRY_DEST/hooks/telemetry/scripts/ensure-toolkit-ids.sh"
chmod +x "$ENSURE_IDS"

cat > "$COPILOT_HOOKS_DIR/mc-agent-toolkit-telemetry.json" << EOF
{
    "version": 1,
    "hooks": {
        "sessionStart": [
            {
                "type": "command",
                "bash": "bash '$ENSURE_IDS'",
                "timeoutSec": 5
            }
        ]
    }
}
EOF

echo "  ✓ Session-start telemetry hook registered at $COPILOT_HOOKS_DIR/mc-agent-toolkit-telemetry.json"

# --- Done ---

echo ""
echo "Hook installation complete. Next steps:"
echo "  1. Install the plugin (for skills + MCP):"
echo "       copilot plugin install $PLUGIN_DIR"
echo "  2. Start a Copilot session:"
echo "       copilot"
echo "  3. The Monte Carlo MCP server will prompt for authentication on first use"
