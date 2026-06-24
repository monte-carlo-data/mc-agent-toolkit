# Monte Carlo Agent Toolkit — Cursor Plugin

Monte Carlo's unified agent toolkit plugin for the Cursor editor. Delivers data observability skills and enforcement hooks as named features within a single plugin.

## Available Features

| Feature | Description |
|---|---|
| **MC Prevent** | Detect and prevent breaking schema changes using Monte Carlo lineage and monitoring data. |

**Requires Python 3.10+.**

## Installation

### One-line install (macOS / Linux)

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/monte-carlo-data/mc-agent-toolkit/main/plugins/cursor/scripts/install.sh)
```

### Manual install

1. Clone the repository:

   ```bash
   git clone https://github.com/monte-carlo-data/mc-agent-toolkit.git
   cd mc-agent-toolkit
   ```

2. Run the install script:

   ```bash
   bash plugins/cursor/scripts/install.sh
   ```

   This copies the plugin (with symlinks resolved) to `~/.cursor/plugins/local/mc-agent-toolkit`.

3. Restart Cursor or run **Developer: Reload Window** from the Command Palette (`Cmd+Shift+P`).

4. The Monte Carlo MCP server will prompt for OAuth authentication on first use.

## Known Issues

- **Hook denials may not be enforced.** Cursor's `beforeReadFile` (and potentially other `before*` hooks) may fail to block the operation even when the hook exits with a deny response. This means Prevent hooks can detect and warn about breaking changes but cannot guarantee the edit is stopped. See [Cursor forum discussion](https://forum.cursor.com/t/hook-beforereadfile-does-not-work-in-the-agent/150520) for details.

## Telemetry

The toolkit sends an anonymous install beacon — a `Toolkit Installed` event so we can count installations and version adoption. It includes an opaque per-install UUID, a per-session UUID, the toolkit version, and the editor it runs in (`cursor`). No prompts, arguments, skill names, or code are ever sent. It fires once per machine per toolkit version — the first time you start Cursor after installing, and again after each version change (deduped by a local marker) — and is fail-open and non-blocking, never delaying or interrupting your session.

**Authenticated MCP traffic (v1.13.3+).** The same anonymous `install_id` and the toolkit version also ride as HTTP headers (`x-mcd-toolkit-install-id`, `x-mcd-toolkit-version`) on **authenticated** requests to the Monte Carlo MCP server (baked into the installed `mcp.json` at install time). This lets the otherwise-anonymous install record be correlated with your account's MCP tool usage server-side — still no prompts, arguments, or code. The opt-out below disables these headers too.

To opt out, set `MC_AGENT_TOOLKIT_TELEMETRY_DISABLED=1` in your shell environment before starting Cursor. The toolkit will not phone home.

The data is stored in Mixpanel and Datadog and is used only for product-development decisions. The UUIDs are generated locally on first session and stored under `~/.cursor/mc-agent-toolkit/`. Deleting that directory resets your install identity to a fresh anonymous one.

## Architecture

The toolkit plugin wraps shared skills and hook logic, with each feature namespaced independently:

- **Skills** — symlinked from `skills/` at the repo root (shared across all editors)
- **Shared hook logic** — copied from `plugins/shared/prevent/lib/` into each plugin's `hooks/prevent/lib/` (platform-agnostic business logic)
- **Adapter hooks** — Cursor-specific JSON parsing and output formatting under `hooks/prevent/`
- **MCP config** — Monte Carlo MCP server connection
- **Telemetry hook** — the install-beacon `sessionStart` is registered in `hooks/prevent/hooks.json` (Cursor loads a single manifest-referenced hooks file per plugin), while the script itself lives under `hooks/telemetry/`

See the [plugins README](../README.md) for the overall plugin architecture and editor support comparison.
