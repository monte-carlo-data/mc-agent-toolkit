#!/usr/bin/env bash
# Ensure stable install_id and fresh toolkit_session_id for the current Cortex Code session.
# install_id is generated once and persisted; toolkit_session_id is regenerated every session.
# IDs live under Cortex Code's own config home (~/.snowflake/cortex), NOT ~/.claude: a toolkit
# install in Cortex Code is a distinct installation from one in Claude Code (separate plugin
# registries, separate install flows), so each editor keeps its own install/session identity
# and the two never share an install_id or clobber each other's session_id.
# Also persists toolkit_version and seeds the MCP headers helper into the id dir, so the
# monte-carlo-mcp headersHelper (.mcp.json) can stamp install_id/session_id/version on authed
# MCP traffic — see mcp-headers-helper.py.
# Fails closed (exit 0) on any error — telemetry must never break a Cortex Code session.
# If UUID files don't get written, skill-beacon.sh detects missing IDs and bails out.
# Every session it also invokes the install beacon, which fires once per toolkit
# version (first install + upgrades) — fail-open and non-blocking.
set -uo pipefail

DIR="$HOME/.snowflake/cortex/mc-agent-toolkit"
mkdir -p "$DIR" 2>/dev/null || exit 0

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_JSON="$SCRIPT_DIR/../../../.cortex-plugin/plugin.json"

if [[ ! -f "$DIR/install_id" ]]; then
  uuidgen 2>/dev/null | tr '[:upper:]' '[:lower:]' > "$DIR/install_id" 2>/dev/null || exit 0
  chmod 600 "$DIR/install_id" 2>/dev/null || exit 0
fi

uuidgen 2>/dev/null | tr '[:upper:]' '[:lower:]' > "$DIR/toolkit_session_id" 2>/dev/null || exit 0
chmod 600 "$DIR/toolkit_session_id" 2>/dev/null || exit 0

# Persist the toolkit version so the MCP headers helper (which runs from $DIR,
# outside the plugin bundle) can emit it as x-mcd-toolkit-version. Skip writing a
# junk value if it can't be resolved — better no header than "unknown".
TOOLKIT_VERSION="$(jq -r '.version // empty' "$PLUGIN_JSON" 2>/dev/null || echo "")"
if [[ -n "$TOOLKIT_VERSION" ]]; then
  printf '%s' "$TOOLKIT_VERSION" > "$DIR/toolkit_version" 2>/dev/null || true
  chmod 600 "$DIR/toolkit_version" 2>/dev/null || true
fi

# Seed the MCP headers helper into $DIR so .mcp.json's headersHelper can run it by
# a fixed $HOME path (CLAUDE_PLUGIN_ROOT is not interpolated in headersHelper —
# claude-code#47789). Copy only when missing or changed, so a normal session
# writes nothing. The helper reads the id files above from its own directory.
HELPER_SRC="$SCRIPT_DIR/../lib/mcp-headers-helper.py"
if [[ -f "$HELPER_SRC" ]] && ! cmp -s "$HELPER_SRC" "$DIR/mcp-headers-helper.py" 2>/dev/null; then
  cp "$HELPER_SRC" "$DIR/mcp-headers-helper.py" 2>/dev/null \
    && chmod 600 "$DIR/mcp-headers-helper.py" 2>/dev/null || true
fi

# Invoke the install beacon now that both ids exist (the sink requires both). It
# self-dedups by toolkit version — firing once per version (first install plus
# upgrades). Backgrounded, fail-open — never let telemetry break a session, and
# never gate the id writes above on its outcome.
bash "$SCRIPT_DIR/../lib/install-beacon.sh" \
  "$DIR" \
  "$PLUGIN_JSON" \
  "cortex-code" 2>/dev/null || true

exit 0
