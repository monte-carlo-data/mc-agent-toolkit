# Agent Monitor Creation Procedure

This is the agent monitor creation procedure for AI agent observability. Follow
these steps in order when a user asks to monitor their AI agents — setting up
alerts on agent behavior, investigating agent traces, or creating agent monitors.

All tools are available via the `monte-carlo-mcp` MCP server.

---

## Step 1: Discover agents

Call `get_agent_metadata` to list all AI agents in the account. Present agent
names to the user (never expose MCONs or internal IDs). Ask which agent(s)
they want to monitor.

Key fields in the response:

| Field | Description |
|-------|-------------|
| `agentName` | Human-readable agent name |
| `agentReference` | The value to pass as the `agent` arg when creating monitors — a platform `{database}:{schema}.{name}` reference (Snowflake Cortex / Databricks) or an OpenTelemetry `service_name`. May be null for agents that cannot be referenced. |
| `traceTableMcon` | Trace table MCON — used as the `trace_table_mcon` input for `get_agent_conversation`/`get_agent_trace` |
| `sourceType` | `TRACE_TABLE` (custom) or `PLATFORM_AGENT` (Monte Carlo native) |

**Duplicate agents across warehouses:** The same agent name may appear in
multiple warehouses (e.g., deployed in both prod and staging). When this
happens, present the warehouse **names** (never UUIDs) and ask the user which
warehouse they want to monitor. Pass the chosen warehouse as the `warehouse`
arg (name or UUID) when the agent reference does not pin it down.

---

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

## The `agent` reference

All four `create_or_update_agent_*_monitor` tools author the monitor's source via
a single top-level **`agent`** argument — there is no `dw_id` or `data_source`/MCON.
Two accepted forms:

- **Platform agent reference** — `{database}:{schema}.{name}` (Snowflake Cortex /
  Databricks agents), e.g. `analytics:agents.support_bot`.
- **OpenTelemetry `service_name`** — for OTel-instrumented agents, e.g. `checkout-agent`.

Get the exact value from `get_agent_metadata`'s **`agentReference`** field — never
construct it by hand. Two optional companions:

- `warehouse` (name or UUID) — only needed when the agent reference doesn't pin down
  the warehouse. Resolve names via `get_warehouses`.
- `trace_table` — only for non-ClickHouse OTel agents whose trace storage cannot be
  inferred from the agent reference.

---

## Agent span filters

The optional `agent_span_filters` parameter refines which spans are monitored. Each
filter is an object with optional fields: `agent`, `workflow`, `task`, `spanName`.
Each field contains a `{"value": "..."}` sub-object.

| Filter field | Description | Example |
|-------------|-------------|---------|
| `agent` | Filter by agent name | `{"agent": {"value": "My Agent"}}` |
| `workflow` | Filter by workflow name | `{"workflow": {"value": "Chat Agent"}}` |
| `task` | Filter by task name | `{"task": {"value": "call_model"}}` |
| `spanName` | Filter by span name | `{"spanName": {"value": "ChatBedrockConverse.chat"}}` |

Multiple fields can be combined in one filter object. Example:
```json
[{"agent": {"value": "My Agent"}, "workflow": {"value": "Chat Agent"}, "task": {"value": "call_model"}}]
```

`agent_span_filters` is a refinement and is optional — the `agent` reference already
scopes the monitor. (Trajectory monitors are the exception: there `agent_span_filters`
may set ONLY the `agent` field — see `agent-trajectory-monitor.md`.)

---

## Schedule configuration

Schedule is set via two top-level args, not a nested object:

- `schedule_type` — defaults to `fixed`. Valid values: `fixed`, `dynamic`, `manual`.
- `interval_minutes` — defaults to `60` for `fixed`. Common patterns: `60` (hourly),
  `360` (every 6 hours), `1440` (daily).

Omit both to accept the hourly fixed default. Use shorter intervals for critical
agents, longer for less critical ones.

---

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

| I want to... | Monitor type | Reference file |
|-------------|-------------|----------------|
| Track a numeric metric trend (latency, tokens) | Agent Metric | `agent-metric-monitor.md` |
| Score output quality with LLM evaluation | Agent Evaluation | `agent-evaluation-monitor.md` |
| Alert on execution patterns or span sequences | Agent Trajectory | `agent-trajectory-monitor.md` |
| Assert a logical rule on span data | Agent Validation | `agent-validation-monitor.md` |
| Monitor span volume over time | Agent Metric | `agent-metric-monitor.md` |
| Detect answer relevance drops | Agent Evaluation | `agent-evaluation-monitor.md` |
| Catch runaway tool call loops | Agent Trajectory | `agent-trajectory-monitor.md` |
| Ensure token count stays below threshold | Agent Validation | `agent-validation-monitor.md` |

After selecting the monitor type, **read the reference doc** for that type to
get the detailed parameter guide, examples, constraints, and creation workflow.

---

## Step 4: Create the monitor

All four tools follow the same **two-call preview-then-confirm pattern** as the data
monitor tools: the first call (`dry_run=True`, the default) returns the rendered MaC
YAML for review; the second call (`dry_run=False`) deploys the monitor live and
returns its UUID. Pass `monitor_uuid` on either call to update an existing agent
monitor in place instead of creating a new one (PUT semantics — re-pass every field
you want to keep).

1. **Always start with `dry_run=True`** (the default). Show the user the
   configuration preview (the rendered YAML).
2. Call `get_audiences` to list available notification audiences. Suggest the
   most relevant one and ask the user to pick. Pass audience **names** (not UUIDs)
   as the `audiences` list.
3. After showing the preview, offer to create or adjust settings.
4. Only set `dry_run=False` when the user explicitly confirms creation.

---

## Field name reference

See `agent-span-fields.md` for the complete list of known span field names
available in agent monitors. Do not guess field names — use only the ones
documented there.
