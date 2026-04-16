# Monte Carlo Monitoring Advisor Skill

Analyze data coverage, create monitors for warehouse tables and AI agents. Walks users through warehouse discovery, use-case exploration, coverage gap analysis, data monitor creation, and agent observability — all through natural conversation. This single skill handles all monitoring needs: coverage analysis, data quality monitors (metric, validation, custom SQL, comparison, table), and AI agent monitors (metric, evaluation, trajectory, validation).

## Editor & Stack Compatibility

The skill works with any AI editor that supports MCP and the Agent Skills format — including Claude Code, Cursor, and VS Code.

All warehouses supported by Monte Carlo work with the monitoring advisor. The skill validates table and column references against your actual warehouse schema via the Monte Carlo API.

## Prerequisites

- Claude Code, Cursor, VS Code or any editor with MCP support
- Monte Carlo account with Editor role or above
- [MC CLI](https://docs.getmontecarlo.com/docs/using-the-cli) installed for monitor deployment (`pip install montecarlodata`)
- All monitor creation capabilities are built in — no additional skills needed

## Setup

### Via the mc-agent-toolkit plugin (recommended)

Install the plugin for your editor — it bundles the skill, hooks, MCP server, and permissions automatically. See the [main README](../../README.md#installing-the-plugin-recommended) for editor-specific instructions.

### Standalone

1. Configure the Monte Carlo MCP server:
   ```
   claude mcp add --transport http monte-carlo-mcp https://mcp.getmontecarlo.com/mcp
   ```

2. Install the skill:
   ```bash
   npx skills add monte-carlo-data/mc-agent-toolkit --skill monitoring-advisor
   ```

3. Authenticate: run `/mcp` in your editor, select `monte-carlo-mcp`, and complete the OAuth flow.

4. Verify: ask your editor "Test my Monte Carlo connection" — it should call `test_connection` and confirm.

<details>
<summary>Legacy: header-based auth (for MCP clients without HTTP transport)</summary>

If your MCP client doesn't support HTTP transport, use `.mcp.json.example` with `npx mcp-remote` and header-based authentication. See the [MCP server docs](https://docs.getmontecarlo.com/docs/mcp-server) for details.

</details>

## How to use it

Ask your AI editor about your monitoring coverage — describe what you want to understand or protect. The skill guides the agent through warehouse discovery, use-case analysis, coverage gap identification, and monitor creation. No special commands needed.

### Example prompts

- "What are my coverage gaps?"
- "Show me my use cases and what's monitored"
- "Which tables should I monitor first?"
- "Analyze monitoring coverage for my warehouse"
- "Find unmonitored tables with recent anomalies"
- "Help me set up monitoring for my critical use cases"
- "Create a freshness monitor on the orders table"
- "Set up a null check on the email column"
- "Monitor my AI agent's latency and token usage"
- "Track my agent's response quality"

### What it does

1. **Discovers** your warehouses, use cases, and AI agents
2. **Analyzes** coverage — which tables are monitored, which aren't, and which have active anomalies
3. **Prioritizes** gaps by criticality, importance score, and anomaly activity
4. **Creates** data quality monitors (metric, validation, custom SQL, comparison, table) with full parameter validation
5. **Creates** AI agent monitors (metric, evaluation, trajectory, validation) for agent observability
6. **Generates** monitors-as-code YAML ready for deployment

### Deploying generated monitors

When the advisor generates a monitor, it returns MaC YAML. Deploy with:

```bash
montecarlo monitors apply --dry-run    # preview
montecarlo monitors apply --auto-yes   # apply
```

Your project needs a `montecarlo.yml` config in the working directory:

```yaml
version: 1
namespace: <your-namespace>
default_resource: <your-warehouse-name>
```
