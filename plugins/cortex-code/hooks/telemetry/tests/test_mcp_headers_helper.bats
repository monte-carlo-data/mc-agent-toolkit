#!/usr/bin/env bats
# Tests for mcp-headers-helper.py — the headersHelper that emits toolkit
# telemetry headers (x-mcd-toolkit-install-id / -session-id / -version) on
# authed MCP traffic. The helper reads id files from its OWN directory, so each
# test copies it into a temp dir alongside fixture files and runs it there.

INSTALL_ID="11111111-1111-4111-8111-111111111111"
SESSION_ID="22222222-2222-4222-8222-222222222222"
VERSION="1.13.2"

setup() {
  IDS_DIR="$(mktemp -d)"
  HELPER="$IDS_DIR/mcp-headers-helper.py"
  cp "$BATS_TEST_DIRNAME/../lib/mcp-headers-helper.py" "$HELPER"
  unset MC_AGENT_TOOLKIT_TELEMETRY_DISABLED
}

teardown() {
  rm -rf "$IDS_DIR"
}

write_all_ids() {
  printf '%s' "$INSTALL_ID" > "$IDS_DIR/install_id"
  printf '%s' "$SESSION_ID" > "$IDS_DIR/toolkit_session_id"
  printf '%s' "$VERSION" > "$IDS_DIR/toolkit_version"
}

@test "emits all three headers, by name, with the file contents as values" {
  write_all_ids
  run python3 "$HELPER"
  [ "$status" -eq 0 ]
  [ "$(echo "$output" | jq -r '."x-mcd-toolkit-install-id"')" = "$INSTALL_ID" ]
  [ "$(echo "$output" | jq -r '."x-mcd-toolkit-session-id"')" = "$SESSION_ID" ]
  [ "$(echo "$output" | jq -r '."x-mcd-toolkit-version"')" = "$VERSION" ]
}

@test "omits session header (not null) when toolkit_session_id file is absent" {
  printf '%s' "$INSTALL_ID" > "$IDS_DIR/install_id"
  printf '%s' "$VERSION" > "$IDS_DIR/toolkit_version"
  run python3 "$HELPER"
  [ "$status" -eq 0 ]
  [ "$(echo "$output" | jq -r '."x-mcd-toolkit-install-id"')" = "$INSTALL_ID" ]
  [ "$(echo "$output" | jq 'has("x-mcd-toolkit-session-id")')" = "false" ]
}

@test "omits header for an empty file" {
  printf '%s' "$INSTALL_ID" > "$IDS_DIR/install_id"
  printf '' > "$IDS_DIR/toolkit_session_id"
  run python3 "$HELPER"
  [ "$status" -eq 0 ]
  [ "$(echo "$output" | jq 'has("x-mcd-toolkit-session-id")')" = "false" ]
}

@test "opt-out emits an empty object" {
  write_all_ids
  export MC_AGENT_TOOLKIT_TELEMETRY_DISABLED=1
  run python3 "$HELPER"
  [ "$status" -eq 0 ]
  [ "$output" = "{}" ]
}

@test "no id files present: emits empty object, exit 0" {
  run python3 "$HELPER"
  [ "$status" -eq 0 ]
  [ "$output" = "{}" ]
}

@test "output is always valid JSON" {
  write_all_ids
  run python3 "$HELPER"
  echo "$output" | jq -e . >/dev/null
}
