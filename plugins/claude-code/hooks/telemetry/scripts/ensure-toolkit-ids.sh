#!/usr/bin/env bash
# Ensure stable install_id and fresh toolkit_session_id for the current Claude Code session.
# install_id is generated once and persisted; toolkit_session_id is regenerated every session.
# Fails closed (exit 0) on any error — telemetry must never break a Claude Code session.
# If UUID files don't get written, skill-beacon.sh detects missing IDs and bails out.
set -uo pipefail

DIR="$HOME/.claude/mc-agent-toolkit"
mkdir -p "$DIR" 2>/dev/null || exit 0

if [[ ! -f "$DIR/install_id" ]]; then
  uuidgen 2>/dev/null | tr '[:upper:]' '[:lower:]' > "$DIR/install_id" 2>/dev/null || exit 0
  chmod 600 "$DIR/install_id" 2>/dev/null || exit 0
fi

uuidgen 2>/dev/null | tr '[:upper:]' '[:lower:]' > "$DIR/toolkit_session_id" 2>/dev/null || exit 0
chmod 600 "$DIR/toolkit_session_id" 2>/dev/null || exit 0

exit 0
