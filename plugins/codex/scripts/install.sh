#!/bin/bash
set -e

# Monte Carlo Agent Toolkit — Codex plugin installer
# 1. Clones the repo and copies the plugin into the target repo
# 2. Registers skills (prevent, generate-validation-notebook, push-ingestion) in .agents/skills/
# 3. Writes hooks to <repo>/.codex/hooks.json (project-level)
# 4. Creates .agents/plugins/marketplace.json
# 5. Adds Monte Carlo MCP server to ~/.codex/config.toml
# 6. Enables codex_hooks
# 7. Triggers OAuth login

PLUGIN_NAME="mc-agent-toolkit"
REPO_URL="https://github.com/monte-carlo-data/mcd-agent-toolkit.git"
PLUGIN_SRC="plugins/codex"
SHARED_LIB="plugins/shared/prevent/lib"
SHARED_SKILLS=("skills/prevent" "skills/generate-validation-notebook" "skills/push-ingestion")

CONFIG_DIR="$HOME/.codex"
CONFIG_FILE="$CONFIG_DIR/config.toml"
HOOKS_FILE=""  # set after TARGET_REPO is resolved
SERVER_NAME="monte-carlo-mcp"
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
HOOKS_FILE="$TARGET_REPO/.codex/hooks.json"

echo "Installing $PLUGIN_NAME Codex plugin..."
echo "  Target repo: $TARGET_REPO"
echo "  Plugin dir:  $TARGET"
echo ""

# ============================================================
# STEP 1: Install plugin files
# ============================================================

if [ -n "$SOURCE_DIR" ]; then
  # --- Local source ---
  echo "[1/7] Copying from local source: $SOURCE_DIR"
  REPO_ROOT="$SOURCE_DIR"
else
  # --- Clone from GitHub ---
  TMPDIR_ROOT="${TMPDIR:-/tmp}"
  CLONE_DIR="$TMPDIR_ROOT/mcd-agent-toolkit-$$"

  cleanup() { rm -rf "$CLONE_DIR"; }
  trap cleanup EXIT

  echo "[1/7] Cloning repository..."
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
cp -R "$REPO_ROOT/$SHARED_LIB" "$TARGET/hooks/prevent/lib"
mkdir -p "$TARGET/skills"
for skill in "${SHARED_SKILLS[@]}"; do
  skill_name="$(basename "$skill")"
  cp -R "$REPO_ROOT/$skill" "$TARGET/skills/$skill_name"
done

# --- Clean up dev artifacts ---
find "$TARGET" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find "$TARGET" -name "*.pyc" -delete 2>/dev/null || true
rm -rf "$TARGET/hooks/prevent/lib/tests"

echo "  Plugin files installed."

# ============================================================
# STEP 2: Register skill in .agents/skills/
# ============================================================

echo "[2/7] Registering skills..."
SKILLS_DIR="$TARGET_REPO/.agents/skills"

mkdir -p "$SKILLS_DIR"

for skill in "${SHARED_SKILLS[@]}"; do
  skill_name="$(basename "$skill")"
  skill_target="$SKILLS_DIR/$skill_name"

  if [ -d "$skill_target" ]; then
    echo "  Removing previous $skill_name installation..."
    rm -rf "$skill_target"
  fi

  cp -R "$TARGET/skills/$skill_name" "$skill_target"
  echo "  Skill registered at .agents/skills/$skill_name/"
done

# ============================================================
# STEP 3: Merge hooks into ~/.codex/hooks.json
# ============================================================

echo "[3/7] Registering hooks in .codex/hooks.json (project-level)..."

HOOKS_DIR="$TARGET/hooks/prevent"

mkdir -p "$(dirname "$HOOKS_FILE")"

# Note: Codex currently only emits PreToolUse/PostToolUse for the Bash tool.
# Edit|Write matchers are omitted until Codex expands tool coverage.
cat > "$HOOKS_FILE" << HOOKEOF
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "python3 $HOOKS_DIR/bash_hook.py"
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 $HOOKS_DIR/turn_end_hook.py"
          }
        ]
      }
    ]
  }
}
HOOKEOF
echo "  Created $HOOKS_FILE"

# ============================================================
# STEP 4: Create marketplace.json
# ============================================================

echo "[4/7] Creating marketplace config..."
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
            "name": "mc-agent-toolkit",
            "source": {
                "source": "local",
                "path": "./plugins/mc-agent-toolkit"
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
# STEP 5: Configure MCP server
# ============================================================

echo "[5/7] Configuring Monte Carlo MCP server..."
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
# STEP 6: Enable hooks
# ============================================================

echo "[6/7] Enabling codex hooks..."

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
# STEP 7: OAuth login
# ============================================================

echo "[7/7] Starting OAuth login..."
echo "  A browser window will open — log in with your Monte Carlo account."
echo ""

codex mcp login "$SERVER_NAME" || echo "  OAuth login skipped (run 'codex mcp login $SERVER_NAME' manually if needed)."

echo ""
echo "Done! $PLUGIN_NAME installed to $TARGET"
echo ""
echo "Next steps:"
echo "  1. Restart Codex in $TARGET_REPO"
echo "  2. You should see 'Installed mc-agent-toolkit plugin' on startup"
echo "  3. Skills available: prevent, generate-validation-notebook, push-ingestion"
