#!/usr/bin/env bats

setup() {
  TEST_HOME="$(mktemp -d)"
  export HOME="$TEST_HOME"
  SCRIPT="$BATS_TEST_DIRNAME/../scripts/ensure-toolkit-ids.sh"
  IDS_DIR="$TEST_HOME/.claude/mc-agent-toolkit"

  # First run now fires the install beacon — mock curl so no real network calls
  # happen during tests, and run it synchronously for deterministic assertions.
  MOCK_BIN="$(mktemp -d)"
  cp "$BATS_TEST_DIRNAME/helpers/mock_curl.sh" "$MOCK_BIN/curl"
  chmod +x "$MOCK_BIN/curl"
  export PATH="$MOCK_BIN:$PATH"
  export MOCK_CURL_LOG="$(mktemp)"
  export MC_BEACON_SYNC=1
  unset MC_AGENT_TOOLKIT_TELEMETRY_DISABLED
  unset MCD_TOOLKIT_BEACON_URL
}

teardown() {
  rm -rf "$TEST_HOME" "$MOCK_BIN"
  rm -f "$MOCK_CURL_LOG"
}

@test "creates install_id and toolkit_session_id files" {
  run bash "$SCRIPT"
  [ "$status" -eq 0 ]
  [ -f "$TEST_HOME/.claude/mc-agent-toolkit/install_id" ]
  [ -f "$TEST_HOME/.claude/mc-agent-toolkit/toolkit_session_id" ]
}

@test "files contain lowercase UUIDs" {
  bash "$SCRIPT"
  install_id="$(cat "$TEST_HOME/.claude/mc-agent-toolkit/install_id")"
  toolkit_session_id="$(cat "$TEST_HOME/.claude/mc-agent-toolkit/toolkit_session_id")"
  [[ "$install_id" =~ ^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$ ]]
  [[ "$toolkit_session_id" =~ ^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$ ]]
}

@test "files have mode 600" {
  bash "$SCRIPT"
  perms_install="$(stat -f '%Lp' "$TEST_HOME/.claude/mc-agent-toolkit/install_id" 2>/dev/null || stat -c '%a' "$TEST_HOME/.claude/mc-agent-toolkit/install_id")"
  perms_session="$(stat -f '%Lp' "$TEST_HOME/.claude/mc-agent-toolkit/toolkit_session_id" 2>/dev/null || stat -c '%a' "$TEST_HOME/.claude/mc-agent-toolkit/toolkit_session_id")"
  [ "$perms_install" = "600" ]
  [ "$perms_session" = "600" ]
}

@test "install_id is stable across runs; toolkit_session_id rotates" {
  bash "$SCRIPT"
  install_first="$(cat "$TEST_HOME/.claude/mc-agent-toolkit/install_id")"
  session_first="$(cat "$TEST_HOME/.claude/mc-agent-toolkit/toolkit_session_id")"
  bash "$SCRIPT"
  install_second="$(cat "$TEST_HOME/.claude/mc-agent-toolkit/install_id")"
  session_second="$(cat "$TEST_HOME/.claude/mc-agent-toolkit/toolkit_session_id")"
  [ "$install_first" = "$install_second" ]
  [ "$session_first" != "$session_second" ]
}

@test "creates parent directory when absent" {
  rm -rf "$TEST_HOME/.claude"
  run bash "$SCRIPT"
  [ "$status" -eq 0 ]
  [ -d "$TEST_HOME/.claude/mc-agent-toolkit" ]
}

@test "exits 0 even when parent directory cannot be created" {
  # Make $HOME a regular file so mkdir -p $HOME/.claude/... must fail.
  rm -rf "$TEST_HOME"
  touch "$TEST_HOME"
  run bash "$SCRIPT"
  [ "$status" -eq 0 ]
}

@test "first run fires exactly one Toolkit Installed beacon" {
  run bash "$SCRIPT"
  [ "$status" -eq 0 ]
  [ -s "$MOCK_CURL_LOG" ]
  [ "$(wc -l < "$MOCK_CURL_LOG" | tr -d ' ')" = "1" ]
  payload="$(jq -r '.data' "$MOCK_CURL_LOG")"
  [ "$(echo "$payload" | jq -r '.event')" = "Toolkit Installed" ]
  [ "$(echo "$payload" | jq -r '.harness')" = "claude-code" ]
  [ "$(echo "$payload" | jq -r '.install_id')" = "$(cat "$IDS_DIR/install_id")" ]
  [ "$(echo "$payload" | jq -r '.session_id')" = "$(cat "$IDS_DIR/toolkit_session_id")" ]
}

@test "second run does not fire the install beacon (install_id already exists)" {
  bash "$SCRIPT"
  : > "$MOCK_CURL_LOG"   # clear the first-run beacon
  run bash "$SCRIPT"
  [ "$status" -eq 0 ]
  [ ! -s "$MOCK_CURL_LOG" ]
}

@test "re-fires the install beacon after install_id is deleted (marker wipe)" {
  bash "$SCRIPT"
  rm "$IDS_DIR/install_id"
  : > "$MOCK_CURL_LOG"
  run bash "$SCRIPT"
  [ "$status" -eq 0 ]
  [ -s "$MOCK_CURL_LOG" ]
  [ "$(jq -r '.data | fromjson.event' "$MOCK_CURL_LOG")" = "Toolkit Installed" ]
}

@test "toolkit_session_id is written even on the first (beacon-firing) run" {
  run bash "$SCRIPT"
  [ "$status" -eq 0 ]
  [ -f "$IDS_DIR/toolkit_session_id" ]
}
