#!/usr/bin/env bash
# Ensure stable install_id and fresh toolkit_session_id for the current Copilot session.
# install_id is generated once and persisted; toolkit_session_id is regenerated every session.
# IDs live under Copilot's own config home (~/.copilot), NOT ~/.claude: a toolkit install in
# Copilot is a distinct installation from one in Claude Code or Cortex Code (separate plugin
# registries, separate install flows), so each editor keeps its own install/session identity.
# Fails closed (exit 0) on any error — telemetry must never break a Copilot session.
# Every session it also invokes the install beacon, which fires once per toolkit
# version (first install + upgrades) — fail-open and non-blocking.
set -uo pipefail

DIR="$HOME/.copilot/mc-agent-toolkit"
mkdir -p "$DIR" 2>/dev/null || exit 0

if [[ ! -f "$DIR/install_id" ]]; then
  uuidgen 2>/dev/null | tr '[:upper:]' '[:lower:]' > "$DIR/install_id" 2>/dev/null || exit 0
  chmod 600 "$DIR/install_id" 2>/dev/null || exit 0
fi

uuidgen 2>/dev/null | tr '[:upper:]' '[:lower:]' > "$DIR/toolkit_session_id" 2>/dev/null || exit 0
chmod 600 "$DIR/toolkit_session_id" 2>/dev/null || exit 0

# Invoke the install beacon now that both ids exist (the sink requires both). It
# self-dedups by toolkit version — firing once per version (first install plus
# upgrades). Backgrounded, fail-open — never let telemetry break a session, and
# never gate the id writes above on its outcome.
# Copilot's manifest is the plugin-root plugin.json (no .copilot-plugin/ subdir),
# so the version path is one level shallower than the other editors.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
bash "$SCRIPT_DIR/../lib/install-beacon.sh" \
  "$DIR" \
  "$SCRIPT_DIR/../../../plugin.json" \
  "copilot" 2>/dev/null || true

exit 0
