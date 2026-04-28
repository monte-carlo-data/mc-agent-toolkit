---
name: monte-carlo-monitoring-advisor
description: Analyze data coverage, create monitors for warehouse tables and AI agents. Covers coverage gaps, use-case analysis, data monitor creation, and agent observability.
bucket: Monitoring
version: 2.0.0
---

# Monte Carlo Monitoring Advisor Skill

This skill handles all monitoring requests -- coverage analysis, data monitor creation, and AI agent monitoring. It routes to the right reference file based on the user's intent.

Reference files live next to this skill file. **Use the Read tool** (not MCP resources) to access them:

- Data monitor creation procedure: `references/data-monitor-creation.md` (relative to this file)
- Agent monitor creation procedure: `references/agent-monitor-creation.md` (relative to this file)
- Per-type references: `references/data-*.md` and `references/agent-*.md` (relative to this file)

## When to activate this skill

Activate when the user:

- Asks about monitoring coverage, data coverage, or coverage gaps
- Wants to understand what's monitored vs. not in their warehouse
- Asks about use cases, use-case criticality, or use-case analysis
- Wants to explore their data estate and find what needs monitoring
- Says things like "what should I monitor?", "where are my coverage gaps?", "show me my use cases"
- Asks about unmonitored tables with anomalies or importance-based prioritization
- Asks to create, add, or set up a monitor (e.g. "add a monitor for...", "create a freshness check on...", "set up validation for...")
- Mentions monitoring a specific table, field, or metric
- Wants to check data quality rules or enforce data contracts
- Asks about monitoring options for a table or dataset
- Requests monitors-as-code YAML generation
- Wants to add monitoring after new transformation logic (when the prevent skill is not active)
- Asks about monitoring AI agents, agent latency, agent token usage, or agent quality
- Wants to set up alerts on agent behavior or execution patterns
- Asks about investigating agent traces or conversations
- Says things like "monitor my agent", "track agent latency", "alert on agent errors"
- Asks about agent evaluation monitors, trajectory monitors, or validation monitors
- Mentions agent observability or agent monitoring

## When NOT to activate this skill

Do not activate when the user is:

- Just querying data or exploring table contents
- Triaging or responding to active alerts (use the prevent skill's Workflow 3)
- Running impact assessments before code changes (use the prevent skill's Workflow 4)
- Asking about existing monitor configuration (use `get_monitors` directly)
- Editing or deleting existing monitors

---

## Prerequisites

- **Required:** Monte Carlo MCP server (`monte-carlo-mcp`) must be configured and authenticated
- **Optional:** A database MCP server (Snowflake, BigQuery, Redshift, Databricks) for SQL profiling of table usage patterns

---

## Available MCP tools

All tools are available via the `monte-carlo` MCP server.

### Coverage and discovery tools

| Tool | Purpose |
| --- | --- |
| `get_warehouses` | List accessible warehouses (needed first -- `get_use_cases` requires `warehouse_id`) |
| `get_use_cases` | List use cases with criticality, descriptions, table counts, precomputed tag names |
| `get_use_case_table_summary` | Criticality distribution (HIGH/MEDIUM/LOW table counts) for a use case |
| `get_use_case_tables` | Paginated tables with criticality, golden-table status, MCONs |
| `get_monitors` | Check monitoring status on specific tables via `mcons` filter |
| `get_asset_lineage` | Upstream/downstream dependencies for tables (takes MCONs + direction) |
| `get_audiences` | List notification audiences |
| `get_unmonitored_tables_with_anomalies` | Tables with muted OOTB anomalies but no monitors (takes ISO 8601 time range) |
| `search` | Find tables by name; supports `is_monitored` filter |
| `get_table` | Table details, fields, stats, domain membership |
| `get_queries_for_table` | Query logs for a table (source/destination) |
| `get_field_metric_definitions` | Available metrics per field type for a warehouse |
| `get_domains` | List Monte Carlo domains |
| `get_validation_predicates` | Available validation rule types |

### Data monitor creation tools

| Tool | Purpose |
| --- | --- |
| `create_table_monitor_mac` | Generate table monitor YAML (dry-run) |
| `create_metric_monitor_mac` | Generate metric monitor YAML (dry-run) |
| `create_validation_monitor_mac` | Generate validation monitor YAML (dry-run) |
| `create_custom_sql_monitor_mac` | Generate custom SQL monitor YAML (dry-run) |
| `create_comparison_monitor_mac` | Generate comparison monitor YAML (dry-run) |

### Agent monitoring tools

| Tool | Purpose |
| --- | --- |
| `get_agent_metadata` | List AI agents -- returns agent names, trace table MCONs, source types |
| `get_agent_conversation` | Retrieve recent LLM interactions/conversations for an agent |
| `get_agent_trace` | Inspect execution traces and span trees |
| `create_agent_metric_monitor` | Create monitors for quantitative span-level metrics |
| `create_agent_evaluation_monitor` | Create monitors for LLM-evaluated quality metrics |
| `create_agent_trajectory` | Create trajectory monitors for execution pattern alerts |
| `create_agent_validation` | Create validation monitors for logical assertions |

---

## Routing

When the user's request comes in, determine which workflow to follow:

| User intent | Workflow |
| --- | --- |
| Coverage analysis, use-case exploration, "what should I monitor?" | **Coverage workflow** (below) |
| Create a specific data monitor for a known table | **Read `references/data-monitor-creation.md`** and follow its procedure |
| Monitor AI agents, agent latency, agent quality, agent traces | **Read `references/agent-monitor-creation.md`** and follow its procedure |
| Coverage analysis leads to monitor creation | Complete coverage workflow, then **read `references/data-monitor-creation.md`** for creation |

When reading reference files, always use the **Read tool** with the path relative to this skill file.

---

## Coverage workflow

This is the primary flow when the user asks about monitoring coverage, coverage gaps, or what to monitor.

### Step 1: Discover warehouses

Call `get_warehouses` to list all accessible warehouses.

- If **one** warehouse: select it automatically, proceed to Step 2.
- If **multiple** warehouses: present warehouse **names** (never UUIDs) and ask the user which one to explore.

### Step 2: Discover use cases

Call `get_use_cases(warehouse_id=<selected>)` to discover use cases for the chosen warehouse.

- If **use cases exist** --> proceed to the **Use-case exploration** (below).
- If **no use cases** --> proceed to the **Importance-based fallback** (below).

### Step 3: Check for database MCP (optional)

Check if the user has a database MCP server available by looking for tools containing `snowflake`, `bigquery`, `redshift`, or `databricks` in the tool list. If found, note it for the SQL profiling step later. If not found, skip SQL profiling gracefully.

---

## Use-case exploration

This is the primary flow when use cases are defined.

### Present use cases

- Sort by criticality: **HIGH** before **MEDIUM** before **LOW**.
- For each use case, show the **description** and explain the **reasoning for its criticality level** so the user understands why it matters.
- Call `get_use_case_tables` with `golden_tables_only=true` and mention specific golden-table names as concrete examples. Golden tables are the last layer in the warehouse -- they feed ML models, dashboards, and reports. Explain this when relevant.
- Use `get_asset_lineage` to explain how tables in a use case are connected and why certain tables are important (e.g. a golden table with many upstream dependencies).

### Analyze coverage

1. Call `get_use_case_table_summary` to show how many tables exist at each criticality level (HIGH / MEDIUM / LOW) for the use case.
2. Call `get_use_case_tables` to obtain table MCONs, then call `get_monitors(mcons=[...])` to report how many are already monitored vs. not.
3. Ask the user which criticality scope they prefer:
   - **HIGH only** -- monitor only the most critical tables
   - **MEDIUM + HIGH** -- broader coverage
   - **ALL** -- full coverage including LOW-criticality tables
4. You may suggest covering **multiple** use cases in one session.

### Identify coverage gaps with anomaly data

Use `get_unmonitored_tables_with_anomalies` to discover tables that are **not monitored** but already have muted out-of-the-box anomalies. This reveals real coverage gaps -- places where Monte Carlo detected data issues but no monitor was configured to alert anyone.

- Call it with a recent time window (e.g. last 7-30 days) using ISO 8601 timestamps.
- Results are ranked by **importance score** -- the most critical gaps appear first.
- Each result includes a sample of anomaly events showing what types of issues were detected (freshness, volume, schema changes).
- Use this to **prioritize** which unmonitored tables to cover first -- a table with recent anomalies is a stronger candidate than one with no activity.
- Cross-reference with use-case data: if an unmonitored table with anomalies belongs to a critical use case, escalate its priority.

---

## Importance-based fallback

When no use cases are defined, fall back to importance-based table discovery.

1. **Find unmonitored tables:** Use `search(query="", is_monitored=false)` to find unmonitored tables sorted by importance.
2. **Find tables with anomalies:** Use `get_unmonitored_tables_with_anomalies` with a recent time window (last 14-30 days) to find tables with recent anomalies but no monitors.
3. **Inspect top candidates:** Use `get_table` to check table details, fields, and stats for the most important unmonitored tables.
4. **Understand criticality via lineage:** Use `get_asset_lineage` to understand which tables are most connected -- tables with many downstream dependencies are higher priority.
5. **Prioritize:** Rank candidates by importance score and anomaly activity. Present the top candidates to the user with reasoning.

---

## SQL profiling (optional)

If a database MCP server was detected in Step 3 of the coverage workflow:

1. Call `get_queries_for_table` to see recent query patterns on candidate tables.
2. Use the database MCP tools (e.g. `snowflake_query`, `bigquery_query`) to profile table usage -- identify which tables are queried most frequently, which columns are used in JOINs and WHERE clauses.
3. Use this information to refine monitor suggestions -- heavily-queried tables with no monitors are high-priority gaps.

If no database MCP is available, skip this step entirely. Do not ask the user to configure one.

---

## Pre-creation context (coverage-driven)

When coverage analysis leads to monitor creation, gather this context before reading the creation reference file:

1. Call `get_audiences` to list available notification audiences. Ask the user which audience they want notifications sent to.
2. Ask whether the monitor should be created as a **DRAFT** or active.
3. When passing `audiences` or `failure_audiences`, use the audience **name/label** (not UUID).

### Use-case tag monitors

The most common output of coverage analysis is a **table monitor scoped by use-case tags** via `create_table_monitor_mac`. The `asset_selection` parameter uses this structure:

```json
{
  "databases": ["<database_name>"],
  "schemas": ["<schema_name>"],
  "filters": [
    {
      "type": "TABLE_TAG",
      "tableTags": ["<tag_key>:<criticality>"],
      "tableTagsOperator": "HAS_ANY"
    }
  ]
}
```

Rules:
- Filter `type` is **always** `TABLE_TAG` for use-case monitors.
- `tableTagsOperator` should be `HAS_ANY`.
- Each entry in `tableTags` is `"<tag_key>:<value>"` where the tag key is the precomputed tag name from `get_use_cases` output and the value is the criticality level in lowercase (`high`, `medium`, `low`).
- To monitor only HIGH-criticality tables: `["tag_name:high"]`
- To monitor MEDIUM + HIGH: `["tag_name:high", "tag_name:medium"]`
- To monitor ALL: `["tag_name:high", "tag_name:medium", "tag_name:low"]`

### Monitor description guidelines

Write a clear, meaningful `description` that explains what the monitor covers and why. The backend auto-generates the monitor `name` -- you cannot control it, but the description is what users see.

- **Bad:** `"Data Quality Monitoring - HIGH criticality table monitor"`
- **Good:** `"Monitor HIGH criticality tables in the Revenue Reporting use case to catch issues before they affect dashboards and financial reports."`

The description should mention the criticality scope, the use case name, and a brief reason why this monitoring matters.

---

## Transient and truncate-and-reload tables

Some tables show 0 rows when queried directly but have recent write activity in Monte Carlo metadata. These are **transient tables** -- fully replaced on each pipeline run (truncate-and-reload pattern). Recognize this pattern early to avoid wasting time querying empty tables.

Signs of a transient table:
- `get_table` shows recent `last_write` timestamp and high read/write activity
- Direct SQL query returns 0 rows or all-NULL timestamp columns
- Monte Carlo detected freshness anomalies (the table stayed empty longer than expected between loads)

---

## Graceful degradation

Handle missing or unavailable tools gracefully:

| Scenario | Behavior |
| --- | --- |
| No use cases defined | Fall back to importance-based discovery |
| No database MCP available | Skip SQL profiling, rely on MC tools only |
| `get_unmonitored_tables_with_anomalies` returns empty | Note that no recent anomalies were found; proceed with use-case or importance-based prioritization |
| `get_use_case_tables` returns no tables | Note the use case has no tables; suggest exploring other use cases |
| `get_audiences` returns empty | Inform user no audiences are configured; monitors can still be created without notification routing |
| User has no warehouses | Inform user that no warehouses are accessible; they may need to check their Monte Carlo permissions |

Never error out or stop the conversation because one tool returned empty results. Explain what happened and offer the next best path.

---

## Rules

- **Never expose UUIDs, MCONs, or internal identifiers** to the user -- always use human-readable names for warehouses, audiences, use cases, and tables. Keep internal identifiers for tool calls only.
- When the user asks about relationships between tables, use `get_asset_lineage` to fetch upstream/downstream connections and explain the data flow.
- Be concise but thorough. Use bullet points and tables for clarity.
- Always use **ISO 8601** format for datetime values in tool calls.
- Never reformat YAML values returned by creation tools.
- When passing `audiences` or `failure_audiences` to monitor creation tools, use the audience **name/label** (not UUID). The API accepts audience names.
