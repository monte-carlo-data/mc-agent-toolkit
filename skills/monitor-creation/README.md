# Monte Carlo Monitor Creation Skill

This skill guides AI agents through creating Monte Carlo monitors correctly — validating tables exist, checking field names and types, choosing the right monitor type, and generating monitors-as-code YAML. It eliminates common errors like invalid field types, nonexistent table references, and missing required parameters.

## Editor & Stack Compatibility

The skill works with any AI editor that supports MCP and the Agent Skills format — including Claude Code, Cursor, and VS Code.

For data stacks, all warehouses supported by Monte Carlo work with monitor creation. The skill validates table and column references against your actual warehouse schema via the Monte Carlo API.

## Prerequisites

- Claude Code, Cursor, VS Code or any editor with MCP support
- Monte Carlo account with Editor role or above
- [MC CLI](https://docs.getmontecarlo.com/docs/using-the-cli) installed for monitor deployment (`pip install montecarlodata`)

## Setup

### Step 1 — Configure the Monte Carlo MCP server (recommended)

```
claude mcp add --transport http monte-carlo-mcp https://integrations.getmontecarlo.com/mcp
```

This registers the Monte Carlo MCP server with Claude Code. See the [official docs](https://docs.getmontecarlo.com/docs/mcp-server#option-1-oauth-21-recommended-for-mcp-clients-that-support-http-transport) for other MCP clients.

> **Note:** This step is optional if you install the plugin (Step 2), which bundles its own MCP server. However, configuring the standalone server first is recommended — it's available across all projects and won't be removed if you uninstall the plugin.

### Step 2 — Install the plugin

In Claude Code, run:

```
/plugin install mc-core@mcd-agent-toolkit
```

Or add via the marketplace first if needed. The plugin bundles hooks, commands, and tool permissions on top of the skill. If you configured the MCP server in Step 1, the plugin will use that alongside its own bundled server.

### Step 3 — Authenticate with Monte Carlo

In Claude Code, run:

```
/mcp
```

Select the Monte Carlo server (`monte-carlo-mcp` if standalone, or `monte-carlo` if plugin-bundled) and follow the browser-based OAuth flow to log in with your Monte Carlo account.

### Step 4 — Verify the connection

In Claude Code, paste:

> "Test my Monte Carlo connection"

Claude will call `testConnection` and confirm your credentials are working.

### Step 5 — Configure tool permissions (standalone only)

If you're using the standalone MCP server (Step 1) **without** the plugin, add this to `.claude/settings.local.json` in your project:

```json
{
  "permissions": {
    "allow": ["mcp__monte-carlo-mcp__*"]
  }
}
```

The plugin handles this automatically — no manual configuration needed.

<details>
<summary>Legacy: header-based auth (for MCP clients without HTTP transport)</summary>

If your MCP client doesn't support HTTP transport, configure the MCP server using `.mcp.json.example` with `npx mcp-remote` and header-based authentication. You'll need an MCP server key from Monte Carlo → Settings → API Keys. See the [MCP server docs](https://docs.getmontecarlo.com/docs/mcp-server) for details.

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

## Troubleshooting

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common setup and runtime issues.
