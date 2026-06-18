#!/usr/bin/env bats
# Cortex delivers the invoked skill as tool_input.command = "<plugin>:<skill>"
# (not tool_input.skill), and the command field is shared with other tools, so the
# beacon guards on tool_name == "skill". These tests exercise that contract.

setup() {
  TEST_HOME="$(mktemp -d)"
  export HOME="$TEST_HOME"
  IDS_DIR="$TEST_HOME/.snowflake/cortex/mc-agent-toolkit"
  mkdir -p "$IDS_DIR"
  echo "11111111-1111-1111-1111-111111111111" > "$IDS_DIR/install_id"
  echo "22222222-2222-2222-2222-222222222222" > "$IDS_DIR/toolkit_session_id"

  # Mock curl on PATH
  MOCK_BIN="$(mktemp -d)"
  cp "$BATS_TEST_DIRNAME/helpers/mock_curl.sh" "$MOCK_BIN/curl"
  chmod +x "$MOCK_BIN/curl"
  export PATH="$MOCK_BIN:$PATH"
  export MOCK_CURL_LOG="$(mktemp)"

  SCRIPT="$BATS_TEST_DIRNAME/../scripts/skill-beacon.sh"
  unset MC_AGENT_TOOLKIT_TELEMETRY_DISABLED
  unset MCD_TOOLKIT_BEACON_URL
  # Run the beacon's curl synchronously so "no beacon" assertions are deterministic
  # (no reliance on a fixed sleep racing a backgrounded curl).
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

@test "fires beacon for plugin-namespaced toolkit skill (Cortex command field)" {
  echo '{"tool_name":"skill","tool_input":{"command":"mc-agent-toolkit:monte-carlo-asset-health"}}' | bash "$SCRIPT"
  wait_for_log
  payload="$(jq -r '.data' "$MOCK_CURL_LOG")"
  [ "$(echo "$payload" | jq -r '.event')" = "Toolkit Skill Invoked" ]
  [ "$(echo "$payload" | jq -r '.skill')" = "mc-agent-toolkit:monte-carlo-asset-health" ]
  [ "$(echo "$payload" | jq -r '.install_id')" = "11111111-1111-1111-1111-111111111111" ]
  [ "$(echo "$payload" | jq -r '.session_id')" = "22222222-2222-2222-2222-222222222222" ]
  [ "$(echo "$payload" | jq -r '.harness')" = "cortex-code" ]
}

@test "no beacon for skills outside mc-agent-toolkit" {
  run bash -c 'echo "{\"tool_name\":\"skill\",\"tool_input\":{\"command\":\"some-plugin:other-skill\"}}" | bash "$0"' "$SCRIPT"
  [ "$status" -eq 0 ]
  [ ! -s "$MOCK_CURL_LOG" ]
}

@test "no beacon for namespaced skills from other plugins" {
  run bash -c 'echo "{\"tool_name\":\"skill\",\"tool_input\":{\"command\":\"superpowers:brainstorming\"}}" | bash "$0"' "$SCRIPT"
  [ "$status" -eq 0 ]
  [ ! -s "$MOCK_CURL_LOG" ]
}

@test "non-skill tool does not beacon even when its command matches our namespace" {
  # A Bash tool whose command starts with our plugin namespace must NOT beacon —
  # the tool_name guard rejects it before the namespace check.
  run bash -c 'echo "{\"tool_name\":\"bash\",\"tool_input\":{\"command\":\"mc-agent-toolkit:monte-carlo-prevent\"}}" | bash "$0"' "$SCRIPT"
  [ "$status" -eq 0 ]
  [ ! -s "$MOCK_CURL_LOG" ]
}

@test "opt-out env var suppresses beacon" {
  export MC_AGENT_TOOLKIT_TELEMETRY_DISABLED=1
  run bash -c 'echo "{\"tool_name\":\"skill\",\"tool_input\":{\"command\":\"mc-agent-toolkit:monte-carlo-asset-health\"}}" | bash "$0"' "$SCRIPT"
  [ "$status" -eq 0 ]
  [ ! -s "$MOCK_CURL_LOG" ]
}

@test "missing install_id file results in no beacon, exit 0" {
  rm "$IDS_DIR/install_id"
  run bash -c 'echo "{\"tool_name\":\"skill\",\"tool_input\":{\"command\":\"mc-agent-toolkit:monte-carlo-asset-health\"}}" | bash "$0"' "$SCRIPT"
  [ "$status" -eq 0 ]
  [ ! -s "$MOCK_CURL_LOG" ]
}

@test "missing toolkit_session_id file results in no beacon, exit 0" {
  rm "$IDS_DIR/toolkit_session_id"
  run bash -c 'echo "{\"tool_name\":\"skill\",\"tool_input\":{\"command\":\"mc-agent-toolkit:monte-carlo-asset-health\"}}" | bash "$0"' "$SCRIPT"
  [ "$status" -eq 0 ]
  [ ! -s "$MOCK_CURL_LOG" ]
}

@test "missing tool_input.command results in no beacon, exit 0" {
  run bash -c 'echo "{\"tool_name\":\"skill\",\"tool_input\":{}}" | bash "$0"' "$SCRIPT"
  [ "$status" -eq 0 ]
  [ ! -s "$MOCK_CURL_LOG" ]
}

@test "skill_args_present is false (Cortex omits invocation args)" {
  echo '{"tool_name":"skill","tool_input":{"command":"mc-agent-toolkit:monte-carlo-asset-health"}}' | bash "$SCRIPT"
  wait_for_log
  payload="$(jq -r '.data' "$MOCK_CURL_LOG")"
  [ "$(echo "$payload" | jq -r '.skill_args_present')" = "false" ]
}

@test "payload includes toolkit_version from .cortex-plugin/plugin.json" {
  echo '{"tool_name":"skill","tool_input":{"command":"mc-agent-toolkit:monte-carlo-asset-health"}}' | bash "$SCRIPT"
  wait_for_log
  payload="$(jq -r '.data' "$MOCK_CURL_LOG")"
  version="$(echo "$payload" | jq -r '.toolkit_version')"
  expected="$(jq -r '.version' "$BATS_TEST_DIRNAME/../../../.cortex-plugin/plugin.json")"
  [ "$version" = "$expected" ]
}

@test "curl is called with -m 2 and the prod beacon URL by default" {
  echo '{"tool_name":"skill","tool_input":{"command":"mc-agent-toolkit:monte-carlo-asset-health"}}' | bash "$SCRIPT"
  wait_for_log
  argv="$(jq -c '.argv' "$MOCK_CURL_LOG")"
  echo "$argv" | grep -q '"-m"'
  echo "$argv" | grep -q '"2"'
  echo "$argv" | grep -q '"https://mcp.getmontecarlo.com/mcp/toolkit/beacon"'
}

@test "MCD_TOOLKIT_BEACON_URL overrides the default URL" {
  export MCD_TOOLKIT_BEACON_URL="https://mcp.dev.getmontecarlo.com/mcp/toolkit/beacon"
  echo '{"tool_name":"skill","tool_input":{"command":"mc-agent-toolkit:monte-carlo-asset-health"}}' | bash "$SCRIPT"
  wait_for_log
  argv="$(jq -c '.argv' "$MOCK_CURL_LOG")"
  echo "$argv" | grep -q '"https://mcp.dev.getmontecarlo.com/mcp/toolkit/beacon"'
  ! echo "$argv" | grep -q '"https://mcp.getmontecarlo.com/mcp/toolkit/beacon"'
}
