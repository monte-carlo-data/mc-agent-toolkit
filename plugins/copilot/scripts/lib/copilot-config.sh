#!/usr/bin/env bash
# Register the Monte Carlo MCP server in Copilot CLI's user config, with toolkit
# telemetry headers baked in. Copilot's MCP config supports only static headers
# (no runtime helper / no plugin hook that mutates MCP headers), and the
# supported non-interactive way to write the user-level ~/.copilot/mcp-config.json
# is `copilot mcp add`. install_id comes from the shared ensure_install_id so it
# matches the SessionStart beacon's id and the telemetry streams join.
#
# Copilot-specific; lives outside hooks/, so NOT part of the shared-lib sync.
# SOURCE this file; requires toolkit-ids.sh sourced first.

# configure_copilot_mcp_server <server_name> <server_url> <ids_dir> <plugin_json> [copilot_bin]
# Idempotently (remove + re-add) register the remote server with
# x-mcd-toolkit-install-id + x-mcd-toolkit-version headers. The install-id header
# is omitted when telemetry is opted out. Remove-then-add means a url/header
# change migrates on reinstall (the installer owns this user-config entry).
# No-op (fail-open) if the copilot CLI isn't available.
configure_copilot_mcp_server() {
  local server_name="$1" server_url="$2" ids_dir="$3" plugin_json="$4" copilot_bin="${5:-copilot}"
  command -v "$copilot_bin" >/dev/null 2>&1 || return 0

  local version
  version="$(read_plugin_version "$plugin_json")"

  local -a header_args=()
  if [ "${MC_AGENT_TOOLKIT_TELEMETRY_DISABLED:-}" != "1" ]; then
    local install_id
    install_id="$(ensure_install_id "$ids_dir")"
    [ -n "$install_id" ] && header_args+=(--header "x-mcd-toolkit-install-id: $install_id")
  fi
  [ -n "$version" ] && header_args+=(--header "x-mcd-toolkit-version: $version")

  # Remove any existing entry first so url + headers refresh on reinstall.
  "$copilot_bin" mcp remove "$server_name" >/dev/null 2>&1 || true
  if [ "${#header_args[@]}" -gt 0 ]; then
    "$copilot_bin" mcp add --transport http "$server_name" "$server_url" "${header_args[@]}" >/dev/null 2>&1 || true
  else
    "$copilot_bin" mcp add --transport http "$server_name" "$server_url" >/dev/null 2>&1 || true
  fi
}
