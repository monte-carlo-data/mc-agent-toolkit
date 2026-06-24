#!/usr/bin/env bash
# Sourceable helpers for the toolkit's local install identity.
#
# Shared by the SessionStart hook (ensure-toolkit-ids.sh) and the bake-editor
# install scripts (e.g. codex install.sh) so the install_id generated at install
# time and at session start is byte-identical: same path, same lowercase-v4
# format. Without this, a header baked at install time would carry a different
# install_id than the install beacon, and the anonymous and authed telemetry
# streams would not join on install_id.
#
# Canonical in plugins/shared/telemetry/lib/; synced per-plugin via
# `./scripts/bump-version.sh --sync-only`. SOURCE this file; do not execute it.

# ensure_install_id <ids_dir>
# Generate-or-read a stable install_id at <ids_dir>/install_id and echo it.
# First call generates a lowercase v4 UUID (uuidgen | tr) and chmod 600s it;
# later calls read the existing file. Echoes nothing on failure — the caller
# treats an empty result as "skip" (fail-open).
ensure_install_id() {
  local dir="$1"
  [ -n "$dir" ] || return 0
  mkdir -p "$dir" 2>/dev/null || return 0
  chmod 700 "$dir" 2>/dev/null || true
  # Regenerate when the file is missing OR empty (-s, not -f): a prior failed
  # write — e.g. uuidgen absent in a minimal container — can leave a zero-byte
  # file that must not permanently block generating a real id.
  if [ ! -s "$dir/install_id" ]; then
    uuidgen 2>/dev/null | tr '[:upper:]' '[:lower:]' > "$dir/install_id" 2>/dev/null || return 0
    # If generation produced nothing, don't leave an empty file behind.
    [ -s "$dir/install_id" ] || { rm -f "$dir/install_id" 2>/dev/null; return 0; }
    chmod 600 "$dir/install_id" 2>/dev/null || true
  fi
  cat "$dir/install_id" 2>/dev/null || true
}

# read_plugin_version <plugin_manifest_json>
# Echo the manifest's `.version`, or nothing if it can't be resolved (no jq,
# unreadable manifest, or no version field) — the caller omits the header rather
# than emitting a junk value.
read_plugin_version() {
  local manifest="$1"
  [ -n "$manifest" ] || return 0
  jq -r '.version // empty' "$manifest" 2>/dev/null || true
}
