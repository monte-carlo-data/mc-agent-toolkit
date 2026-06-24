#!/usr/bin/env bash
# Ensure stable install_id and fresh toolkit_session_id for the current Codex session.
# install_id is generated once and persisted; toolkit_session_id is regenerated every session.
# IDs live under Codex's own config home (~/.codex), NOT ~/.claude: a toolkit install in
# Codex is a distinct installation from one in Claude Code or Cortex Code (separate plugin
# registries, separate install flows), so each editor keeps its own install/session identity.
# Fails closed (exit 0) on any error — telemetry must never break a Codex session.
# Every session it also invokes the install beacon, which fires once per toolkit
# version (first install + upgrades) — fail-open and non-blocking.
set -uo pipefail

DIR="$HOME/.codex/mc-agent-toolkit"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Generate-or-read install_id via the shared helper — the SAME implementation
# install.sh uses to bake the install_id header into config.toml, so the baked
# header and the install beacon carry an identical install_id (streams join).
# shellcheck source=/dev/null
source "$SCRIPT_DIR/../lib/toolkit-ids.sh"
ensure_install_id "$DIR" >/dev/null || exit 0

uuidgen 2>/dev/null | tr '[:upper:]' '[:lower:]' > "$DIR/toolkit_session_id" 2>/dev/null || exit 0
chmod 600 "$DIR/toolkit_session_id" 2>/dev/null || exit 0

# Invoke the install beacon now that both ids exist (the sink requires both). It
# self-dedups by toolkit version — firing once per version (first install plus
# upgrades). Backgrounded, fail-open — never let telemetry break a session, and
# never gate the id writes above on its outcome.
bash "$SCRIPT_DIR/../lib/install-beacon.sh" \
  "$DIR" \
  "$SCRIPT_DIR/../../../.codex-plugin/plugin.json" \
  "codex" 2>/dev/null || true

exit 0
