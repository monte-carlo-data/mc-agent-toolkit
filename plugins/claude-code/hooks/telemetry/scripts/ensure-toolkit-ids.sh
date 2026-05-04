#!/usr/bin/env bash
# Ensure stable install_id and fresh session_id for the current Claude Code session.
# install_id is generated once and persisted; session_id is regenerated every session.
set -euo pipefail

DIR="$HOME/.claude/mc-agent-toolkit"
mkdir -p "$DIR"

if [[ ! -f "$DIR/install_id" ]]; then
  uuidgen | tr '[:upper:]' '[:lower:]' > "$DIR/install_id"
  chmod 600 "$DIR/install_id"
fi

uuidgen | tr '[:upper:]' '[:lower:]' > "$DIR/session_id"
chmod 600 "$DIR/session_id"
