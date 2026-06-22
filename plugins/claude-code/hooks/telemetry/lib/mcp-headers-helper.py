#!/usr/bin/env python3
"""Emit toolkit telemetry headers for the Monte Carlo MCP server (``headersHelper``).

Claude Code / Cortex Code invoke this script as the ``headersHelper`` for the
``monte-carlo-mcp`` HTTP server (see each plugin's ``.mcp.json``). On every MCP
connection it prints a JSON object of HTTP headers to stdout, which the editor
attaches to authenticated MCP requests:

    x-mcd-toolkit-install-id   stable per-machine install UUID
    x-mcd-toolkit-session-id   per-session UUID (rotated each session)
    x-mcd-toolkit-version      toolkit version

These let the anonymous beacon stream (keyed by ``install_id``) be joined to the
authenticated ``MCP Tool Called`` stream server-side. The values are read from
sibling files in this script's own directory: the ``SessionStart`` hook
(``ensure-toolkit-ids.sh``) copies this script into the editor's id dir
(e.g. ``~/.claude/mc-agent-toolkit/``) alongside ``install_id``,
``toolkit_session_id``, and ``toolkit_version``.

This script lives outside the plugin bundle at runtime because
``${CLAUDE_PLUGIN_ROOT}`` is not interpolated inside ``headersHelper``
(claude-code#47789); referencing a fixed ``$HOME`` path is the workaround.

Design rules:
  * Opt-out: if ``MC_AGENT_TOOLKIT_TELEMETRY_DISABLED=1``, emit no headers.
  * Fail-open: print ``{}`` on ANY error and exit 0. A broken helper must never
    block an MCP connection. The ``.mcp.json`` invocation also appends
    ``|| echo '{}'`` as a second safety net for when this file isn't present yet
    (first connection before ``SessionStart`` has copied it).
  * Only emit a header whose source file exists and is non-empty.
"""

import json
import os
import sys

# HTTP header name -> id file name (a sibling of this script in the id dir).
_HEADER_FILES = {
    "x-mcd-toolkit-install-id": "install_id",
    "x-mcd-toolkit-session-id": "toolkit_session_id",
    "x-mcd-toolkit-version": "toolkit_version",
}


def _build_headers() -> dict[str, str]:
    if os.environ.get("MC_AGENT_TOOLKIT_TELEMETRY_DISABLED") == "1":
        return {}

    ids_dir = os.path.dirname(os.path.abspath(__file__))
    headers: dict[str, str] = {}
    for header, filename in _HEADER_FILES.items():
        try:
            with open(os.path.join(ids_dir, filename), encoding="utf-8") as fh:
                value = fh.read().strip()
        except OSError:
            continue
        if value:
            headers[header] = value
    return headers


def main() -> None:
    try:
        headers = _build_headers()
    except Exception:
        headers = {}
    sys.stdout.write(json.dumps(headers))


if __name__ == "__main__":
    main()
