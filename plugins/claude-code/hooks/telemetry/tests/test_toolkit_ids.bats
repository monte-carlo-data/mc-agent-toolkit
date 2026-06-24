#!/usr/bin/env bats
# Tests for the shared toolkit-ids.sh `ensure_install_id` (synced into each editor's
# hooks/telemetry/lib/). install_id is the telemetry join key, so a failed
# generation must never leave an empty file that permanently blocks regeneration.

setup() {
  TEST_HOME="$(mktemp -d)"
  IDS_DIR="$TEST_HOME/ids"
  # shellcheck source=/dev/null
  source "$BATS_TEST_DIRNAME/../lib/toolkit-ids.sh"
}

teardown() {
  rm -rf "$TEST_HOME"
}

@test "generates a stable lowercase v4 install_id (mode 600)" {
  id1="$(ensure_install_id "$IDS_DIR")"
  [[ "$id1" =~ ^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$ ]]
  perms="$(stat -f '%Lp' "$IDS_DIR/install_id" 2>/dev/null || stat -c '%a' "$IDS_DIR/install_id")"
  [ "$perms" = "600" ]
  [ "$(ensure_install_id "$IDS_DIR")" = "$id1" ]   # stable across calls
}

@test "creates the id dir mode 700" {
  ensure_install_id "$IDS_DIR" >/dev/null
  perms="$(stat -f '%Lp' "$IDS_DIR" 2>/dev/null || stat -c '%a' "$IDS_DIR")"
  [ "$perms" = "700" ]
}

@test "uuidgen unavailable (under pipefail): leaves NO empty install_id, recovers when uuidgen returns" {
  # Shadow uuidgen with a stub that produces nothing (simulates absence/failure).
  STUB="$(mktemp -d)"
  printf '#!/usr/bin/env bash\nexit 1\n' > "$STUB/uuidgen"
  chmod +x "$STUB/uuidgen"
  LIB="$BATS_TEST_DIRNAME/../lib/toolkit-ids.sh"

  # Run in the PRODUCTION shell context (set -uo pipefail, inherited from the
  # SessionStart hook) — bats `run` alone strips pipefail and wouldn't exercise
  # the pipeline-failure path.
  run env "PATH=$STUB:$PATH" bash -c "set -uo pipefail; source '$LIB'; ensure_install_id '$IDS_DIR'"
  [ "$status" -eq 0 ]                       # fail-open
  [ "$output" = "" ]                        # no id emitted
  [ ! -f "$IDS_DIR/install_id" ]            # crucial: no zero-byte file left behind

  rm -rf "$STUB"
  # uuidgen works again → a real (v4) id is generated, not permanently blocked.
  id="$(ensure_install_id "$IDS_DIR")"
  [[ "$id" =~ ^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$ ]]
}

@test "an existing EMPTY install_id is regenerated, not treated as valid" {
  mkdir -p "$IDS_DIR"
  : > "$IDS_DIR/install_id"                  # pre-existing zero-byte file
  id="$(ensure_install_id "$IDS_DIR")"
  [[ "$id" =~ ^[0-9a-f-]{36}$ ]]
  [ -s "$IDS_DIR/install_id" ]
}

@test "read_plugin_version returns the version, or empty when absent" {
  echo '{"version":"9.9.9"}' > "$TEST_HOME/p.json"
  [ "$(read_plugin_version "$TEST_HOME/p.json")" = "9.9.9" ]
  echo '{}' > "$TEST_HOME/p2.json"
  [ "$(read_plugin_version "$TEST_HOME/p2.json")" = "" ]
}
