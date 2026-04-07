# Monte Carlo Agent Toolkit — Claude Code Plugin

Monte Carlo's unified agent toolkit plugin for Claude Code. Delivers data observability skills, enforcement hooks, and slash commands as named features within a single plugin.

## Installation

1. Add the marketplace:
   ```
   /plugin marketplace add monte-carlo-data/mc-marketplace
   ```
2. Install the plugin:
   ```
   /plugin install mc-agent-toolkit@mc-marketplace
   ```
3. Updates — `claude plugin update` pulls in the latest changes.

## Available Features

| Feature | Description |
|---|---|
| **MC Prevent** | Analyzes schema changes using MC lineage, monitoring, alerts, queries, and table metadata. Generates Monte Carlo monitors and validation queries to prevent data incidents. |
| **MC Generate Validation Notebook** | Generates executable validation queries from a pull request and packages them into Monte Carlo notebooks for direct testing. |
| **MC Push Ingestion** | Generates warehouse-specific collection scripts and guides customers through pushing metadata, lineage, and query logs to Monte Carlo. |

## Architecture

The toolkit plugin wraps shared skills and hook logic, with each feature namespaced independently:

- **Skills** — symlinked from `skills/` at the repo root (shared across all editors)
- **Shared hook logic** — symlinked from `plugins/shared/prevent/lib/` (platform-agnostic business logic)
- **Adapter hooks** — Claude Code-specific JSON parsing and output formatting under `hooks/prevent/`
- **Commands** — slash commands namespaced under `commands/<skill>/`
- **MCP config** — Monte Carlo MCP server connection (shared by all features)
