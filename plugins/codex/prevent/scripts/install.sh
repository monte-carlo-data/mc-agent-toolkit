#!/bin/bash
set -e

# Monte Carlo Prevent — Codex plugin installer
# 1. Clones the repo and copies the plugin into the target repo
# 2. Creates .agents/plugins/marketplace.json
# 3. Adds Monte Carlo MCP server to ~/.codex/config.toml
# 4. Enables codex_hooks
# 5. Triggers OAuth login

PLUGIN_NAME="mc-prevent"
REPO_URL="https://github.com/monte-carlo-data/mcd-agent-toolkit.git"
PLUGIN_SRC="plugins/codex/prevent"
SHARED_LIB="hooks/prevent/lib"
SHARED_SKILL="skills/prevent"

CONFIG_DIR="$HOME/.codex"
CONFIG_FILE="$CONFIG_DIR/config.toml"
SERVER_NAME="monte-carlo"
SERVER_URL="https://integrations.getmontecarlo.com/mcp"

# --- Parse arguments ---
# Usage: install.sh [--local /path/to/mcd-agent-toolkit] <target-repo>
SOURCE_DIR=""
TARGET_REPO=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --local)
      SOURCE_DIR="$(cd "$2" && pwd)"
      shift 2
      ;;
    *)
      TARGET_REPO="$1"
      shift
      ;;
  esac
done

TARGET_REPO="${TARGET_REPO:-.}"
TARGET_REPO="$(cd "$TARGET_REPO" && pwd)"
TARGET="$TARGET_REPO/plugins/$PLUGIN_NAME"

echo "Installing $PLUGIN_NAME Codex plugin..."
echo "  Target repo: $TARGET_REPO"
echo "  Plugin dir:  $TARGET"
echo ""

# ============================================================
# STEP 1: Install plugin files
# ============================================================

if [ -n "$SOURCE_DIR" ]; then
  # --- Local source ---
  echo "[1/5] Copying from local source: $SOURCE_DIR"
  REPO_ROOT="$SOURCE_DIR"
else
  # --- Clone from GitHub ---
  TMPDIR_ROOT="${TMPDIR:-/tmp}"
  CLONE_DIR="$TMPDIR_ROOT/mcd-agent-toolkit-$$"

  cleanup() { rm -rf "$CLONE_DIR"; }
  trap cleanup EXIT

  echo "[1/5] Cloning repository..."
  git clone --depth 1 --quiet "$REPO_URL" "$CLONE_DIR"
  REPO_ROOT="$CLONE_DIR"
fi

# --- Verify plugin source exists ---
if [ ! -f "$REPO_ROOT/$PLUGIN_SRC/.codex-plugin/plugin.json" ]; then
  echo "ERROR: Plugin manifest not found at $PLUGIN_SRC/.codex-plugin/plugin.json"
  exit 1
fi

# --- Remove previous installation ---
if [ -d "$TARGET" ]; then
  echo "  Removing previous installation..."
  rm -rf "$TARGET"
fi

# --- Copy plugin files (excluding symlinks) ---
mkdir -p "$TARGET"
cd "$REPO_ROOT/$PLUGIN_SRC"
find . -not -type l -not -path './__pycache__/*' -not -path './.pytest_cache/*' \
       -not -path './tests/*' -not -name '*.pyc' | cpio -pdm "$TARGET" 2>/dev/null

# --- Copy symlink targets as real directories ---
cp -R "$REPO_ROOT/$SHARED_LIB" "$TARGET/hooks/lib"
mkdir -p "$TARGET/skills"
cp -R "$REPO_ROOT/$SHARED_SKILL" "$TARGET/skills/prevent"

# --- Clean up dev artifacts ---
find "$TARGET" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find "$TARGET" -name "*.pyc" -delete 2>/dev/null || true
rm -rf "$TARGET/hooks/lib/tests"

echo "  Plugin files installed."

# ============================================================
# STEP 2: Create marketplace.json
# ============================================================

echo "[2/5] Creating marketplace config..."
MARKETPLACE_DIR="$TARGET_REPO/.agents/plugins"
MARKETPLACE_FILE="$MARKETPLACE_DIR/marketplace.json"

mkdir -p "$MARKETPLACE_DIR"

if [ -f "$MARKETPLACE_FILE" ] && grep -q "\"$PLUGIN_NAME\"" "$MARKETPLACE_FILE" 2>/dev/null; then
  echo "  marketplace.json already contains $PLUGIN_NAME — skipping."
else
  cat > "$MARKETPLACE_FILE" << 'EOF'
{
    "name": "local-plugins",
    "plugins": [
        {
            "name": "mc-prevent",
            "source": {
                "source": "local",
                "path": "./plugins/mc-prevent"
            },
            "policy": {
                "installation": "AVAILABLE"
            },
            "category": "Data Observability"
        }
    ]
}
EOF
  echo "  Created $MARKETPLACE_FILE"
fi

# ============================================================
# STEP 3: Configure MCP server
# ============================================================

echo "[3/5] Configuring Monte Carlo MCP server..."
mkdir -p "$CONFIG_DIR"

if [ -f "$CONFIG_FILE" ] && grep -q "\[mcp_servers\.${SERVER_NAME}\]" "$CONFIG_FILE" 2>/dev/null; then
  echo "  MCP server already configured — skipping."
else
  echo "" >> "$CONFIG_FILE"
  cat >> "$CONFIG_FILE" << EOF

[mcp_servers.${SERVER_NAME}]
url = "${SERVER_URL}"
enabled = true
http_headers = { "User-Agent" = "codex-mcp/1.0" }
EOF
  echo "  Added monte-carlo MCP server to $CONFIG_FILE"
fi

# ============================================================
# STEP 4: Enable hooks
# ============================================================

echo "[4/5] Enabling codex hooks..."

if [ -f "$CONFIG_FILE" ] && grep -q "codex_hooks" "$CONFIG_FILE" 2>/dev/null; then
  echo "  Hooks already enabled — skipping."
else
  cat >> "$CONFIG_FILE" << EOF

[features]
codex_hooks = true
EOF
  echo "  Enabled codex_hooks in $CONFIG_FILE"
fi

# ============================================================
# STEP 5: OAuth login
# ============================================================

echo "[5/5] Starting OAuth login..."
echo "  A browser window will open — log in with your Monte Carlo account."
echo ""

codex mcp login "$SERVER_NAME" || echo "  OAuth login skipped (run 'codex mcp login monte-carlo' manually if needed)."

echo ""
echo "Done! $PLUGIN_NAME installed to $TARGET"
echo ""
echo "Next steps:"
echo "  1. Restart Codex in $TARGET_REPO"
echo "  2. You should see 'Installed mc-prevent plugin' on startup"
