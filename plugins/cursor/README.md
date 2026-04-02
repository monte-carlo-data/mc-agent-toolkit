# Cursor Plugins

Monte Carlo plugins for the Cursor editor.

## Available Plugins

| Plugin | Description |
|---|---|
| `mc-prevent` | Detect and prevent breaking schema changes using Monte Carlo lineage and monitoring data. |

## Installation

### One-line install (macOS / Linux)

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/monte-carlo-data/mcd-agent-toolkit/main/plugins/cursor/prevent/scripts/install.sh)
```

### Manual install

1. Clone the repository:

   ```bash
   git clone https://github.com/monte-carlo-data/mcd-agent-toolkit.git
   cd mcd-agent-toolkit
   ```

2. Run the install script:

   ```bash
   bash plugins/cursor/prevent/scripts/install.sh
   ```

   This copies the plugin (with symlinks resolved) to `~/.cursor/plugins/local/mc-prevent`.

3. Restart Cursor or run **Developer: Reload Window** from the Command Palette (`Cmd+Shift+P`).

4. The Monte Carlo MCP server will prompt for OAuth authentication on first use.

## Architecture

Each Cursor plugin is a thin adapter wrapping shared skills and hook logic:

- **Skills** — symlinked from `skills/` at the repo root (shared with Claude Code)
- **Hook lib** — symlinked from `hooks/prevent/lib/` (shared decision logic)
- **Adapter hooks** — Cursor-specific JSON parsing and output formatting
- **MCP config** — Monte Carlo MCP server connection
