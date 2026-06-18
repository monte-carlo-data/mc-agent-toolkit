#!/usr/bin/env bash
# Ensure stable install_id and fresh toolkit_session_id for the current Claude Code session.
# install_id is generated once and persisted; toolkit_session_id is regenerated every session.
# Fails closed (exit 0) on any error — telemetry must never break a Claude Code session.
# If UUID files don't get written, skill-beacon.sh detects missing IDs and bails out.
# On the first-ever run (when install_id is created) it also fires a one-shot
# "Toolkit Installed" beacon — fail-open and non-blocking.
set -uo pipefail

DIR="$HOME/.claude/mc-agent-toolkit"
mkdir -p "$DIR" 2>/dev/null || exit 0

install_id_created=0
if [[ ! -f "$DIR/install_id" ]]; then
  uuidgen 2>/dev/null | tr '[:upper:]' '[:lower:]' > "$DIR/install_id" 2>/dev/null || exit 0
  chmod 600 "$DIR/install_id" 2>/dev/null || exit 0
  install_id_created=1
fi

uuidgen 2>/dev/null | tr '[:upper:]' '[:lower:]' > "$DIR/toolkit_session_id" 2>/dev/null || exit 0
chmod 600 "$DIR/toolkit_session_id" 2>/dev/null || exit 0

# First-ever run for this editor: fire the one-shot install beacon now that both
# install_id and toolkit_session_id exist (the sink requires both). Backgrounded,
# fail-open — never let telemetry break a session, and never gate the id writes
# above on the beacon's outcome.
if [[ "$install_id_created" == "1" ]]; then
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  bash "$SCRIPT_DIR/../lib/install-beacon.sh" \
    "$DIR" \
    "$SCRIPT_DIR/../../../.claude-plugin/plugin.json" \
    "claude-code" 2>/dev/null || true
fi

exit 0
