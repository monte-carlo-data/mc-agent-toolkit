#!/usr/bin/env bats
# Tests for the Codex MCP-config bake (codex-config.sh + shared toolkit-ids.sh).
# Verifies that the install_id baked into config.toml matches what the SessionStart
# hook helper produces (the telemetry-join key), that the write is idempotent on
# re-run, and that opt-out suppresses the install-id header.

setup() {
  TEST_HOME="$(mktemp -d)"
  export HOME="$TEST_HOME"
  IDS_DIR="$TEST_HOME/.codex/mc-agent-toolkit"
  CONFIG="$TEST_HOME/.codex/config.toml"
  mkdir -p "$TEST_HOME/.codex"

  # A fake plugin manifest with a known version.
  PLUGIN_JSON="$TEST_HOME/plugin.json"
  echo '{"version": "9.9.9"}' > "$PLUGIN_JSON"

  # shellcheck source=/dev/null
  source "$BATS_TEST_DIRNAME/../../hooks/telemetry/lib/toolkit-ids.sh"
  # shellcheck source=/dev/null
  source "$BATS_TEST_DIRNAME/../lib/codex-config.sh"

  unset MC_AGENT_TOOLKIT_TELEMETRY_DISABLED
}

teardown() {
  rm -rf "$TEST_HOME"
}

@test "fresh install bakes a valid v4 install_id header and the version" {
  configure_codex_mcp_server "$CONFIG" "monte-carlo-mcp" "https://x/mcp/toolkit" "$IDS_DIR" "$PLUGIN_JSON"
  grep -q '^\[mcp_servers\.monte-carlo-mcp\]' "$CONFIG"
  id="$(grep -o 'x-mcd-toolkit-install-id" = "[0-9a-f-]*"' "$CONFIG" | grep -o '[0-9a-f]\{8\}-[0-9a-f]\{4\}-[0-9a-f]\{4\}-[0-9a-f]\{4\}-[0-9a-f]\{12\}')"
  [[ "$id" =~ ^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$ ]]
  grep -q 'x-mcd-toolkit-version" = "9.9.9"' "$CONFIG"
  grep -q 'User-Agent" = "codex-mcp/1.0"' "$CONFIG"
}

@test "baked install_id equals what ensure_install_id reads (the join key)" {
  configure_codex_mcp_server "$CONFIG" "monte-carlo-mcp" "https://x/mcp/toolkit" "$IDS_DIR" "$PLUGIN_JSON"
  baked="$(grep -o 'x-mcd-toolkit-install-id" = "[0-9a-f-]*"' "$CONFIG" | grep -o '[0-9a-f-]\{36\}')"
  from_helper="$(ensure_install_id "$IDS_DIR")"
  [ "$baked" = "$from_helper" ]
}

@test "re-run is idempotent: rewrites in place, no duplicate block or header" {
  configure_codex_mcp_server "$CONFIG" "monte-carlo-mcp" "https://x/mcp/toolkit" "$IDS_DIR" "$PLUGIN_JSON"
  # bump the version to simulate an upgrade, then re-run
  echo '{"version": "10.0.0"}' > "$PLUGIN_JSON"
  configure_codex_mcp_server "$CONFIG" "monte-carlo-mcp" "https://x/mcp/toolkit" "$IDS_DIR" "$PLUGIN_JSON"
  [ "$(grep -c '^\[mcp_servers\.monte-carlo-mcp\]' "$CONFIG")" -eq 1 ]
  [ "$(grep -c '^http_headers' "$CONFIG")" -eq 1 ]
  grep -q 'x-mcd-toolkit-version" = "10.0.0"' "$CONFIG"   # refreshed
  ! grep -q '9.9.9' "$CONFIG"                              # old version gone
}

@test "installer owns the block: a stale url is migrated to canonical on re-run" {
  # Simulate a pre-existing block with an old/different url.
  printf '\n[mcp_servers.monte-carlo-mcp]\nurl = "https://old.example.com/mcp"\nenabled = true\nhttp_headers = { "User-Agent" = "x" }\n' > "$CONFIG"
  configure_codex_mcp_server "$CONFIG" "monte-carlo-mcp" "https://mcp.dev.getmontecarlo.com/mcp/toolkit" "$IDS_DIR" "$PLUGIN_JSON"
  grep -q 'url = "https://mcp.dev.getmontecarlo.com/mcp/toolkit"' "$CONFIG"   # migrated
  ! grep -q 'old.example.com' "$CONFIG"                                       # stale url gone
  [ "$(grep -c '^\[mcp_servers\.monte-carlo-mcp\]' "$CONFIG")" -eq 1 ]        # not duplicated
}

@test "leaves other sections untouched while rewriting our block" {
  printf '[other]\nfoo = "bar"\n\n[mcp_servers.monte-carlo-mcp]\nurl = "https://old/mcp"\nenabled = true\nhttp_headers = { }\n' > "$CONFIG"
  configure_codex_mcp_server "$CONFIG" "monte-carlo-mcp" "https://x/mcp/toolkit" "$IDS_DIR" "$PLUGIN_JSON"
  grep -q '^\[other\]' "$CONFIG"
  grep -q 'foo = "bar"' "$CONFIG"
  grep -q 'url = "https://x/mcp/toolkit"' "$CONFIG"   # our block rewritten to canonical
  [ "$(grep -c '^\[mcp_servers\.monte-carlo-mcp\]' "$CONFIG")" -eq 1 ]
}

@test "opt-out bakes no install-id header (version still rides)" {
  export MC_AGENT_TOOLKIT_TELEMETRY_DISABLED=1
  configure_codex_mcp_server "$CONFIG" "monte-carlo-mcp" "https://x/mcp/toolkit" "$IDS_DIR" "$PLUGIN_JSON"
  ! grep -q 'x-mcd-toolkit-install-id' "$CONFIG"
  grep -q 'x-mcd-toolkit-version" = "9.9.9"' "$CONFIG"
}

@test "unresolvable version omits the version header" {
  echo '{}' > "$PLUGIN_JSON"   # no .version
  configure_codex_mcp_server "$CONFIG" "monte-carlo-mcp" "https://x/mcp/toolkit" "$IDS_DIR" "$PLUGIN_JSON"
  ! grep -q 'x-mcd-toolkit-version' "$CONFIG"
  grep -q 'User-Agent" = "codex-mcp/1.0"' "$CONFIG"
}
