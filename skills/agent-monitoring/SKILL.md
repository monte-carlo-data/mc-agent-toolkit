---
name: agent-monitoring
description: |
  Investigation and monitor creation guide for AI agent observability.
  Activates when the user asks about monitoring AI agents, setting up alerts
  on agent behavior, investigating agent traces, or creating agent monitors.
version: 1.0.0
---

# Agent Monitoring: Investigation and Monitor Creation Guide

Use this guide when the user asks about monitoring their AI agents — setting
up alerts on agent behavior, investigating agent traces, or creating agent
monitors. Follow the steps **in order**.

Reference files live next to this skill file. **Use the Read tool** (not MCP resources) to access them:

- Metric monitor creation guide: `references/metric-monitor.md` (relative to this file)
- Evaluation monitor creation guide: `references/evaluation-monitor.md` (relative to this file)
- Trajectory monitor creation guide: `references/trajectory-monitor.md` (relative to this file)
- Validation monitor creation guide: `references/validation-monitor.md` (relative to this file)
- Known span field names: `references/span-fields.md` (relative to this file)

## When to activate this skill

Activate when the user:

- Asks about monitoring AI agents, agent latency, agent token usage, or agent quality
- Wants to set up alerts on agent behavior or execution patterns
- Asks about investigating agent traces or conversations
- Says things like "monitor my agent", "track agent latency", "alert on agent errors"
- Asks about agent evaluation monitors, trajectory monitors, or validation monitors
- Mentions agent observability or agent monitoring

## When NOT to activate this skill

Do not activate when the user is:

- Asking about data pipeline monitoring (use the prevent or monitoring-advisor skill)
- Creating monitors on regular warehouse tables (use the monitor-creation skill)
- Triaging data quality alerts (use the prevent skill's Workflow 3)
- Running impact assessments before code changes (use the prevent skill's Workflow 4)

---

## Available MCP tools

All tools are available via the `monte-carlo` MCP server.

| Tool | Purpose |
| --- | --- |
| `get_agent_metadata` | List AI agents — returns agent names, trace table MCONs, and source types |
| `get_agent_conversation` | Retrieve recent LLM interactions/conversations for an agent |
| `get_agent_trace` | Inspect execution traces and span trees |
| `create_agent_metric_monitor` | Create monitors for quantitative span-level metrics |
| `create_agent_evaluation_monitor` | Create monitors for LLM-evaluated quality metrics |
| `create_agent_trajectory` | Create trajectory monitors for execution pattern alerts |
| `create_agent_validation` | Create validation monitors for logical assertions |
| `getAudiences` | List notification audiences |

---

## Step 1: Discover agents

Call `get_agent_metadata` to list all AI agents in the account. Present agent
names to the user (never expose MCONs or internal IDs). Ask which agent(s)
they want to monitor.

Key fields in the response:
- `agentName` — the human-readable agent name
- `traceTableMcon` — needed as the `data_source` when creating monitors
- `sourceType` — `TRACE_TABLE` (custom) or `PLATFORM_AGENT` (Monte Carlo native)

**MCON usage:** The `traceTableMcon` returned by `get_agent_metadata` must be
used **exactly as-is** in the `data_source.mcon` field when creating monitors.
Do not modify, truncate, or reconstruct it. If a monitor creation fails with
"table must be validated", verify the MCON matches exactly what
`get_agent_metadata` returned.

**Duplicate agents across warehouses:** The same agent name may appear in
multiple warehouses (e.g., the agent is deployed in both prod and staging).
When this happens, present the warehouse **names** (never UUIDs) and ask the
user which warehouse they want to monitor. Each warehouse has a different
`traceTableMcon`, so the choice determines which data source the monitor
uses.

## Step 2: Investigate agent behavior

Use the read tools to understand the agent's behavior before suggesting monitors.

### 2a. Review recent conversations

Call `get_agent_conversation` with the agent's `agent_name` and
`trace_table_mcon` to see recent LLM interactions. Look for:
- **Error patterns** — spans with error status or failure indicators
- **Latency outliers** — unusually long durations
- **Token usage** — high token counts that may indicate inefficiency
- **Conversation quality** — check prompt/completion text for relevance

### 2b. Inspect execution traces

Pick a few trace IDs from the conversation results and call `get_agent_trace`
to see the full span tree. Look for:
- **Excessive tool calls** — an agent calling the same tool many times
- **Missing steps** — expected spans that don't appear
- **Error cascades** — a failed span causing downstream failures
- **Unusual paths** — the agent taking an unexpected execution route

---

## General rules

- Agent monitors can ONLY be created on the `traceTableMcon` returned by
  `get_agent_metadata`. You cannot use any other table or MCON — the API
  will reject it with "table must be validated"
- Always use `FIXED` (uppercase) for `scheduleType` in schedule configs
- Always use `ingest_ts` as the `timeField` for time filters
- Use `duration_sec` (not `duration_ms`) for latency monitoring
- Use `total_tokens`, `prompt_tokens`, `completion_tokens` for token monitoring
- Use `ROW_COUNT_CHANGE` metric without `fields` array for volume monitoring
- Agent span filters always need at least the `agent` field set
- Trajectory `agentSpanFilters`: only the `agent` field is allowed — do not set `workflow`, `task`, or `spanName` (use `spanField` in the alert condition instead)
- Always use the exact `traceTableMcon` from `get_agent_metadata` as the `data_source.mcon` — never modify it
- Use predefined transforms when possible — they have known output field names (see evaluation monitor reference)

## Agent span filters

The `agent_span_filters` parameter narrows which spans are monitored. Each
filter is an object with optional fields: `agent`, `workflow`, `task`,
`spanName`. Each field contains a `{"value": "..."}` sub-object.

| Filter field | Description | Example |
|-------------|-------------|---------|
| `agent` | Filter by agent name | `{"agent": {"value": "My Agent"}}` |
| `workflow` | Filter by workflow name | `{"workflow": {"value": "Chat Agent"}}` |
| `task` | Filter by task name | `{"task": {"value": "call_model"}}` |
| `spanName` | Filter by span name | `{"spanName": {"value": "ChatBedrockConverse.chat"}}` |

Multiple fields can be combined in one filter object. Example:
`[{"agent": {"value": "My Agent"}, "workflow": {"value": "Chat Agent"}, "task": {"value": "call_model"}}]`

Always include at least the `agent` field in span filters.

## Schedule configuration

Common schedule patterns:
- **Hourly**: `{"scheduleType": "FIXED", "intervalMinutes": 60}`
- **Every 6 hours**: `{"scheduleType": "FIXED", "intervalMinutes": 360}`
- **Daily**: `{"scheduleType": "FIXED", "intervalMinutes": 1440}`

Valid `scheduleType` values: `FIXED`, `LOOSE`, `DYNAMIC`, `MANUAL` (always uppercase).

Use shorter intervals for critical agents, longer for less critical ones.

## Time filter configuration

Used by trajectory and validation monitors. The `timeField` is an object with
a `field` property — always use `ingest_ts`:

```json
{"timeField": {"field": "ingest_ts"}, "lookbackInHrs": 24}
```

---

## Step 3: Choose the right monitor type

Based on your investigation, recommend one or more monitor types. Read the
corresponding reference doc for the detailed creation guide.

| I want to... | Monitor type | Reference |
|-------------|-------------|-----------|
| Track a numeric metric trend (latency, tokens) | Agent Metric | `references/metric-monitor.md` |
| Score output quality with LLM evaluation | Agent Evaluation | `references/evaluation-monitor.md` |
| Alert on execution patterns or span sequences | Agent Trajectory | `references/trajectory-monitor.md` |
| Assert a logical rule on span data | Agent Validation | `references/validation-monitor.md` |
| Monitor span volume over time | Agent Metric | `references/metric-monitor.md` |
| Detect answer relevance drops | Agent Evaluation | `references/evaluation-monitor.md` |
| Catch runaway tool call loops | Agent Trajectory | `references/trajectory-monitor.md` |
| Ensure token count stays below threshold | Agent Validation | `references/validation-monitor.md` |

After selecting the monitor type, **read the reference doc** for that type to
get the detailed parameter guide, examples, and creation workflow.

## Step 4: Create the monitor

1. **Always start with `dry_run=True`** (the default). Show the user the
   generated queries and configuration preview.
2. Call `getAudiences` to list available audiences. Suggest the
   most relevant one and ask the user to pick.
3. After showing the preview, offer to create or adjust settings.
4. Only set `dry_run=False` when the user explicitly confirms creation.

---

## Common errors

| Error message | Cause | Fix |
|--------------|-------|-----|
| "table must be validated" | MCON doesn't match a registered table | Verify the exact `traceTableMcon` from `get_agent_metadata` — use it as-is, do not modify |
| "workflow should not be set" in agentSpanFilters | Trajectory monitors only allow the `agent` field in `agentSpanFilters` | Remove `workflow`, `task`, and `spanName` from `agentSpanFilters`; use `spanField` in the alert condition instead |
| "Field X doesn't exist" | Field name not in the PARSED_SPANS schema, or wrong transform output field name | Check `references/span-fields.md`; for evaluation monitors, verify the transform output field name |
| "Expected type ScheduleType" | Schedule type is lowercase or invalid | Use `FIXED` (uppercase) — all schedule type values must be uppercase |
