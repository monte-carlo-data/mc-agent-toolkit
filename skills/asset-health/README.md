# Monte Carlo Asset Health Skill

Check the health of a data table using Monte Carlo — surfaces last activity, active alerts, monitoring coverage, importance, tags, and upstream dependency health in a single structured report.

## Editor & Stack Compatibility

The skill works with any AI editor that supports MCP and the Agent Skills format — including Claude Code, Cursor, and VS Code.

All warehouses supported by Monte Carlo work with this skill.

## Prerequisites

- Claude Code, Cursor, VS Code or any editor with MCP support
- Monte Carlo account with Viewer role or above

## Setup

### Via the mc-agent-toolkit plugin (recommended)

Install the plugin for your editor — it bundles the skill, MCP server, and permissions automatically. See the [main README](../../README.md#installing-the-plugin-recommended) for editor-specific instructions.

### Standalone

1. Configure the Monte Carlo MCP server:
   ```
   claude mcp add --transport http monte-carlo-mcp https://integrations.getmontecarlo.com/mcp
   ```

2. Install the skill:
   ```bash
   npx skills add monte-carlo-data/mc-agent-toolkit --skill asset-health
   ```

   Or copy directly:
   ```bash
   cp -r skills/asset-health ~/.claude/skills/asset-health
   ```

## Usage

Ask about the health or status of any table:

- "How is table orders_status doing?"
- "Check health of dim_customers"
- "What's the status of raw_events?"
- "Check on volume_change table"

The skill will produce a structured health report with metrics, active alerts, monitor status, and upstream dependency health.
