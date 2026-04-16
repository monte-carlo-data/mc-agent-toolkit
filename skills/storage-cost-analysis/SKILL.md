---
name: monte-carlo-storage-cost-analysis
description: |
  Identifies storage waste patterns (unread tables, zombies, dead-ends) and
  recommends safe cleanup actions with cost savings estimates. Uses lineage
  to verify downstream dependencies before recommending removal. Activates
  when a user asks about storage costs, unused tables, or warehouse cleanup.
version: 1.0.0
---

# Monte Carlo Storage Cost Analysis Skill

This skill helps identify tables that are wasting storage and recommends safe cleanup actions. It uses Monte Carlo's observability data -- lineage, query activity, monitoring status, and importance scores -- to classify waste patterns and compute safety tiers before recommending any action.

Reference files live next to this skill file. **Use the Read tool** (not MCP resources) to access them:

- Waste pattern definitions and classification: `references/waste-patterns.md` (relative to this file)
- Safety tier computation: `references/safety-tiers.md` (relative to this file)

## When to activate this skill

Activate when the user:

- Asks about storage costs, waste, or cleanup opportunities
- Wants to find unused, unread, or stale tables
- Asks "which tables can I drop?" or "what's costing us money?"
- Mentions storage optimization, cost reduction, or warehouse cleanup
- Wants to identify zombie tables or dead-end pipelines

## When NOT to activate this skill

Do not activate when the user is:

- Just querying data or exploring table contents
- Creating or modifying monitors (use the monitoring-advisor skill)
- Investigating data quality incidents (use the prevent skill)
- Looking at pipeline performance (use the performance-diagnosis skill)

## Prerequisites

The following MCP tools must be available (connect to Monte Carlo's MCP server):

- `search` -- find tables by name, filter by monitoring status and importance
- `get_table` -- get table metadata (size, type, timestamps)
- `get_asset_lineage` -- check upstream/downstream dependencies
- `get_queries_for_table` -- check read/write query activity
- `get_warehouses` -- list available warehouses

## Workflow

### Step 1: Identify the scope

Ask the user which warehouse to analyze, or use the one they mentioned. Call `get_warehouses` to list available warehouses if needed.

If the user specifies a schema or tag filter, use `search` with the appropriate filters to scope the analysis.

### Step 2: Find candidate tables

Use `search` to find tables that may be waste candidates. Run multiple searches to cover different patterns:

1. **Unmonitored tables**: `search(query="*", is_monitored=false, resource_ids=[warehouse_id])` -- tables nobody cared enough to monitor
2. **All tables** (if the user wants a full analysis): paginate through `search` results for the target warehouse

For each candidate, note: table name, importance score, monitoring status, MCON.

### Step 3: Investigate each candidate

For each candidate table (or top N by size), gather evidence:

1. **Query activity**: Call `get_queries_for_table(mcon=table_mcon, query_type="source")` to check reads, and `query_type="destination"` to check writes. Focus on:
   - Total read count (zero reads = potential waste)
   - Last read timestamp (stale if >90 days ago)
   - Write frequency (write-only tables are waste candidates)

2. **Downstream dependencies**: Call `get_asset_lineage(mcons=[table_mcon], direction="DOWNSTREAM")` to check if anything consumes this table.
   - `has_relationships: false` = no downstream consumers (safer to remove)
   - Has downstream consumers = **do NOT recommend removal** without user review

3. **Table metadata**: Call `get_table(mcon=table_mcon)` for size, type, and last update time.

### Step 4: Classify waste patterns

Read the `references/waste-patterns.md` file and classify each table into one of the waste categories based on the evidence gathered. Apply the safety tier computation from `references/safety-tiers.md`.

### Step 5: Present recommendations

Group findings by waste pattern and present to the user:

1. **Safe to remove** (safety tier 0-1): Tables with no downstream dependencies, no reads, low importance. Recommend `DROP TABLE` or archival.
2. **Needs review** (safety tier 2-3): Tables with some risk factors. Present the evidence and let the user decide.
3. **Needs lineage investigation** (has downstream deps): Tables that have consumers -- **never recommend removal** without the user verifying downstream impact.

For each recommendation, include:
- Table name (human-readable, never MCONs)
- Waste pattern (e.g., "Unread -- zero queries in 90 days")
- Size and estimated monthly cost (Snowflake: ~$23/TB/month)
- Safety tier with explanation
- Specific action: DROP, ARCHIVE, INVESTIGATE, or KEEP

### Important rules

- **Never recommend removing a table with downstream consumers** without explicit lineage verification. Safety first.
- **Always explain WHY** a table is waste -- don't just say "drop it."
- **Cost estimates are approximate.** Snowflake: ~$23/TB/month. For non-Snowflake warehouses, show size only (no cost estimate) and note that pricing varies.
- **Importance scores are computed metrics**, not business criticality. A low importance score doesn't mean the table is safe to remove -- always check lineage and query activity.
- **Present results as a table** for easy scanning: table name, waste pattern, size, safety tier, recommendation.
- **Never expose MCONs, UUIDs, or internal identifiers** to the user.
