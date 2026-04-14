# Performance Diagnosis Skill

Diagnoses data pipeline performance issues using Monte Carlo's cross-platform observability.

## What it does

- Finds slow jobs and expensive queries across Airflow, dbt, and Databricks
- Uses a tiered investigation approach: discover problems, bridge to tables, drill into root causes
- Detects regressions via change timeline correlation (query changes + volume shifts + failures)
- Identifies failed/futile query patterns with pre-computed root cause analysis
- Tracks latency trends to spot gradual degradation

## MCP Tools Required

Connect to Monte Carlo's MCP server (`integrations.getmontecarlo.com/mcp`). The skill uses these tools:

| Tool | Tier | Purpose |
|------|------|---------|
| `get_jobs_performance` | Discovery | Find slow/failing jobs |
| `get_top_slow_queries` | Discovery | Find most expensive queries |
| `get_tables_for_job` | Bridge | Convert job MCONs to table MCONs |
| `get_tasks_performance` | Diagnosis | Find bottleneck tasks within a job |
| `get_change_timeline` | Diagnosis | Unified "what changed?" timeline |
| `get_query_rca` | Diagnosis | Root cause analysis for query failures |
| `get_query_latency_distribution` | Diagnosis | Latency trend over time |
| `get_asset_lineage` | Diagnosis | Trace upstream/downstream impact |
| `get_warehouses` | Supporting | List available warehouses |

## Example prompts

- "Why is our nightly pipeline so slow?"
- "Find the most expensive queries in our Snowflake warehouse"
- "What changed that made the orders model take twice as long?"
- "Are there any failing query patterns we should fix?"
- "Show me the latency trend for our ETL jobs"

## Investigation flow

```
Tier 1: Discovery          Tier 2: Diagnosis
(no MCONs needed)          (MCONs from Tier 1 or user)

get_jobs_performance ──┐
                       ├──► get_tables_for_job ──► get_tasks_performance
get_top_slow_queries ──┘                           get_change_timeline
                                                   get_query_rca
                                                   get_query_latency_distribution
                                                   get_asset_lineage
```

Typical investigation: 3-7 tool calls. Stop as soon as you have a root cause with evidence.

See `references/investigation-tiers.md` for detailed tool usage.
