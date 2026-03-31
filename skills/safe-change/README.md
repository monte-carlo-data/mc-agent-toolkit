# Monte Carlo Safe Change Skill

Bring Monte Carlo data observability into your editor — automatically, before you write a single line of code.

## What this does

When you reference a dbt model or table, Monte Carlo context comes to you: table health, active alerts, lineage, and downstream blast radius. Your AI editor uses that context to shape the code it writes — not just surface it. If you try to rename a column with 500 downstream dependents, the editor recommends a safe transition strategy and explains why, citing the specific MC data it found. When you add new logic, it generates and deploys the right monitor for your logic — validation, metric, comparison, or custom SQL — before you merge. When you're done with a change, it generates targeted validation queries — tailored to the specific columns, filters, and business logic you modified — so you can verify the change behaved as intended before merging.

## Editor & Stack Compatibility

The skill works with any AI editor that supports MCP and the Agent Skills format — including Claude Code, Cursor, and VS Code.

For data stacks, compatibility varies by how you work:

| Stack | Support | Notes |
|---|---|---|
| dbt + any MC-supported warehouse | ✅ Full | Optimized and tested |
| SQL-first, no dbt | 🟡 Partial | Core workflows work via explicit prompting; auto-triggers on file open coming soon |
| Databricks notebooks | 🟡 Partial | Health check, impact assessment, and alert triage work; file-based triggers coming soon |
| SQLMesh | 🟡 Partial | Core workflows work; native SQLMesh project structure support coming soon |
| PySpark / non-SQL pipelines | 🟠 Limited | Manual prompting only; broader support on the roadmap |

**Coming shortly:** Generic SQL file triggers, Databricks notebook support, and SQLMesh project structure support — so auto-activation works regardless of your transformation tool.

Core workflows — table health check, change impact assessment, alert triage, and monitor generation — work for any warehouse supported by Monte Carlo.


## Prerequisites

- Claude Code, Cursor, VS Code or any editors with MCP support
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

See [installation options](https://github.com/monte-carlo-data/mcd-skills#installation) in the main repository README. The plugin bundles hooks, commands, and tool permissions on top of the skill. If you configured the MCP server in Step 1, the plugin will use that alongside its own bundled server.

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

Open your dbt project (or any data engineering codebase) in your editor. From there, you can either reference a few models or tables you plan to work on — or just prompt the editor with the change you want to make. The skill activates automatically based on what you're doing; no special commands needed.

**Workflow 1 — Table health check:** Opens when you reference a `.sql` file, dbt model, or table name. Surfaces freshness, row count, importance, lineage, and active alerts. Auto-escalates to a full impact assessment if the table has active alerts, key asset dependents, or high importance.

**Workflow 2 — Monitor generation:** After you add new transformation logic (a column, filter, or business rule), suggests and deploys a validation, metric, comparison, or custom SQL monitor as code.

**Workflow 3 — Alert triage:** When you ask about data quality issues. Lists open alerts, checks table state, traces lineage to find the root cause or blast radius.

**Workflow 4 — Change impact assessment:** Fires automatically before any SQL edit — including filter changes, bugfixes, reverts, and parameter tweaks, not just schema changes. Surfaces downstream blast radius, active incidents, column exposure in recent queries, and monitor coverage. Reports a risk tier (High / Medium / Low) and translates the findings into a specific code recommendation. If the MC data suggests your planned approach is risky, Claude will recommend a safer alternative and explain why — citing the specific tables, alert counts, and read volumes it found.

**Workflow 5 — Change validation queries:** After you've made a change and are ready to test it, say something like "generate validation queries" or "validate this change". Claude generates 3–5 targeted SQL queries based on the Workflow 4 findings and the diff — null checks, before/after row counts, distribution checks — using the exact column names, filter logic, and business rules from your change. Queries are saved to `validation/<table_name>_<timestamp>.sql` with inline comments explaining what a passing result looks like for each check. Does not activate automatically; only runs when you ask.

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

## Troubleshooting

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common setup and runtime issues.
