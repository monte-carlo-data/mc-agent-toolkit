#!/usr/bin/env bats
# The install beacon fires once, at first-ever session start, carrying the
# "Toolkit Installed" event. It is editor-agnostic shared code synced from
# plugins/shared/telemetry/lib/; these tests exercise the Cursor copy.

setup() {
  TEST_HOME="$(mktemp -d)"
  export HOME="$TEST_HOME"
  IDS_DIR="$TEST_HOME/.cursor/mc-agent-toolkit"
  mkdir -p "$IDS_DIR"
  echo "11111111-1111-1111-1111-111111111111" > "$IDS_DIR/install_id"
  echo "22222222-2222-2222-2222-222222222222" > "$IDS_DIR/toolkit_session_id"

  # Mock curl on PATH
  MOCK_BIN="$(mktemp -d)"
  cp "$BATS_TEST_DIRNAME/helpers/mock_curl.sh" "$MOCK_BIN/curl"
  chmod +x "$MOCK_BIN/curl"
  export PATH="$MOCK_BIN:$PATH"
  export MOCK_CURL_LOG="$(mktemp)"

  SCRIPT="$BATS_TEST_DIRNAME/../lib/install-beacon.sh"
  MANIFEST="$BATS_TEST_DIRNAME/../../../.cursor-plugin/plugin.json"
  unset MC_AGENT_TOOLKIT_TELEMETRY_DISABLED
  unset MCD_TOOLKIT_BEACON_URL
  # Run curl synchronously so "no beacon" assertions are deterministic.
  export MC_BEACON_SYNC=1
}

teardown() {
  rm -rf "$TEST_HOME" "$MOCK_BIN"
  rm -f "$MOCK_CURL_LOG"
}

wait_for_log() {
  for _ in 1 2 3 4 5 6 7 8 9 10; do
    [[ -s "$MOCK_CURL_LOG" ]] && return 0
    sleep 0.05
  done
  return 1
}

@test "fires Toolkit Installed beacon with ids and cursor harness" {
  run bash "$SCRIPT" "$IDS_DIR" "$MANIFEST" "cursor"
  [ "$status" -eq 0 ]
  wait_for_log
  payload="$(jq -r '.data' "$MOCK_CURL_LOG")"
  [ "$(echo "$payload" | jq -r '.event')" = "Toolkit Installed" ]
  [ "$(echo "$payload" | jq -r '.install_id')" = "11111111-1111-1111-1111-111111111111" ]
  [ "$(echo "$payload" | jq -r '.session_id')" = "22222222-2222-2222-2222-222222222222" ]
  [ "$(echo "$payload" | jq -r '.harness')" = "cursor" ]
}

@test "install payload carries no skill fields" {
  bash "$SCRIPT" "$IDS_DIR" "$MANIFEST" "cursor"
  wait_for_log
  payload="$(jq -r '.data' "$MOCK_CURL_LOG")"
  [ "$(echo "$payload" | jq -r 'has("skill")')" = "false" ]
  [ "$(echo "$payload" | jq -r 'has("skill_args_present")')" = "false" ]
}

@test "payload includes toolkit_version from .cursor-plugin/plugin.json" {
  bash "$SCRIPT" "$IDS_DIR" "$MANIFEST" "cursor"
  wait_for_log
  payload="$(jq -r '.data' "$MOCK_CURL_LOG")"
  version="$(echo "$payload" | jq -r '.toolkit_version')"
  expected="$(jq -r '.version' "$MANIFEST")"
  [ "$version" = "$expected" ]
}

@test "opt-out env var suppresses beacon" {
  export MC_AGENT_TOOLKIT_TELEMETRY_DISABLED=1
  run bash "$SCRIPT" "$IDS_DIR" "$MANIFEST" "cursor"
  [ "$status" -eq 0 ]
  [ ! -s "$MOCK_CURL_LOG" ]
}

@test "missing install_id results in no beacon, exit 0" {
  rm "$IDS_DIR/install_id"
  run bash "$SCRIPT" "$IDS_DIR" "$MANIFEST" "cursor"
  [ "$status" -eq 0 ]
  [ ! -s "$MOCK_CURL_LOG" ]
}

@test "missing toolkit_session_id results in no beacon, exit 0" {
  rm "$IDS_DIR/toolkit_session_id"
  run bash "$SCRIPT" "$IDS_DIR" "$MANIFEST" "cursor"
  [ "$status" -eq 0 ]
  [ ! -s "$MOCK_CURL_LOG" ]
}

@test "curl is called with -m 2 and the prod beacon URL by default" {
  bash "$SCRIPT" "$IDS_DIR" "$MANIFEST" "cursor"
  wait_for_log
  argv="$(jq -c '.argv' "$MOCK_CURL_LOG")"
  echo "$argv" | grep -q '"-m"'
  echo "$argv" | grep -q '"2"'
  echo "$argv" | grep -q '"https://mcp.getmontecarlo.com/mcp/toolkit/beacon"'
}

@test "MCD_TOOLKIT_BEACON_URL overrides the default URL" {
  export MCD_TOOLKIT_BEACON_URL="https://mcp.dev.getmontecarlo.com/mcp/toolkit/beacon"
  bash "$SCRIPT" "$IDS_DIR" "$MANIFEST" "cursor"
  wait_for_log
  argv="$(jq -c '.argv' "$MOCK_CURL_LOG")"
  echo "$argv" | grep -q '"https://mcp.dev.getmontecarlo.com/mcp/toolkit/beacon"'
  ! echo "$argv" | grep -q '"https://mcp.getmontecarlo.com/mcp/toolkit/beacon"'
}

@test "backgrounded beacon (no MC_BEACON_SYNC) still fires" {
  # Exercise the production default path: ( curl ... ) & disown.
  unset MC_BEACON_SYNC
  bash "$SCRIPT" "$IDS_DIR" "$MANIFEST" "cursor"
  wait_for_log
  [ -s "$MOCK_CURL_LOG" ]
  [ "$(jq -r '.data | fromjson | .event' "$MOCK_CURL_LOG")" = "Toolkit Installed" ]
}

@test "does not fire when beacon_sent_version matches the current version" {
  echo "$(jq -r '.version' "$MANIFEST")" > "$IDS_DIR/beacon_sent_version"
  run bash "$SCRIPT" "$IDS_DIR" "$MANIFEST" "cursor"
  [ "$status" -eq 0 ]
  [ ! -s "$MOCK_CURL_LOG" ]
}

@test "re-fires and updates the marker when beacon_sent_version differs" {
  echo "0.0.0" > "$IDS_DIR/beacon_sent_version"
  bash "$SCRIPT" "$IDS_DIR" "$MANIFEST" "cursor"
  wait_for_log
  [ -s "$MOCK_CURL_LOG" ]
  [ "$(jq -r '.data | fromjson | .event' "$MOCK_CURL_LOG")" = "Toolkit Installed" ]
  [ "$(cat "$IDS_DIR/beacon_sent_version")" = "$(jq -r '.version' "$MANIFEST")" ]
}
