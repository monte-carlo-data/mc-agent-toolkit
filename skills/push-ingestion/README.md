# Push Ingestion Skill

Generate warehouse-specific collection scripts and push metadata, lineage, and query logs to Monte Carlo via the push ingestion API. Works with any data source — if a ready-made template doesn't exist, the skill derives collection queries from the warehouse's system catalog.

## What it does

When you discuss push ingestion in conversation, this skill automatically guides you through:

- Setting up the required API keys
- Generating collection scripts tailored to your warehouse
- Pushing metadata, lineage, and query logs to Monte Carlo
- Validating that pushed data is visible in the platform
- Managing custom lineage nodes and edges
- Deleting push-ingested tables when needed

## Prerequisites

- Claude Code or any MCP-capable editor
- Monte Carlo account with API access
- Two separate API keys:
  1. **Ingestion key** — for pushing data (`montecarlo integrations create-key --scope Ingestion`)
  2. **GraphQL API key** — for verification queries (create at https://getmontecarlo.com/settings/api)
- Access to your data warehouse

See [prerequisites.md](references/prerequisites.md) for full setup instructions.

## Setup

### Via the mc-agent-toolkit plugin (recommended)

Install the plugin for your editor — see the [main README](../../README.md) for instructions. The skill is bundled automatically.

### Standalone

Copy the skill to your local skills directory:

```bash
cp -r skills/push-ingestion ~/.claude/skills/push-ingestion
```

## Available slash commands

When installed via the Claude Code plugin, these slash commands are available:

| Command | Description |
|---|---|
| `/mc-build-metadata-collector` | Generate a metadata collection script for your warehouse |
| `/mc-build-lineage-collector` | Generate a lineage collection script |
| `/mc-build-query-log-collector` | Generate a query log collection script |
| `/mc-validate-metadata` | Verify pushed metadata via the Monte Carlo GraphQL API |
| `/mc-validate-lineage` | Verify pushed lineage via the Monte Carlo GraphQL API |
| `/mc-validate-query-logs` | Verify pushed query logs via the Monte Carlo GraphQL API |
| `/mc-create-lineage-node` | Create a custom lineage node |
| `/mc-create-lineage-edge` | Create a custom lineage edge |
| `/mc-delete-lineage-node` | Delete a custom lineage node |
| `/mc-delete-push-tables` | Delete push-ingested tables |

## Supported warehouses

The skill includes templates for common warehouses under `scripts/templates/`. For warehouses without templates, the Snowflake template is used as the canonical reference and adapted to the target warehouse's system catalog.

See the [SKILL.md](SKILL.md) for detailed workflow instructions and template usage.
