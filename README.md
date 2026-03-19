# Monte Carlo Claude Plugin

Installs [Monte Carlo's Claude Code skills](https://github.com/monte-carlo-data/mcd-skills) into your editor.

## Installation

### Option A — Install script

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/monte-carlo-data/monte-carlo-claude-plugin/main/install.sh)
```

### Option B — via [skills.sh](https://skills.sh) CLI

```bash
npx skilladd monte-carlo-data/mcd-skills
```

### Option C — via Claude Code plugin marketplace

Skills installed this way are namespaced (invoked as `/monte-carlo:<skill-name>`).

```
/plugin marketplace add monte-carlo-data/monte-carlo-claude-plugin
/plugin install monte-carlo@monte-carlo-claude-plugin
```

> **Note:** The `safe-change` skill requires the [Monte Carlo MCP Server](https://docs.getmontecarlo.com/docs/mcp-server) to be configured. See [setup instructions](https://github.com/monte-carlo-data/mcd-skills/blob/main/safe-change/README.md#setup).

## Skills installed

- **[safe-change](https://github.com/monte-carlo-data/mcd-skills/tree/main/safe-change)** — Surfaces table health, alerts, lineage, and blast radius before SQL edits; generates monitors-as-code. Requires Monte Carlo MCP Server.
- **[generate-validation-notebook](https://github.com/monte-carlo-data/mcd-skills/tree/main/generate-validation-notebook)** — Generates SQL validation notebooks for dbt PR changes.
