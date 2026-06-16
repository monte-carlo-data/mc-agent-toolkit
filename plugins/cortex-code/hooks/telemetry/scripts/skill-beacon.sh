#!/usr/bin/env bash
# Fire a fire-and-forget beacon on skill invocation (Cortex Code adapter).
# Reads tool input JSON from stdin (Cortex hook contract). Cortex delivers the
# invoked skill as tool_input.command = "<plugin>:<skill-name>" (Claude Code uses
# tool_input.skill), so we read .command first and fall back to .skill.
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
HOOK_INPUT="$(cat || true)"
[[ -z "$HOOK_INPUT" ]] && exit 0

# Only beacon for the skill tool. Cortex's tool_input.command field is also present
# on other tools (e.g. Bash), so guard on tool_name explicitly rather than relying
# solely on the hook matcher.
TOOL_NAME="$(printf '%s' "$HOOK_INPUT" | jq -r '.tool_name // empty' 2>/dev/null | tr '[:upper:]' '[:lower:]' || true)"
[[ "$TOOL_NAME" == "skill" ]] || exit 0

# Cortex: tool_input.command = "<plugin>:<skill-name>"; Claude Code: tool_input.skill.
SKILL_NAME="$(printf '%s' "$HOOK_INPUT" | jq -r '.tool_input.command // .tool_input.skill // empty' 2>/dev/null || true)"
[[ -z "$SKILL_NAME" ]] && exit 0  # not a skill invocation we recognize; bail

# Only beacon for this plugin's skills. Cortex namespaces a skill invocation as
# "<plugin-name>:<skill>", using the skill's `name:` field — e.g.
# "mc-agent-toolkit:monte-carlo-prevent" (the name field, NOT the skills/ directory
# name "prevent"). So gate on our own plugin-name prefix from the manifest rather
# than matching skill directory names.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Script path: <plugin_root>/hooks/telemetry/scripts/skill-beacon.sh
PLUGIN_JSON="$SCRIPT_DIR/../../../.cortex-plugin/plugin.json"
PLUGIN_NAME="$(jq -r '.name // empty' "$PLUGIN_JSON" 2>/dev/null || true)"
[[ -z "$PLUGIN_NAME" ]] && exit 0
case "$SKILL_NAME" in
  "$PLUGIN_NAME":*) : ;;   # one of our plugin's skills
  *) exit 0 ;;             # another plugin's skill (or unnamespaced) — don't beacon
esac

# Cortex does not include invocation args in the hook payload, so this is always
# false here; kept for payload-schema parity with the other harnesses.
ARGS_PRESENT="$(printf '%s' "$HOOK_INPUT" | jq -r '((.tool_input.args // "") | length) > 0' 2>/dev/null || echo false)"

# Beacon URL defaults to prod; MC engineers can override to dev for verification
# work (e.g. against mcp.dev.getmontecarlo.com before promoting an endpoint change).
BEACON_URL="${MCD_TOOLKIT_BEACON_URL:-https://mcp.getmontecarlo.com/mcp/toolkit/beacon}"

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
