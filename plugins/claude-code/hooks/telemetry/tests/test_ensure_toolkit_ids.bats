#!/usr/bin/env bats

setup() {
  TEST_HOME="$(mktemp -d)"
  export HOME="$TEST_HOME"
  SCRIPT="$BATS_TEST_DIRNAME/../scripts/ensure-toolkit-ids.sh"
}

teardown() {
  rm -rf "$TEST_HOME"
}

@test "creates install_id and session_id files" {
  run bash "$SCRIPT"
  [ "$status" -eq 0 ]
  [ -f "$TEST_HOME/.claude/mc-agent-toolkit/install_id" ]
  [ -f "$TEST_HOME/.claude/mc-agent-toolkit/session_id" ]
}

@test "files contain lowercase UUIDs" {
  bash "$SCRIPT"
  install_id="$(cat "$TEST_HOME/.claude/mc-agent-toolkit/install_id")"
  session_id="$(cat "$TEST_HOME/.claude/mc-agent-toolkit/session_id")"
  [[ "$install_id" =~ ^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$ ]]
  [[ "$session_id" =~ ^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$ ]]
}

@test "files have mode 600" {
  bash "$SCRIPT"
  perms_install="$(stat -f '%Lp' "$TEST_HOME/.claude/mc-agent-toolkit/install_id" 2>/dev/null || stat -c '%a' "$TEST_HOME/.claude/mc-agent-toolkit/install_id")"
  perms_session="$(stat -f '%Lp' "$TEST_HOME/.claude/mc-agent-toolkit/session_id" 2>/dev/null || stat -c '%a' "$TEST_HOME/.claude/mc-agent-toolkit/session_id")"
  [ "$perms_install" = "600" ]
  [ "$perms_session" = "600" ]
}

@test "install_id is stable across runs; session_id rotates" {
  bash "$SCRIPT"
  install_first="$(cat "$TEST_HOME/.claude/mc-agent-toolkit/install_id")"
  session_first="$(cat "$TEST_HOME/.claude/mc-agent-toolkit/session_id")"
  bash "$SCRIPT"
  install_second="$(cat "$TEST_HOME/.claude/mc-agent-toolkit/install_id")"
  session_second="$(cat "$TEST_HOME/.claude/mc-agent-toolkit/session_id")"
  [ "$install_first" = "$install_second" ]
  [ "$session_first" != "$session_second" ]
}

@test "creates parent directory when absent" {
  rm -rf "$TEST_HOME/.claude"
  run bash "$SCRIPT"
  [ "$status" -eq 0 ]
  [ -d "$TEST_HOME/.claude/mc-agent-toolkit" ]
}
