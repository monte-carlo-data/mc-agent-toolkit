#!/usr/bin/env bats
# Tests for the Cursor MCP-config bake (cursor-config.sh + shared toolkit-ids.sh).
# Verifies the install_id baked into mcp.json matches what the SessionStart hook
# helper produces (the telemetry-join key), that the write is idempotent and valid
# JSON, preserves the url, and that opt-out suppresses the install-id header.

setup() {
  TEST_HOME="$(mktemp -d)"
  export HOME="$TEST_HOME"
  IDS_DIR="$TEST_HOME/.cursor/mc-agent-toolkit"
  MCP_JSON="$TEST_HOME/mcp.json"
  cat > "$MCP_JSON" <<'JSON'
{
  "mcpServers": {
    "monte-carlo-mcp": {
      "url": "https://mcp.getmontecarlo.com/mcp/toolkit"
    }
  }
}
JSON

  PLUGIN_JSON="$TEST_HOME/plugin.json"
  echo '{"version": "9.9.9"}' > "$PLUGIN_JSON"

  # shellcheck source=/dev/null
  source "$BATS_TEST_DIRNAME/../../hooks/telemetry/lib/toolkit-ids.sh"
  # shellcheck source=/dev/null
  source "$BATS_TEST_DIRNAME/../lib/cursor-config.sh"

  unset MC_AGENT_TOOLKIT_TELEMETRY_DISABLED
}

teardown() {
  rm -rf "$TEST_HOME"
}

cfg() {
  configure_cursor_mcp_headers "$MCP_JSON" "monte-carlo-mcp" "$IDS_DIR" "$PLUGIN_JSON"
}

@test "fresh install bakes a valid v4 install_id header and the version" {
  cfg
  jq -e . "$MCP_JSON" >/dev/null   # still valid JSON
  id="$(jq -r '.mcpServers["monte-carlo-mcp"].headers["x-mcd-toolkit-install-id"]' "$MCP_JSON")"
  [[ "$id" =~ ^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$ ]]
  [ "$(jq -r '.mcpServers["monte-carlo-mcp"].headers["x-mcd-toolkit-version"]' "$MCP_JSON")" = "9.9.9" ]
}

@test "baked install_id equals what ensure_install_id reads (the join key)" {
  cfg
  baked="$(jq -r '.mcpServers["monte-carlo-mcp"].headers["x-mcd-toolkit-install-id"]' "$MCP_JSON")"
  [ "$baked" = "$(ensure_install_id "$IDS_DIR")" ]
}

@test "preserves the server url" {
  cfg
  [ "$(jq -r '.mcpServers["monte-carlo-mcp"].url' "$MCP_JSON")" = "https://mcp.getmontecarlo.com/mcp/toolkit" ]
}

@test "idempotent re-run: refreshes version, stable install_id, still valid JSON" {
  cfg
  id1="$(jq -r '.mcpServers["monte-carlo-mcp"].headers["x-mcd-toolkit-install-id"]' "$MCP_JSON")"
  echo '{"version": "10.0.0"}' > "$PLUGIN_JSON"
  cfg
  jq -e . "$MCP_JSON" >/dev/null
  [ "$(jq -r '.mcpServers["monte-carlo-mcp"].headers["x-mcd-toolkit-version"]' "$MCP_JSON")" = "10.0.0" ]
  [ "$(jq -r '.mcpServers["monte-carlo-mcp"].headers["x-mcd-toolkit-install-id"]' "$MCP_JSON")" = "$id1" ]
}

@test "opt-out bakes no install-id header (version still rides)" {
  export MC_AGENT_TOOLKIT_TELEMETRY_DISABLED=1
  cfg
  [ "$(jq -r '.mcpServers["monte-carlo-mcp"].headers | has("x-mcd-toolkit-install-id")' "$MCP_JSON")" = "false" ]
  [ "$(jq -r '.mcpServers["monte-carlo-mcp"].headers["x-mcd-toolkit-version"]' "$MCP_JSON")" = "9.9.9" ]
}

@test "opt-out + unresolvable version omits the headers object entirely" {
  export MC_AGENT_TOOLKIT_TELEMETRY_DISABLED=1
  echo '{}' > "$PLUGIN_JSON"
  cfg
  [ "$(jq -r '.mcpServers["monte-carlo-mcp"] | has("headers")' "$MCP_JSON")" = "false" ]
}
