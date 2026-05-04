#!/usr/bin/env bats

setup() {
  TEST_HOME="$(mktemp -d)"
  export HOME="$TEST_HOME"
  IDS_DIR="$TEST_HOME/.claude/mc-agent-toolkit"
  mkdir -p "$IDS_DIR"
  echo "11111111-1111-1111-1111-111111111111" > "$IDS_DIR/install_id"
  echo "22222222-2222-2222-2222-222222222222" > "$IDS_DIR/session_id"

  # Mock curl on PATH
  MOCK_BIN="$(mktemp -d)"
  cp "$BATS_TEST_DIRNAME/helpers/mock_curl.sh" "$MOCK_BIN/curl"
  chmod +x "$MOCK_BIN/curl"
  export PATH="$MOCK_BIN:$PATH"
  export MOCK_CURL_LOG="$(mktemp)"

  SCRIPT="$BATS_TEST_DIRNAME/../scripts/skill-beacon.sh"
  unset MCD_TOOLKIT_TELEMETRY_DISABLED
  unset MCD_TOOLKIT_BEACON_URL
}

teardown() {
  rm -rf "$TEST_HOME" "$MOCK_BIN"
  rm -f "$MOCK_CURL_LOG"
}

# Helper: wait briefly for the backgrounded curl to flush its log line.
wait_for_log() {
  for _ in 1 2 3 4 5 6 7 8 9 10; do
    [[ -s "$MOCK_CURL_LOG" ]] && return 0
    sleep 0.05
  done
  return 1
}

@test "fires beacon with correct skill name" {
  echo '{"tool_name":"Skill","tool_input":{"skill":"start-work","args":""}}' | bash "$SCRIPT"
  wait_for_log
  payload="$(jq -r '.data' "$MOCK_CURL_LOG")"
  [ "$(echo "$payload" | jq -r '.event')" = "Toolkit Skill Invoked" ]
  [ "$(echo "$payload" | jq -r '.skill')" = "start-work" ]
  [ "$(echo "$payload" | jq -r '.install_id')" = "11111111-1111-1111-1111-111111111111" ]
  [ "$(echo "$payload" | jq -r '.session_id')" = "22222222-2222-2222-2222-222222222222" ]
}

@test "skill_args_present is true when args non-empty" {
  echo '{"tool_name":"Skill","tool_input":{"skill":"hack","args":"phase 2"}}' | bash "$SCRIPT"
  wait_for_log
  payload="$(jq -r '.data' "$MOCK_CURL_LOG")"
  [ "$(echo "$payload" | jq -r '.skill_args_present')" = "true" ]
}

@test "skill_args_present is false when args empty or missing" {
  echo '{"tool_name":"Skill","tool_input":{"skill":"hack"}}' | bash "$SCRIPT"
  wait_for_log
  payload="$(jq -r '.data' "$MOCK_CURL_LOG")"
  [ "$(echo "$payload" | jq -r '.skill_args_present')" = "false" ]
}

@test "skill_args_present is false when args is empty string" {
  echo '{"tool_name":"Skill","tool_input":{"skill":"hack","args":""}}' | bash "$SCRIPT"
  wait_for_log
  payload="$(jq -r '.data' "$MOCK_CURL_LOG")"
  [ "$(echo "$payload" | jq -r '.skill_args_present')" = "false" ]
}

@test "payload never contains args content" {
  echo '{"tool_name":"Skill","tool_input":{"skill":"hack","args":"SECRET-PROMPT-TEXT"}}' | bash "$SCRIPT"
  wait_for_log
  # Search the raw log (covers argv, headers, body — every field mock_curl captured),
  # not just .data, so any future leak path is caught.
  ! grep -q "SECRET-PROMPT-TEXT" "$MOCK_CURL_LOG"
}

@test "opt-out env var suppresses beacon" {
  export MCD_TOOLKIT_TELEMETRY_DISABLED=1
  run bash -c 'echo "{\"tool_name\":\"Skill\",\"tool_input\":{\"skill\":\"x\"}}" | bash "$0"' "$SCRIPT"
  [ "$status" -eq 0 ]
  sleep 0.2
  [ ! -s "$MOCK_CURL_LOG" ]
}

@test "missing install_id file results in no beacon, exit 0" {
  rm "$IDS_DIR/install_id"
  run bash -c 'echo "{\"tool_name\":\"Skill\",\"tool_input\":{\"skill\":\"x\"}}" | bash "$0"' "$SCRIPT"
  [ "$status" -eq 0 ]
  sleep 0.2
  [ ! -s "$MOCK_CURL_LOG" ]
}

@test "missing session_id file results in no beacon, exit 0" {
  rm "$IDS_DIR/session_id"
  run bash -c 'echo "{\"tool_name\":\"Skill\",\"tool_input\":{\"skill\":\"x\"}}" | bash "$0"' "$SCRIPT"
  [ "$status" -eq 0 ]
  sleep 0.2
  [ ! -s "$MOCK_CURL_LOG" ]
}

@test "missing tool_input.skill results in no beacon, exit 0" {
  run bash -c 'echo "{\"tool_name\":\"Skill\",\"tool_input\":{}}" | bash "$0"' "$SCRIPT"
  [ "$status" -eq 0 ]
  sleep 0.2
  [ ! -s "$MOCK_CURL_LOG" ]
}

@test "non-skill tool input results in no beacon, exit 0" {
  run bash -c 'echo "{\"tool_name\":\"Bash\",\"tool_input\":{\"command\":\"ls\"}}" | bash "$0"' "$SCRIPT"
  [ "$status" -eq 0 ]
  sleep 0.2
  [ ! -s "$MOCK_CURL_LOG" ]
}

@test "payload includes toolkit_version from plugin.json" {
  echo '{"tool_name":"Skill","tool_input":{"skill":"x"}}' | bash "$SCRIPT"
  wait_for_log
  payload="$(jq -r '.data' "$MOCK_CURL_LOG")"
  version="$(echo "$payload" | jq -r '.toolkit_version')"
  expected="$(jq -r '.version' "$BATS_TEST_DIRNAME/../../../.claude-plugin/plugin.json")"
  [ "$version" = "$expected" ]
}

@test "curl is called with -m 2 and the prod beacon URL by default" {
  echo '{"tool_name":"Skill","tool_input":{"skill":"x"}}' | bash "$SCRIPT"
  wait_for_log
  argv="$(jq -c '.argv' "$MOCK_CURL_LOG")"
  echo "$argv" | grep -q '"-m"'
  echo "$argv" | grep -q '"2"'
  echo "$argv" | grep -q '"https://mcp.getmontecarlo.com/mcp/toolkit/beacon"'
}

@test "MCD_TOOLKIT_BEACON_URL overrides the default URL" {
  export MCD_TOOLKIT_BEACON_URL="https://mcp.dev.getmontecarlo.com/mcp/toolkit/beacon"
  echo '{"tool_name":"Skill","tool_input":{"skill":"x"}}' | bash "$SCRIPT"
  wait_for_log
  argv="$(jq -c '.argv' "$MOCK_CURL_LOG")"
  echo "$argv" | grep -q '"https://mcp.dev.getmontecarlo.com/mcp/toolkit/beacon"'
  ! echo "$argv" | grep -q '"https://mcp.getmontecarlo.com/mcp/toolkit/beacon"'
}
