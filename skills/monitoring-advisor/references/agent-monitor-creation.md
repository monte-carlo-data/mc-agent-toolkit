# Agent Monitor Creation Procedure

This is the agent monitor creation procedure for AI agent observability. Follow
these steps in order when a user asks to monitor their AI agents — setting up
alerts on agent behavior, investigating agent traces, or creating agent monitors.

All tools are available via the `monte-carlo` MCP server.

---

## Step 1: Discover agents

Call `get_agent_metadata` to list all AI agents in the account. Present agent
names to the user (never expose MCONs or internal IDs). Ask which agent(s)
they want to monitor.

Key fields in the response:

| Field | Description |
|-------|-------------|
| `agentName` | Human-readable agent name |
| `traceTableMcon` | Needed as the `data_source.mcon` when creating monitors |
| `sourceType` | `TRACE_TABLE` (custom) or `PLATFORM_AGENT` (Monte Carlo native) |

**Duplicate agents across warehouses:** The same agent name may appear in
multiple warehouses (e.g., deployed in both prod and staging). When this
happens, present the warehouse **names** (never UUIDs) and ask the user which
warehouse they want to monitor. Each warehouse has a different
`traceTableMcon`, so the choice determines which data source the monitor uses.

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
```json
[{"agent": {"value": "My Agent"}, "workflow": {"value": "Chat Agent"}, "task": {"value": "call_model"}}]
```

Always include at least the `agent` field in span filters.

---

## Schedule configuration

Common schedule patterns:

- **Hourly**: `{"scheduleType": "FIXED", "intervalMinutes": 60}`
- **Every 6 hours**: `{"scheduleType": "FIXED", "intervalMinutes": 360}`
- **Daily**: `{"scheduleType": "FIXED", "intervalMinutes": 1440}`

Valid `scheduleType` values: `FIXED`, `LOOSE`, `DYNAMIC`, `MANUAL` (always uppercase).

Use shorter intervals for critical agents, longer for less critical ones.

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

1. **Always start with `dry_run=True`** (the default). Show the user the
   generated queries and configuration preview.
2. Call `get_audiences` to list available notification audiences. Suggest the
   most relevant one and ask the user to pick.
3. After showing the preview, offer to create or adjust settings.
4. Only set `dry_run=False` when the user explicitly confirms creation.

---

## Field name reference

See `agent-span-fields.md` for the complete list of known span field names
available in agent monitors. Do not guess field names — use only the ones
documented there.
