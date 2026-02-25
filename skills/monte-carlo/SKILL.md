---
name: monte-carlo
description: |
  Use this skill when working with dbt models, SQL files, or data pipelines where you need
  table health, lineage, active alerts, or data quality monitors from Monte Carlo Data.
  Activate when the user opens or edits a dbt model, asks about a table's status, wants to
  add monitoring for new logic, or needs to triage a data quality incident.
version: 1.0.0
---

# Monte Carlo Data — AI Editor Skill

This skill brings Monte Carlo's data observability context directly into your editor. When you're modifying a dbt model or SQL pipeline, use it to surface table health, lineage, active alerts, and to generate monitors-as-code without leaving Claude Code.

## When to activate this skill

Activate proactively when the user:
- Opens or edits a `.sql` file, `.py` file, or dbt model (files in `models/`)
- Mentions a table name, dataset, or dbt model by name
- Asks about data quality, freshness, row counts, or anomalies
- Adds new transformation logic and might need a validation monitor
- Wants to triage or respond to a data quality alert

## Available MCP tools

All tools are available via the `monte-carlo` MCP server.

| Tool | Purpose |
|---|---|
| `testConnection` | Verify auth and connectivity |
| `search` | Find tables/assets by name |
| `getTable` | Schema, stats, freshness, row counts, monitoring status |
| `getAssetLineage` | Upstream sources and downstream dependents |
| `getAlerts` | Active incidents and alerts (use snake_case params — see below) |
| `getMonitors` | List monitors on a table |
| `getQueriesForTable` | Recent query history |
| `getQueryData` | Full SQL for a specific query |
| `createValidationMonitorMac` | Generate monitors-as-code YAML for a validation rule |
| `getValidationPredicates` | List available validation rule types |
| `updateAlert` | Update alert status or severity |
| `setAlertOwner` | Assign alert ownership |
| `createOrUpdateAlertComment` | Add comments to alerts |
| `getDomains` | List MC domains |
| `getUser` | Current user info |
| `getCurrentTime` | ISO timestamp (useful for alert time windows) |

## Core workflows

### 1. Table health check — when opening or editing a model

When the user opens a dbt model or mentions a table, run this sequence automatically:

```
1. search(query="<table_name>") → get the full MCON/table identifier
2. getTable(mcon="<mcon>") → schema, freshness, row count, monitoring status
3. getAssetLineage(mcon="<mcon>") → upstream sources, downstream dependents
4. getAlerts(created_after="<7 days ago>", created_before="<now>", table_mcons=["<mcon>"]) → active alerts
```

Summarize for the user:
- **Health**: last updated, row count, is it monitored?
- **Lineage**: N upstream sources, M downstream consumers (name the important ones)
- **Alerts**: any active/unacknowledged incidents — lead with these if present

Example summary to offer unprompted when a dbt model file is opened:
> "The table `orders_status` was last updated 2 hours ago with 142K rows. It has 3 downstream dependents including `order_status_snapshot`. There are 2 active freshness alerts — want me to pull the details?"

### 2. Add a monitor — when new transformation logic is added

When the user adds a new column, filter, or business rule, suggest adding a validation monitor:

```
1. getValidationPredicates() → show what validation types are available
2. createValidationMonitorMac(
     mcon="<table_mcon>",
     description="<what the rule checks>",
     condition_sql="<the validation SQL>"
   ) → returns YAML
3. Save the YAML to <project>/monitors/<table_name>.yml
4. Run: montecarlo monitors apply --dry-run (to preview)
5. Run: montecarlo monitors apply --auto-yes (to apply)
```

**Important — YAML format for `monitors apply`:**
The `createValidationMonitorMac` tool generates `validation:` format YAML. The `montecarlo monitors apply` CLI expects a different format with `montecarlo:` as the root key. Reformat the generated YAML as:

```yaml
montecarlo:
  custom_sql:
    - warehouse: <warehouse_name>
      name: <monitor_name>
      description: <description>
      schedule:
        interval_minutes: 720
        start_time: '<ISO timestamp>'
      sql: <your validation SQL>
      alert_conditions:
        - operator: GT
          threshold_value: 0.0
```

The `montecarlo.yml` project config (separate from monitor files) should be:
```yaml
version: 1
namespace: <your-namespace>
default_resource: <warehouse_name>
```

### 3. Alert triage — when investigating an active incident

```
1. getAlerts(
     created_after="<start>",
     created_before="<end>",
     order_by="-createdTime",
     statuses=["NOT_ACKNOWLEDGED"]
   ) → list open alerts
2. getTable(mcon="<affected_table_mcon>") → check current table state
3. getAssetLineage(mcon="<mcon>") → identify upstream cause or downstream blast radius
4. getQueriesForTable(mcon="<mcon>") → recent queries that might explain the anomaly
```

To respond to an alert:
- `updateAlert(alert_id="<id>", status="ACKNOWLEDGED")` — acknowledge it
- `setAlertOwner(alert_id="<id>", owner="<email>")` — assign ownership
- `createOrUpdateAlertComment(alert_id="<id>", comment="<text>")` — add context

## Important parameter notes

### `getAlerts` — use snake_case parameters
The MCP tool uses Python snake_case, **not** the camelCase params from the MC web UI:

```
✓ created_after    (not createdTime.after)
✓ created_before   (not createdTime.before)
✓ order_by         (not orderBy)
✓ table_mcons      (not tableMcons)
```

Always provide `created_after` and `created_before`. Max window is 60 days.
Use `getCurrentTime()` to get the current ISO timestamp when needed.

### `search` — finding the right table identifier
MC uses MCONs (Monte Carlo Object Names) as table identifiers. Always use `search` first to resolve a table name to its MCON before calling `getTable`, `getAssetLineage`, or `getAlerts`.

```
search(query="orders_status") → returns mcon, full_table_id, warehouse
```

## Demo scenario

A data engineer opens `models/orders/orders_status.sql` and is adding a new `order_value` column:

1. **Unprompted**: Surface table health for `orders_status`
   - Last updated, row count, existing monitors
   - Active alerts (freshness breach on `analytics:prod_detectors` is firing)
   - Downstream: `order_status_2024` → `order_status_snapshot`

2. **As they add the column**: Suggest a validation monitor
   - "Would you like me to add a monitor to ensure `order_value` is never null or negative?"
   - Generate YAML → save to `monitors/orders_status.yml` → dry-run → apply

3. **End result**: New logic is live, monitor is deployed, all from within Claude Code

## Troubleshooting

**MCP connection fails:**
```bash
# Verify the server is reachable
curl -s -o /dev/null -w "%{http_code}" https://integrations.getmontecarlo.com/mcp/
```
Check that `x-mcd-id` and `x-mcd-token` are set correctly in your MCP config. The key format is `<KEY_ID>:<KEY_SECRET>` — these are split across two separate headers.

**`montecarlo monitors apply` fails with "Not a Monte Carlo project":**
Ensure `montecarlo.yml` (the project config) exists in your working directory.

**`montecarlo monitors apply` fails with "Unknown field":**
The monitor definition files must have `montecarlo:` as the root key. The `validation:` format from `createValidationMonitorMac` is not directly compatible — use the `custom_sql:` format shown above.
