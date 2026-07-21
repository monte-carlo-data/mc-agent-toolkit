# Agent Monitor Creation Procedure

This is the agent monitor creation procedure for AI agent observability. Follow
these steps in order when a user asks to monitor their AI agents — setting up
alerts on agent behavior or creating agent monitors.

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
| `traceTableMcon` | Trace table MCON — used as the `trace_table_mcon` input for the read tools (`get_agent_conversations`, `get_agent_conversation`, `get_agent_traces`, `get_agent_segments`; the parameter is named `mcon` on `get_agent_trace`) |
| `sourceType` | `TRACE_TABLE` (custom) or `PLATFORM_AGENT` (Monte Carlo native) |
| `backend_class` | Which backend the agent's traces live in — `ao_clickhouse_otel`, `platform_agent`, `customer_otel_trace_table`, `databricks_genie`, `databricks_mlflow_sdk`, or `databricks_mlflow_ka`. Null when the server could not classify the agent (or predates the field). |
| `warehouse_uuid` | Warehouse holding the agent's trace data — the value to pass as the `warehouse` arg when creating monitors. Null when the warehouse was deleted or cannot be resolved; fall back to `get_warehouses` (see Warehouse below). |
| `warehouse_name` | Display name of that warehouse — what you show the user. Null alongside `warehouse_uuid`; fall back to `get_warehouses`. |

**What `backend_class` tells you about capabilities:** conversation-grain
evaluation monitors (`is_agent_conversation_aggregation=True`) are supported for
`ao_clickhouse_otel`, `platform_agent` (Snowflake Cortex), and `databricks_genie`;
the MLflow classes are span-only (the backend rejects conversation aggregation for
them). `databricks_genie` agents emit no token or model data — skip token-usage
metrics for them (see `agent-metric-monitor.md`). A null `backend_class` means the
server couldn't classify the agent — default to span-grain proposals.

**Duplicate agent names:** The same agent name may appear more than once (e.g.,
deployed in both prod and staging). Each entry is distinguished by its own
`agentReference`, `traceTableMcon`, and warehouse — ask the user which one they
want to monitor and pass that entry's `agentReference` verbatim. When you ask the
user to choose, present each entry's `warehouse_name`, never a UUID.

---

## Step 2: Investigate agent behavior

Use the read tools to understand the agent's behavior before suggesting monitors.
These read tools are your sampling surface — do **not** query the trace store with
SQL. Agents are tracked as agents, not tables: platform agents (Snowflake Cortex /
Databricks) have no queryable trace table, and for custom agents the raw table's
columns are not the fields monitors use.

### 2a. Review recent conversations

Call `get_agent_conversations` with the agent's `agent_name` and `trace_table_mcon`
to list recent conversations (newest first). Filter to surface interesting ones —
`has_errors`, `status`, or turn/token/duration bounds — and set
`include_transcript=True` to read the prompt/completion transcripts inline. Drill
into one conversation you already have the id for with `get_agent_conversation`.
Look for:

- **Error patterns** — spans with error status or failure indicators
- **Latency outliers** — unusually long durations
- **Token usage** — high token counts that may indicate inefficiency
- **Conversation quality** — check prompt/completion text for relevance

### 2b. Inspect execution shape and traces

Call `get_agent_traces` to list traces with per-trace `workflows`, `tasks`,
`models`, `count_llm_calls`, `total_tokens`, `duration_seconds`, and error counts —
sort by the field you plan to monitor to see typical values and outliers. Call
`get_agent_segments` to enumerate the distinct `workflow` / `task` / `model` values
so you can scope a monitor to a real segment. Then pick a trace id and call
`get_agent_trace` to see the full span tree. Look for:

- **Excessive tool calls** — an agent calling the same tool many times
- **Missing steps** — expected spans that don't appear
- **Error cascades** — a failed span causing downstream failures
- **Unusual paths** — the agent taking an unexpected execution route

You are identifying **what** to monitor — you don't need exact percentiles up
front; anomaly-detection operators (`AUTO`) learn the baseline themselves.

### 2c. Summarize the agent before proposing

Condense the investigation into a short agent understanding and show it to the
user — every monitor you propose should trace back to an item in it:

- **Purpose** — 1–2 sentences on what this agent does, grounded in the sampled
  transcripts (e.g. "a revenue-analytics assistant that answers questions about
  bookings").
- **Conversational?** — multi-turn user conversations (eval-worthy for
  satisfaction / task completion) vs. a batch / single-shot pipeline where
  structural and span checks fit better.
- **Tools and the dominant span** — which tool spans the agent runs, and which
  one does its core work (the SQL execution tool for an analytics agent,
  retrieval for a RAG agent).
- **Healthy trajectory shape** — how many times the dominant span runs per answer
  in healthy traces (the per-trace distribution and its max), typical turn counts,
  and latency/token magnitudes. This is the basis for every derived threshold.
- **Recurring intents** — what users repeatedly ask (from the transcripts) —
  seeds for custom conversation evals.
- **Observed failure modes** — what actually went wrong in the sample — seeds for
  evals and structural monitors.
- **Existing monitors** — from `get_monitors`, so proposals don't duplicate
  coverage.

---

## The `agent` reference

All four `create_or_update_agent_*_monitor` tools author the monitor's source from
a single top-level **`agent`** argument (there is no `dw_id` and no `data_source`
argument — the `agent` reference is the whole source). Two accepted forms:

- **Platform agent reference** — `{database}:{schema}.{name}` (Snowflake Cortex /
  Databricks agents), e.g. `analytics:agents.support_bot`.
- **OpenTelemetry `service_name`** — for OTel-instrumented agents, e.g. `checkout-agent`.

Get the exact value from `get_agent_metadata`'s **`agentReference`** field and pass
it verbatim — never construct, modify, or truncate it, and never pass an MCON. Two
optional companions:

- `trace_table` — only for non-ClickHouse OTel agents whose trace storage cannot be
  inferred from the agent reference.
- The per-type reference tells you whether `warehouse` is required (see below).

---

## Warehouse

`warehouse` names the warehouse the agent's trace data lives in — pass it as a name
or UUID. Use the agent entry's `warehouse_uuid` from `get_agent_metadata` (and its
`warehouse_name` when talking to the user); when both are null, use `get_warehouses`.
Whether `warehouse` is required or optional depends on the monitor type — see the
per-type reference.

---

## Agent span filters

The optional `agent_span_filters` parameter refines which spans are monitored. It
accepts **at most one** filter object. Each field of the object holds a
`{"value": "..."}` sub-object.

| Filter field | Description | Example |
|-------------|-------------|---------|
| `agent` | Filter by agent name | `{"agent": {"value": "My Agent"}}` |
| `workflow` | Filter by workflow name | `{"workflow": {"value": "Chat Agent"}}` |
| `task` | Filter by task name | `{"task": {"value": "call_model"}}` |
| `spanName` | Filter by span name | `{"spanName": {"value": "ChatBedrockConverse.chat"}}` |

Multiple fields can be combined in the single filter object:

```json
[{"workflow": {"value": "Chat Agent"}, "task": {"value": "call_model"}}]
```

`agent_span_filters` is a refinement and is optional — the `agent` reference already
scopes the monitor. Some monitor types restrict which fields are allowed here (e.g.
trajectory monitors, and trace-aggregated metric / validation monitors) — see the
per-type reference for the exact rule.

---

## Schedule configuration

Schedule is set via two top-level args, not a nested object:

- `schedule_type` — defaults to `fixed`. Valid values: `fixed`, `manual`.
- `interval_minutes` — defaults to `60`. The floor and alignment differ per monitor
  type — see each reference.

No agent monitor accepts a dynamic schedule — use `fixed` or `manual`. Use shorter
intervals for critical agents, longer for less critical ones.

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

### Behavior monitors — two trajectory proposals for (almost) every agent

Grounded in the Step 2c summary, propose these two patterns whenever they apply
(`agent-trajectory-monitor.md` has the full playbooks and payload shapes):

1. **Runaway loop — create live.** SPAN_OCCURRENCE on the agent's dominant tool
   span, threshold derived from the observed per-trace occurrence distribution:
   max observed + headroom, never a stock number. The proposal's evidence must
   show the dominant span, the distribution, and the derived threshold with its
   headroom rationale — plus a pre-create breach `preview` (dry run) proving zero
   historical matches; if the preview breaches, the sample missed the heavy tail
   (e.g. multi-turn accumulation in one trace) — re-derive from a wider window.
   Zero historical matches is the point — it is a regression guardrail that stays
   silent until the agent's behavior regresses.
2. **Ungrounded-in-data — create as a DRAFT** (only for agents that answer
   questions from data). Negated `occurs_with` SPAN_RELATION: an answer was
   produced without the agent's data-access tool span. Show a breach `preview`
   (dry run) as evidence, then create with `is_draft=True` — generic questions
   legitimately skip the data tool, and the LLM-judge filter needed to separate
   them from real data questions cannot be combined with a trajectory condition
   yet.

Tag both with the agent's name (`tags=[{"name": "agent", "value": "<AGENT_NAME>"}]`)
and schedule them daily (`interval_minutes=1440`).

Beyond these two, propose **agent-tailored behavioral custom prompts** for
behaviors a span pattern can't see — e.g. "did the agent claim it ran a query it
never executed?", "did the agent re-ask for information the user already gave?".
One boolean `custom_prompt` per behavior, alerting on `TRUE_RATE` / `FALSE_RATE`,
at conversation grain where the backend supports it (see `backend_class` in
Step 1 and `agent-evaluation-monitor.md`).

---

## Step 4: Create the monitor

All four tools follow the same **two-call preview-then-confirm pattern** as the data
monitor tools: the first call (`dry_run=True`, the default) returns the rendered MaC
YAML for review; the second call (`dry_run=False`) deploys the monitor live and
returns its UUID. Pass `monitor_uuid` on either call to update an existing agent
monitor in place instead of creating a new one (PUT semantics — re-pass every field
you want to keep, since omitted fields revert to defaults).

1. **Always start with `dry_run=True`** (the default). Show the user the
   configuration preview (the rendered YAML).
2. Call `get_audiences` to list available notification audiences. Suggest the
   most relevant one(s) and ask the user to pick — they can choose one or several.
   Pass audience **names** (not UUIDs) as the `audiences` list.
3. After showing the preview, offer to create or adjust settings.
4. Only set `dry_run=False` when the user explicitly confirms creation.

---

## Field name reference

See `agent-span-fields.md` for the complete list of known span field names
available in agent monitors. Do not guess field names — use only the ones
documented there.
