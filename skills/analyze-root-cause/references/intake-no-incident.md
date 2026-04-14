# Intake Flow: No Incident ID

Use this when the user describes a data problem but doesn't have a specific Monte Carlo alert or incident ID.

## Goal

Narrow down: **which table**, **what type of issue**, **when it started**, and whether Monte Carlo already detected it.

## Steps

### 1. Ask clarifying questions

Get the essentials from the user:
- **What table or data asset** is affected? (table name, dashboard, report)
- **What looks wrong?** (stale data, wrong numbers, missing rows, new columns, etc.)
- **When did you notice it?** (approximate timestamp helps scope the search)
- **Which warehouse?** (if they have multiple)

### 2. Find the table

Call `search(query="table_name")` to find the table's MCON and metadata.

If the user mentions a dashboard or report, search for it and then trace lineage upstream to find the source table:
- `search(query="dashboard_name")`
- `get_asset_lineage(mcons=[dashboard_mcon], direction="UPSTREAM")`

### 3. Search for existing alerts

Call `get_alerts` with a recent time range (last 7-14 days):
- Filter by the affected table if possible
- Look for alerts that match the user's description (freshness, volume, schema, field metric)
- If a matching alert exists, use its details to drive the investigation — proceed as if the user provided an incident ID

### 4. Check table health

Even without an alert, check the table directly:

- **Freshness:** `get_table_freshness` — when was it last updated? Is it overdue?
- **Volume:** `get_table_size_history` — has the row count changed unexpectedly?
- **Schema:** `get_table(mcon=..., include_fields=true)` — check current schema
- **Query activity:** `get_queries_for_table` — are write queries still running?

### 5. Classify the issue type

Based on the evidence gathered, determine the issue type:

| Symptom | Issue Type | Next Step |
|---------|-----------|-----------|
| Table hasn't updated recently | Freshness | `references/freshness-investigation.md` |
| Row count spiked or dropped | Volume | `references/volume-investigation.md` |
| Columns added/removed/changed | Schema | `references/schema-investigation.md` |
| Data values look wrong (nulls, weird averages) | Field anomaly | `references/field-anomaly-investigation.md` |
| Pipeline failed or errored | ETL failure | `references/etl-failure-investigation.md` |
| Query was modified | Query change | `references/query-change-investigation.md` |

### 6. Proceed to investigation

Once you've identified the table, issue type, and approximate timeline, continue with Step 2 (Map the blast radius) from the main SKILL.md workflow.

## Tips

- **Users often know the symptom but not the cause.** "The dashboard shows yesterday's numbers" = freshness issue. "Revenue is way too high" = volume or field anomaly.
- **Check downstream first if the user reports a dashboard issue.** The bad data might originate several tables upstream.
- **Multiple alerts on the same table at the same time** usually have a single root cause.
