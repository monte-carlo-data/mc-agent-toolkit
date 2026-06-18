#!/usr/bin/env bash
# Ensure stable install_id and fresh toolkit_session_id for the current Cortex Code session.
# install_id is generated once and persisted; toolkit_session_id is regenerated every session.
# IDs live under Cortex Code's own config home (~/.snowflake/cortex), NOT ~/.claude: a toolkit
# install in Cortex Code is a distinct installation from one in Claude Code (separate plugin
# registries, separate install flows), so each editor keeps its own install/session identity
# and the two never share an install_id or clobber each other's session_id.
# Fails closed (exit 0) on any error — telemetry must never break a Cortex Code session.
# If UUID files don't get written, skill-beacon.sh detects missing IDs and bails out.
set -uo pipefail

DIR="$HOME/.snowflake/cortex/mc-agent-toolkit"
mkdir -p "$DIR" 2>/dev/null || exit 0

if [[ ! -f "$DIR/install_id" ]]; then
  uuidgen 2>/dev/null | tr '[:upper:]' '[:lower:]' > "$DIR/install_id" 2>/dev/null || exit 0
  chmod 600 "$DIR/install_id" 2>/dev/null || exit 0
fi

uuidgen 2>/dev/null | tr '[:upper:]' '[:lower:]' > "$DIR/toolkit_session_id" 2>/dev/null || exit 0
chmod 600 "$DIR/toolkit_session_id" 2>/dev/null || exit 0

exit 0
