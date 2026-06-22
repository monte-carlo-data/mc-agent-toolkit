#!/usr/bin/env bash
# Sourceable helper for baking toolkit telemetry headers into Cursor's installed
# mcp.json. Cursor's install.sh copies the committed mcp.json into
# ~/.cursor/plugins/local/mc-agent-toolkit/mcp.json; this rewrites that COPY to
# add a static `headers` object (the committed file stays clean). install_id is
# generated via the shared ensure_install_id so it matches the toolkit's id files
# and the install beacon → the anonymous and authed streams join.
#
# Cursor-specific (JSON via jq) and lives outside hooks/, so NOT part of the
# shared-lib sync. SOURCE this file; requires toolkit-ids.sh sourced first
# (for ensure_install_id / read_plugin_version).

# configure_cursor_mcp_headers <mcp_json> <server_name> <ids_dir> <plugin_json>
# Idempotently set .mcpServers[<server>].headers. Always carries
# x-mcd-toolkit-version (when resolvable); carries x-mcd-toolkit-install-id unless
# telemetry is opted out at install time. Omits the headers object entirely when
# nothing would be set. Fail-open: no-op if jq is missing or the file won't parse.
configure_cursor_mcp_headers() {
  local mcp_json="$1" server="$2" ids_dir="$3" plugin_json="$4"
  command -v jq >/dev/null 2>&1 || return 0
  [ -f "$mcp_json" ] || return 0

  local version install_id=""
  version="$(read_plugin_version "$plugin_json")"
  if [ "${MC_AGENT_TOOLKIT_TELEMETRY_DISABLED:-}" != "1" ]; then
    install_id="$(ensure_install_id "$ids_dir")"
  fi

  local tmp
  tmp="$(mktemp)" || return 0
  if jq \
      --arg server "$server" \
      --arg version "$version" \
      --arg install_id "$install_id" \
      '
      .mcpServers[$server].headers =
        ( {}
          + (if $version != "" then {"x-mcd-toolkit-version": $version} else {} end)
          + (if $install_id != "" then {"x-mcd-toolkit-install-id": $install_id} else {} end)
        )
      | if (.mcpServers[$server].headers | length) == 0
        then .mcpServers[$server] |= del(.headers)
        else . end
      ' "$mcp_json" > "$tmp" 2>/dev/null; then
    mv "$tmp" "$mcp_json"
  else
    rm -f "$tmp"
  fi
}
