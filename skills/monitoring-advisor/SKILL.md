---
name: monte-carlo-monitoring-advisor
description: |
  Analyze data coverage and create monitoring for critical use cases and AI agents.
  Activates when the user asks about monitoring coverage, data coverage gaps,
  use case analysis, what's monitored vs. not, or monitoring AI agents.
version: 1.0.0
---

# Monte Carlo Monitoring Advisor Skill

This skill helps you analyze a user's data estate, discover critical use cases, identify coverage gaps, and suggest or create monitors to protect what matters most. It is the interactive counterpart to Monte Carlo's coverage analysis — walking the user through warehouse discovery, use-case exploration, and monitor creation.

When the user is ready to create monitors, **hand off to the monitor-creation skill** (`../monitor-creation/SKILL.md`). It contains the full validation, parameter guidance, and creation workflow. This skill focuses on the coverage analysis that leads up to monitor creation.

## When to activate this skill

Activate when the user:

- Asks about monitoring coverage, data coverage, or coverage gaps
- Wants to understand what's monitored vs. not in their warehouse
- Asks about use cases, use-case criticality, or use-case analysis
- Wants to explore their data estate and find what needs monitoring
- Says things like "what should I monitor?", "where are my coverage gaps?", "show me my use cases"
- Asks about unmonitored tables with anomalies or importance-based prioritization
- Asks about monitoring AI agents, agent latency, agent token usage, or agent quality

## When NOT to activate this skill

Do not activate when the user is:

- Asking to create a specific monitor for a known table (use the monitor-creation skill)
- Triaging or responding to active alerts (use the prevent skill's Workflow 3)
- Running impact assessments before code changes (use the prevent skill's Workflow 4)
- Editing or deleting existing monitors

---

## Prerequisites

- **Required:** Monte Carlo MCP server (`monte-carlo-mcp`) must be configured and authenticated
- **Optional:** A database MCP server (Snowflake, BigQuery, Redshift, Databricks) for SQL profiling of table usage patterns

---

## Available MCP tools

All tools are available via the `monte-carlo` MCP server.

| Tool | Purpose |
| --- | --- |
| `getWarehouses` | List accessible warehouses (needed first — `getUseCases` requires `warehouse_id`) |
| `getUseCases` | List use cases with criticality, descriptions, table counts, precomputed tag names |
| `getUseCaseTableSummary` | Criticality distribution (HIGH/MEDIUM/LOW table counts) for a use case |
| `getUseCaseTables` | Paginated tables with criticality, golden-table status, MCONs |
| `getMonitors` | Check monitoring status on specific tables via `mcons` filter |
| `getAssetLineage` | Upstream/downstream dependencies for tables (takes MCONs + direction) |
| `getAudiences` | List notification audiences |
| `getUnmonitoredTablesWithAnomalies` | Tables with muted OOTB anomalies but no monitors (takes ISO 8601 time range) |
| `search` | Find tables by name; supports `is_monitored` filter |
| `getTable` | Table details, fields, stats, domain membership |
| `getQueriesForTable` | Query logs for a table (source/destination) |
| `getFieldMetricDefinitions` | Available metrics per field type for a warehouse |
| `getDomains` | List Monte Carlo domains |
| `getValidationPredicates` | Available validation rule types |
| `createTableMonitorMac` | Generate table monitor YAML (dry-run) |
| `createMetricMonitorMac` | Generate metric monitor YAML (dry-run) |
| `createValidationMonitorMac` | Generate validation monitor YAML (dry-run) |
| `createCustomSqlMonitorMac` | Generate custom SQL monitor YAML (dry-run) |
| `createComparisonMonitorMac` | Generate comparison monitor YAML (dry-run) |
| `get_agent_metadata` | List AI agents — returns agent names, trace table MCONs, source types |
| `get_agent_conversation` | Retrieve recent LLM interactions/conversations for an agent |
| `get_agent_trace` | Inspect execution traces and span trees |
| `create_agent_metric_monitor` | Create monitors for quantitative span-level metrics |
| `create_agent_evaluation_monitor` | Create monitors for LLM-evaluated quality metrics |
| `create_agent_trajectory` | Create trajectory monitors for execution pattern alerts |
| `create_agent_validation` | Create validation monitors for logical assertions |

---

## First-turn protocol

Follow this sequence at the start of every conversation. Do NOT skip steps.

### Step 1: Discover warehouses

Call `getWarehouses` to list all accessible warehouses.

- If **one** warehouse: select it automatically, proceed to Step 2.
- If **multiple** warehouses: present warehouse **names** (never UUIDs) and ask the user which one to explore.

### Step 2: Discover use cases

Call `getUseCases(warehouse_id=<selected>)` to discover use cases for the chosen warehouse.

- If **use cases exist** → proceed to the **Use-case workflow** (below).
- If **no use cases** → proceed to the **Importance-based fallback** (below).

### Step 3: AI agent monitoring (conditional)

If the user asks about monitoring AI agents, **read and follow the agent-monitoring skill** (`../agent-monitoring/SKILL.md`). It covers agent discovery, trace investigation, and creation of all 4 agent monitor types (metric, evaluation, trajectory, validation). Call `get_agent_metadata` to list all AI agents, then follow the agent-monitoring skill's step-by-step workflow.

### Step 4: Check for database MCP (optional)

Check if the user has a database MCP server available by looking for tools containing `snowflake`, `bigquery`, `redshift`, or `databricks` in the tool list. If found, note it for the SQL profiling step later. If not found, skip SQL profiling gracefully.

---

## Use-case workflow

This is the primary flow when use cases are defined.

### Present use cases

- Sort by criticality: **HIGH** before **MEDIUM** before **LOW**.
- For each use case, show the **description** and explain the **reasoning for its criticality level** so the user understands why it matters.
- Call `getUseCaseTables` with `golden_tables_only=true` and mention specific golden-table names as concrete examples. Golden tables are the last layer in the warehouse — they feed ML models, dashboards, and reports. Explain this when relevant.
- Use `getAssetLineage` to explain how tables in a use case are connected and why certain tables are important (e.g. a golden table with many upstream dependencies).

### Analyze coverage

1. Call `getUseCaseTableSummary` to show how many tables exist at each criticality level (HIGH / MEDIUM / LOW) for the use case.
2. Call `getUseCaseTables` to obtain table MCONs, then call `getMonitors(mcons=[...])` to report how many are already monitored vs. not.
3. Ask the user which criticality scope they prefer:
   - **HIGH only** — monitor only the most critical tables
   - **MEDIUM + HIGH** — broader coverage
   - **ALL** — full coverage including LOW-criticality tables
4. You may suggest covering **multiple** use cases in one session.

### Identify coverage gaps with anomaly data

Use `getUnmonitoredTablesWithAnomalies` to discover tables that are **not monitored** but already have muted out-of-the-box anomalies. This reveals real coverage gaps — places where Monte Carlo detected data issues but no monitor was configured to alert anyone.

- Call it with a recent time window (e.g. last 7–30 days) using ISO 8601 timestamps.
- Results are ranked by **importance score** — the most critical gaps appear first.
- Each result includes a sample of anomaly events showing what types of issues were detected (freshness, volume, schema changes).
- Use this to **prioritize** which unmonitored tables to cover first — a table with recent anomalies is a stronger candidate than one with no activity.
- Cross-reference with use-case data: if an unmonitored table with anomalies belongs to a critical use case, escalate its priority.

---

## Importance-based fallback

When no use cases are defined, fall back to importance-based table discovery.

1. **Find unmonitored tables:** Use `search(query="", is_monitored=false)` to find unmonitored tables sorted by importance.
2. **Find tables with anomalies:** Use `getUnmonitoredTablesWithAnomalies` with a recent time window (last 14–30 days) to find tables with recent anomalies but no monitors.
3. **Inspect top candidates:** Use `getTable` to check table details, fields, and stats for the most important unmonitored tables.
4. **Understand criticality via lineage:** Use `getAssetLineage` to understand which tables are most connected — tables with many downstream dependencies are higher priority.
5. **Prioritize:** Rank candidates by importance score and anomaly activity. Present the top candidates to the user with reasoning.

---

## SQL profiling (optional)

If a database MCP server was detected in Step 3 of the first-turn protocol:

1. Call `getQueriesForTable` to see recent query patterns on candidate tables.
2. Use the database MCP tools (e.g. `snowflake_query`, `bigquery_query`) to profile table usage — identify which tables are queried most frequently, which columns are used in JOINs and WHERE clauses.
3. Use this information to refine monitor suggestions — heavily-queried tables with no monitors are high-priority gaps.

If no database MCP is available, skip this step entirely. Do not ask the user to configure one.

---

## Monitor creation

When the user is ready to create monitors, **read and follow the monitor-creation skill** (`../monitor-creation/SKILL.md`). It handles monitor type selection, table/column validation, domain assignment, scheduling, confirmation, and YAML generation.

This section covers only the guidance specific to coverage-driven monitor creation.

### Pre-creation context

Before handing off to the monitor-creation workflow:

1. Call `getAudiences` to list available notification audiences. Ask the user which audience they want notifications sent to.
2. Ask whether the monitor should be created as a **DRAFT** or active.
3. When passing `audiences` or `failure_audiences`, use the audience **name/label** (not UUID).

### Use-case tag monitors

The most common output of coverage analysis is a **table monitor scoped by use-case tags** via `createTableMonitorMac`. The `asset_selection` parameter uses this structure:

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
- Each entry in `tableTags` is `"<tag_key>:<value>"` where the tag key is the precomputed tag name from `getUseCases` output and the value is the criticality level in lowercase (`high`, `medium`, `low`).
- To monitor only HIGH-criticality tables: `["tag_name:high"]`
- To monitor MEDIUM + HIGH: `["tag_name:high", "tag_name:medium"]`
- To monitor ALL: `["tag_name:high", "tag_name:medium", "tag_name:low"]`

### Monitor description guidelines

Write a clear, meaningful `description` that explains what the monitor covers and why. The backend auto-generates the monitor `name` — you cannot control it, but the description is what users see.

- **Bad:** `"Data Quality Monitoring - HIGH criticality table monitor"`
- **Good:** `"Monitor HIGH criticality tables in the Revenue Reporting use case to catch issues before they affect dashboards and financial reports."`

The description should mention the criticality scope, the use case name, and a brief reason why this monitoring matters.

---

## AI Agent Monitoring

When the user asks about monitoring AI agents, investigating agent behavior, or creating agent monitors, **read and follow the agent-monitoring skill** (`../agent-monitoring/SKILL.md`). It contains the full discovery, investigation, and monitor creation workflow for AI agents.

The agent-monitoring skill covers 4 monitor types:
- **Agent Metric** — track latency (`duration_sec`), token usage, span volume
- **Agent Evaluation** — LLM-evaluated quality scores with sampling and transforms
- **Agent Trajectory** — execution pattern alerts on span sequences
- **Agent Validation** — logical assertions on span data

All agent monitors target the `traceTableMcon` returned by `get_agent_metadata` — never use a regular table MCON. The agent-monitoring skill's reference docs (`references/metric-monitor.md`, etc.) have detailed parameter guides and examples.

---

## Transient and truncate-and-reload tables

Some tables show 0 rows when queried directly but have recent write activity in Monte Carlo metadata. These are **transient tables** — fully replaced on each pipeline run (truncate-and-reload pattern). Recognize this pattern early to avoid wasting time querying empty tables.

Signs of a transient table:
- `getTable` shows recent `last_write` timestamp and high read/write activity
- Direct SQL query returns 0 rows or all-NULL timestamp columns
- Monte Carlo detected freshness anomalies (the table stayed empty longer than expected between loads)

---

## Graceful degradation

Handle missing or unavailable tools gracefully:

| Scenario | Behavior |
| --- | --- |
| No use cases defined | Fall back to importance-based discovery |
| No database MCP available | Skip SQL profiling, rely on MC tools only |
| `getUnmonitoredTablesWithAnomalies` returns empty | Note that no recent anomalies were found; proceed with use-case or importance-based prioritization |
| `getUseCaseTables` returns no tables | Note the use case has no tables; suggest exploring other use cases |
| `getAudiences` returns empty | Inform user no audiences are configured; monitors can still be created without notification routing |
| User has no warehouses | Inform user that no warehouses are accessible; they may need to check their Monte Carlo permissions |

Never error out or stop the conversation because one tool returned empty results. Explain what happened and offer the next best path.

---

## Rules

- **Never expose UUIDs, MCONs, or internal identifiers** to the user — always use human-readable names for warehouses, audiences, use cases, and tables. Keep internal identifiers for tool calls only.
- When the user asks about relationships between tables, use `getAssetLineage` to fetch upstream/downstream connections and explain the data flow.
- Be concise but thorough. Use bullet points and tables for clarity.
- Always use **ISO 8601** format for datetime values in tool calls.
- Never reformat YAML values returned by creation tools.
- When passing `audiences` or `failure_audiences` to monitor creation tools, use the audience **name/label** (not UUID). The API accepts audience names.
