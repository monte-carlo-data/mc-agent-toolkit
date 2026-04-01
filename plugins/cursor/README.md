# Cursor Plugins

Monte Carlo plugins for the Cursor editor.

## Available Plugins

| Plugin | Description |
|---|---|
| `mc-prevent` | Detect and prevent breaking schema changes using Monte Carlo lineage and monitoring data. |

## Installation

Install via GitHub:

```
/add-plugin monte-carlo-data/mcd-agent-toolkit
```

Then authenticate with Monte Carlo by configuring the MCP server in Cursor settings.

## Architecture

Each Cursor plugin is a thin adapter wrapping shared skills and hook logic:

- **Skills** — symlinked from `skills/` at the repo root (shared with Claude Code)
- **Hook lib** — symlinked from `hooks/prevent/lib/` (shared decision logic)
- **Adapter hooks** — Cursor-specific JSON parsing and output formatting
- **MCP config** — Monte Carlo MCP server connection
