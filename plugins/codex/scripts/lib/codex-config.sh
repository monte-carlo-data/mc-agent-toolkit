#!/usr/bin/env bash
# Sourceable helper for writing the Monte Carlo MCP server block into Codex's
# ~/.codex/config.toml. Codex's MCP config supports only static http_headers (no
# dynamic headersHelper), so the toolkit's install_id and version are baked in at
# install time. install_id is generated via the shared `ensure_install_id` so it
# matches the SessionStart hook's id and the telemetry streams join.
#
# Codex-specific (TOML) and lives outside hooks/, so it is NOT part of the
# shared-lib sync. SOURCE this file; requires toolkit-ids.sh to be sourced first
# (for ensure_install_id / read_plugin_version).

# build_codex_http_headers <ids_dir> <plugin_json>
# Echo the full `http_headers = { ... }` TOML line. Always carries User-Agent and
# (when resolvable) x-mcd-toolkit-version. Carries x-mcd-toolkit-install-id unless
# telemetry is opted out at install time (MC_AGENT_TOOLKIT_TELEMETRY_DISABLED=1).
build_codex_http_headers() {
  local ids_dir="$1" plugin_json="$2"
  local headers='"User-Agent" = "codex-mcp/1.0"'

  local version
  version="$(read_plugin_version "$plugin_json")"
  [ -n "$version" ] && headers="$headers, \"x-mcd-toolkit-version\" = \"$version\""

  if [ "${MC_AGENT_TOOLKIT_TELEMETRY_DISABLED:-}" != "1" ]; then
    local install_id
    install_id="$(ensure_install_id "$ids_dir")"
    [ -n "$install_id" ] && headers="$headers, \"x-mcd-toolkit-install-id\" = \"$install_id\""
  fi

  printf 'http_headers = { %s }' "$headers"
}

# configure_codex_mcp_server <config_file> <server_name> <server_url> <ids_dir> <plugin_json>
# Write the canonical [mcp_servers.<name>] block. This installer OWNS that block:
# if it already exists it is stripped and rewritten (url + enabled + http_headers),
# so a later endpoint change or header update migrates existing users on
# reinstall/upgrade rather than leaving a stale url. Everything else in the file
# (other servers, other sections) is left untouched. Note: manual edits to *this*
# block (e.g. a dev url) are intentionally reset on reinstall — use an env override
# for transient changes, not a hand-edit.
configure_codex_mcp_server() {
  local config_file="$1" server_name="$2" server_url="$3" ids_dir="$4" plugin_json="$5"
  local headers_line
  headers_line="$(build_codex_http_headers "$ids_dir" "$plugin_json")"

  # Strip any existing block (from its header to the next section or EOF), leaving
  # all other sections intact.
  if [ -f "$config_file" ] && grep -q "^\[mcp_servers\.${server_name}\]" "$config_file" 2>/dev/null; then
    # Temp file adjacent to the config so the mv is an atomic same-filesystem
    # rename (mktemp's default /tmp can be a different volume → mv falls back to
    # copy, which is non-atomic).
    local tmp
    tmp="$(mktemp "${config_file}.XXXXXX")" || return 0
    awk -v server="[mcp_servers.${server_name}]" '
      $0 == server { in_block = 1; next }
      /^\[/ && $0 != server { in_block = 0 }
      !in_block { print }
    ' "$config_file" > "$tmp" && mv "$tmp" "$config_file"
  fi

  printf '\n[mcp_servers.%s]\nurl = "%s"\nenabled = true\n%s\n' \
    "$server_name" "$server_url" "$headers_line" >> "$config_file"
}
