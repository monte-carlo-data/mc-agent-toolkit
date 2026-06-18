#!/usr/bin/env bash
# Fire a "Toolkit Installed" beacon once per (machine+editor, toolkit version).
#
# Editor-agnostic: the caller (each editor's ensure-toolkit-ids.sh) passes the
# editor's id directory, plugin manifest path, and harness name, so this single
# body is synced UNCHANGED into every editor plugin
# (plugins/shared/telemetry/lib/ -> plugins/<editor>/hooks/telemetry/lib/ via
# `./scripts/bump-version.sh --sync-only`). Edit it here, never in the copies.
#
# Dedup lives here, keyed on a per-editor `beacon_sent_version` marker that records
# the toolkit version the beacon last fired for. The beacon fires on first install
# AND whenever the version changes (install -> upgrade), then updates the marker.
# Callers invoke this every session start; it self-dedups. The sink also dedups on
# (install_id, toolkit_version) as a backstop if the marker is lost.
#
# Usage: install-beacon.sh <ids_dir> <plugin_manifest_json> <harness>
#
# Fails closed (exit 0) on any error — telemetry must never break a session.
set -uo pipefail

# Opt-out
if [[ "${MC_AGENT_TOOLKIT_TELEMETRY_DISABLED:-}" == "1" ]]; then
  exit 0
fi

IDS_DIR="${1:-}"
PLUGIN_JSON="${2:-}"
HARNESS="${3:-}"
[[ -z "$IDS_DIR" || -z "$PLUGIN_JSON" || -z "$HARNESS" ]] && exit 0

INSTALL_ID="$(cat "$IDS_DIR/install_id" 2>/dev/null || echo "")"
TOOLKIT_SESSION_ID="$(cat "$IDS_DIR/toolkit_session_id" 2>/dev/null || echo "")"

# Don't send null/empty IDs — the sink requires valid v4 UUIDs for both.
[[ -z "$INSTALL_ID" || -z "$TOOLKIT_SESSION_ID" ]] && exit 0

TOOLKIT_VERSION="$(jq -r '.version // "unknown"' "$PLUGIN_JSON" 2>/dev/null || echo "unknown")"

# Dedup: fire once per (install, version). The marker records the version we last
# beaconed for; re-fire only when it differs from the current version (first run,
# or any upgrade/downgrade). Same version → nothing to do.
SENT_MARKER="$IDS_DIR/beacon_sent_version"
SENT_VERSION="$(cat "$SENT_MARKER" 2>/dev/null || echo "")"
[[ "$TOOLKIT_VERSION" == "$SENT_VERSION" ]] && exit 0

# Record this version as beaconed BEFORE firing, so a rapid second session in the
# same version doesn't double-fire. Best-effort; if it fails, the sink's
# (install_id, toolkit_version) dedup is the backstop.
printf '%s' "$TOOLKIT_VERSION" > "$SENT_MARKER" 2>/dev/null || true
chmod 600 "$SENT_MARKER" 2>/dev/null || true

# Beacon URL defaults to prod; MC engineers can override to dev for verification
# work (e.g. against mcp.dev.getmontecarlo.com before promoting an endpoint change).
BEACON_URL="${MCD_TOOLKIT_BEACON_URL:-https://mcp.getmontecarlo.com/mcp/toolkit/beacon}"

# harness identifies the editor this install runs under, so the sink can tell a
# Cortex Code install apart from a Claude Code one (each has its own install_id).
# Note: unlike the skill beacon, the install event carries NO skill /
# skill_args_present — the sink validates this event shape separately.
PAYLOAD="$(jq -nc \
  --arg event "Toolkit Installed" \
  --arg install_id "$INSTALL_ID" \
  --arg session_id "$TOOLKIT_SESSION_ID" \
  --arg toolkit_version "$TOOLKIT_VERSION" \
  --arg harness "$HARNESS" \
  --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  '{event: $event, install_id: $install_id, session_id: $session_id, toolkit_version: $toolkit_version, harness: $harness, ts: $ts}')"

# Fire-and-forget. 2s timeout so a slow server never delays session start.
# MC_BEACON_SYNC (test-only) runs curl in the foreground so tests can assert
# deterministically whether the beacon fired; production always backgrounds it.
if [[ -n "${MC_BEACON_SYNC:-}" ]]; then
  curl -fsS -m 2 -X POST -H 'Content-Type: application/json' -d "$PAYLOAD" "$BEACON_URL" >/dev/null 2>&1 || true
else
  ( curl -fsS -m 2 -X POST \
      -H 'Content-Type: application/json' \
      -d "$PAYLOAD" \
      "$BEACON_URL" \
      >/dev/null 2>&1 || true ) &
  disown
fi

exit 0
