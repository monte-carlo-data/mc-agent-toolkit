#!/usr/bin/env bats
# Tests for the Copilot MCP registration (copilot-config.sh + shared toolkit-ids.sh).
# `copilot` is mocked (injected as the 5th arg) — a stub that logs its argv — so we
# assert the `copilot mcp add` invocation carries the right headers without needing
# the real CLI or network. Verifies the baked install_id matches ensure_install_id
# (the telemetry-join key), idempotent remove-then-add, and opt-out behavior.

setup() {
  TEST_HOME="$(mktemp -d)"
  export HOME="$TEST_HOME"
  IDS_DIR="$TEST_HOME/.copilot/mc-agent-toolkit"
  PLUGIN_JSON="$TEST_HOME/plugin.json"
  echo '{"version": "9.9.9"}' > "$PLUGIN_JSON"

  MOCK_DIR="$(mktemp -d)"
  MOCK_COPILOT="$MOCK_DIR/copilot"
  cat > "$MOCK_COPILOT" <<'EOF'
#!/usr/bin/env bash
echo "$*" >> "$MOCK_COPILOT_LOG"
EOF
  chmod +x "$MOCK_COPILOT"
  export MOCK_COPILOT_LOG="$MOCK_DIR/log"
  : > "$MOCK_COPILOT_LOG"

  # shellcheck source=/dev/null
  source "$BATS_TEST_DIRNAME/../../hooks/telemetry/lib/toolkit-ids.sh"
  # shellcheck source=/dev/null
  source "$BATS_TEST_DIRNAME/../lib/copilot-config.sh"

  unset MC_AGENT_TOOLKIT_TELEMETRY_DISABLED
}

teardown() {
  rm -rf "$TEST_HOME" "$MOCK_DIR"
}

cfg() {
  configure_copilot_mcp_server "monte-carlo-mcp" "https://x/mcp/toolkit" \
    "$IDS_DIR" "$PLUGIN_JSON" "$MOCK_COPILOT"
}

@test "registers the remote server with install_id + version headers" {
  cfg
  grep -q 'mcp add --transport http monte-carlo-mcp https://x/mcp/toolkit' "$MOCK_COPILOT_LOG"
  id="$(cat "$IDS_DIR/install_id")"
  [[ "$id" =~ ^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$ ]]
  grep -q "x-mcd-toolkit-install-id: $id" "$MOCK_COPILOT_LOG"
  grep -q 'x-mcd-toolkit-version: 9.9.9' "$MOCK_COPILOT_LOG"
}

@test "baked install_id equals ensure_install_id (the join key)" {
  cfg
  grep -q "x-mcd-toolkit-install-id: $(ensure_install_id "$IDS_DIR")" "$MOCK_COPILOT_LOG"
}

@test "removes the existing entry first (idempotent migrate on reinstall)" {
  cfg
  grep -q 'mcp remove monte-carlo-mcp' "$MOCK_COPILOT_LOG"
  # add comes after remove
  remove_line="$(grep -n 'mcp remove' "$MOCK_COPILOT_LOG" | head -1 | cut -d: -f1)"
  add_line="$(grep -n 'mcp add' "$MOCK_COPILOT_LOG" | head -1 | cut -d: -f1)"
  [ "$remove_line" -lt "$add_line" ]
}

@test "opt-out omits the install-id header (version still rides)" {
  export MC_AGENT_TOOLKIT_TELEMETRY_DISABLED=1
  cfg
  ! grep -q 'x-mcd-toolkit-install-id' "$MOCK_COPILOT_LOG"
  grep -q 'x-mcd-toolkit-version: 9.9.9' "$MOCK_COPILOT_LOG"
}

@test "no-op (fail-open) when the copilot CLI is unavailable" {
  configure_copilot_mcp_server "monte-carlo-mcp" "https://x/mcp/toolkit" \
    "$IDS_DIR" "$PLUGIN_JSON" "/nonexistent/copilot-binary"
  [ ! -s "$MOCK_COPILOT_LOG" ]
}
