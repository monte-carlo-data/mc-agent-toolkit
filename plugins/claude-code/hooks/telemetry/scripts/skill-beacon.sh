#!/usr/bin/env bash
# Fire a fire-and-forget beacon on Skill tool invocation.
# Reads tool input JSON from stdin (Claude Code hook contract).
# Fails closed (exit 0) on any error — telemetry must never break a skill invocation.
set -uo pipefail

# Opt-out
if [[ "${MC_AGENT_TOOLKIT_TELEMETRY_DISABLED:-}" == "1" ]]; then
  exit 0
fi

DIR="$HOME/.claude/mc-agent-toolkit"
INSTALL_ID="$(cat "$DIR/install_id" 2>/dev/null || echo "")"
TOOLKIT_SESSION_ID="$(cat "$DIR/toolkit_session_id" 2>/dev/null || echo "")"

# If files are missing for any reason, don't beacon (better than sending null IDs)
[[ -z "$INSTALL_ID" || -z "$TOOLKIT_SESSION_ID" ]] && exit 0

# Capture stdin ONCE — stdin is a stream, consumed by first reader.
# Hook stdin contract: {"tool_name":"Skill","tool_input":{"skill":"...","args":"..."},...}
HOOK_INPUT="$(cat || true)"
[[ -z "$HOOK_INPUT" ]] && exit 0

SKILL_NAME="$(printf '%s' "$HOOK_INPUT" | jq -r '.tool_input.skill // empty' 2>/dev/null || true)"
[[ -z "$SKILL_NAME" ]] && exit 0  # not a skill invocation we recognize; bail

# Only beacon for mc-agent-toolkit skills. Skill names may arrive bare
# (e.g. "asset-health") or plugin-namespaced (e.g. "mc-agent-toolkit:asset-health");
# strip any "<plugin>:" prefix before checking against this plugin's skills/ dir.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS_DIR="$SCRIPT_DIR/../../../skills"
SKILL_BASENAME="${SKILL_NAME##*:}"
[[ -d "$SKILLS_DIR/$SKILL_BASENAME" ]] || exit 0

ARGS_PRESENT="$(printf '%s' "$HOOK_INPUT" | jq -r '((.tool_input.args // "") | length) > 0' 2>/dev/null || echo false)"

# Beacon URL defaults to prod; MC engineers can override to dev for verification
# work (e.g. against mcp.dev.getmontecarlo.com before promoting an endpoint change).
BEACON_URL="${MCD_TOOLKIT_BEACON_URL:-https://mcp.getmontecarlo.com/mcp/toolkit/beacon}"

# Resolve plugin version from plugin.json relative to this script's location.
# Script path: <plugin_root>/hooks/telemetry/scripts/skill-beacon.sh
PLUGIN_JSON="$SCRIPT_DIR/../../../.claude-plugin/plugin.json"
TOOLKIT_VERSION="$(jq -r '.version // "unknown"' "$PLUGIN_JSON" 2>/dev/null || echo "unknown")"

PAYLOAD="$(jq -nc \
  --arg event "Toolkit Skill Invoked" \
  --arg install_id "$INSTALL_ID" \
  --arg session_id "$TOOLKIT_SESSION_ID" \
  --arg skill "$SKILL_NAME" \
  --argjson skill_args_present "$ARGS_PRESENT" \
  --arg toolkit_version "$TOOLKIT_VERSION" \
  --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  '{event: $event, install_id: $install_id, session_id: $session_id, skill: $skill, skill_args_present: $skill_args_present, toolkit_version: $toolkit_version, ts: $ts}')"

# Fire-and-forget. 2s timeout so a slow server never delays a skill invocation.
( curl -fsS -m 2 -X POST \
    -H 'Content-Type: application/json' \
    -d "$PAYLOAD" \
    "$BEACON_URL" \
    >/dev/null 2>&1 || true ) &
disown

exit 0
