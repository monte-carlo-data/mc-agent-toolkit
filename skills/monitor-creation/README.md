# Monte Carlo Monitor Creation Skill

Guide AI agents through creating Monte Carlo monitors correctly — validating tables exist, checking field names and types, choosing the right monitor type, and generating monitors-as-code YAML. Eliminates common errors like invalid field types, nonexistent table references, and missing required parameters.

## Editor & Stack Compatibility

The skill works with any AI editor that supports MCP and the Agent Skills format — including Claude Code, Cursor, and VS Code.

All warehouses supported by Monte Carlo work with monitor creation. The skill validates table and column references against your actual warehouse schema via the Monte Carlo API.

## Prerequisites

- Claude Code, Cursor, VS Code or any editor with MCP support
- Monte Carlo account with Editor role or above
- [MC CLI](https://docs.getmontecarlo.com/docs/using-the-cli) installed for monitor deployment (`pip install montecarlodata`)

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
   npx skills add monte-carlo-data/mc-agent-toolkit --skill monitor-creation
   ```

3. Authenticate: run `/mcp` in your editor, select `monte-carlo-mcp`, and complete the OAuth flow.

4. Verify: ask your editor "Test my Monte Carlo connection" — it should call `testConnection` and confirm.

<details>
<summary>Legacy: header-based auth (for MCP clients without HTTP transport)</summary>

If your MCP client doesn't support HTTP transport, use `.mcp.json.example` with `npx mcp-remote` and header-based authentication. See the [MCP server docs](https://docs.getmontecarlo.com/docs/mcp-server) for details.

</details>

## How to use it

Tell your AI editor what you want to monitor — describe the table, the condition, or the data quality concern. The skill guides the agent through table resolution, schema validation, monitor type selection, parameter building, confirmation, and YAML generation. No special commands needed.

### Monitor types

| Type | When to use |
|---|---|
| **Metric** | Track a numeric aggregate over time — row counts, sums, averages, min/max on a column |
| **Validation** | Assert a condition that should always be true — null checks, range constraints, uniqueness |
| **Comparison** | Compare two tables or queries — staging vs. production, pre- vs. post-migration |
| **Custom SQL** | Write arbitrary SQL for complex business logic that doesn't fit the other types |
| **Table** | Monitor table-level health — freshness, volume, and schema changes |

### Deploying generated monitors

When Claude generates a monitor, it saves the YAML to `monitors/<table>.yml`. Deploy with:

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

## Example prompts

- "Create a null check monitor for the orders table"
- "Monitor freshness for all tables in the analytics schema"
- "Set up a comparison monitor between staging and production orders"
- "Add a custom SQL monitor to detect orphan records"
