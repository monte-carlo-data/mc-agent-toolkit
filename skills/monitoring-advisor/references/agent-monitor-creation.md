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

---

## Propose with the POBC framing (walk the user through all four pillars)

When the user is setting up monitoring for an agent (rather than asking for one
specific monitor), structure the proposal around the four pillars of agent
observability — **Performance, Output, Behavior, Context (POBC)** — and walk
through them one at a time. Do NOT dump every proposed monitor in one
monolithic list.

### 1. Open with the framing

Before presenting any monitors, briefly explain the framework. Use this copy,
adapting the agent's actual name into the prose where it reads naturally:

> A quick word on how we think about agent observability. Agents fail in four
> distinct ways, so we monitor four distinct things — **Performance, Output,
> Behavior, and Context (POBC)**: how efficiently the agent answers, what it
> says, how it gets there, and the data it stands on.
>
> **Performance** — is it fast and affordable? Latency, token cost, and error
> monitoring catch drift in both the typical experience and the worst one.
>
> **Output** — is the agent giving good answers? Evals score response quality
> (helpfulness, non-answers, user corrections) so quality regressions surface
> as alerts, not user complaints.
>
> **Behavior** — is it working sensibly under the hood? Trajectory monitoring
> flags runs that loop or take paths a healthy run never takes — including
> failures the agent recovers from and hides.
>
> **Context** — is the data it relies on healthy? The agent's answers are only
> as good as its upstream tables; we monitor those for freshness, schema
> changes, and anomalies.
>
> Everything below maps to one of these four. Here's the plan:

### 2. Walk through the plan pillar by pillar

Present the pillars in order — Performance, Output, Behavior, Context — one
short block each:

1. **Evidence** — one or two sentences of what you observed in Step 2 that
   motivates this pillar's monitors ("p95 latency is 40s with outliers over
   three minutes", "several conversations show repeated user corrections").
   If you found nothing notable for a pillar, say so and propose baseline
   coverage anyway — monitoring exists to catch what hasn't happened yet.
2. **Proposed monitors** — the specific monitors for this pillar, each with
   its monitor type, field or judge, and alert condition.
3. **Confirm** — ask whether to keep, adjust, or drop this pillar's monitors,
   and fold the answer in before moving to the next pillar.

A healthy agent usually warrants coverage in every pillar you can serve —
keep proposals broad across pillars, not deep in one.

**Global defaults for proposed monitors** (apply unless the user asks
otherwise):

- **Daily schedule** — pass `interval_minutes=1440` explicitly; the tools'
  built-in default is hourly (see Schedule configuration below).
- **Eval sampling** — `sampling_config={"count": 100}` (a fixed 100-sample
  budget per run), not a percentage, so evaluation cost stays predictable as
  traffic grows.
- **Audience before creation** — never create a monitor without asking which
  audience(s) should be notified (Step 4).

What each pillar maps to:

| Pillar | Monitor types | Reference |
|---|---|---|
| **Performance** | Metric (validation for hard limits) — latency (`duration_sec`), token cost (`total_tokens`), error rate (`status_code`), volume (`ROW_COUNT_CHANGE`) | `agent-metric-monitor.md` |
| **Output** | Evaluation — predefined judges (`answer_relevance`, `helpfulness`, `task_completion`, `clarity`, `prompt_adherence`), rule checks (`output_length`, `json_validity`), and one custom eval per recurring user intent or failure mode you observed | `agent-evaluation-monitor.md` |
| **Behavior** | Trajectory (validation for aggregate assertions) — runaway loops (`SPAN_OCCURRENCE`), missing or mis-ordered steps (`SPAN_RELATION`), token budgets | `agent-trajectory-monitor.md`, `agent-validation-monitor.md` |
| **Context** | Data-quality monitors on the agent's upstream tables — see below | — |

Mind the backend caveats from Step 1 (`backend_class`): no token or model
metrics for Genie / Knowledge Assistant agents, and conversation-grain evals
only on OTel/ClickHouse, Snowflake Cortex, and Genie. Aggregate (per-trace)
validation assertions require `is_agent_trace_aggregation=True`, supported
only on `ao_clickhouse_otel` / `customer_otel_trace_table` agents — on other
backends, use per-span assertions instead.

**Context is a recommendation for now** — creating data-quality monitors from
the agent's lineage is not wired into this flow yet. Present the pillar rather
than skipping it: name it in the plan, ask the user which upstream tables the
agent depends on, and suggest Monte Carlo's standard data-quality monitoring
(freshness, volume, schema changes, anomalies) on those tables as a follow-up
(the data-monitor workflow in this skill covers them).

### 3. Create the confirmed monitors

Once the user has confirmed the pillars, continue to Step 3 (pick each
monitor's reference doc) and Step 4 (dry-run preview, audience selection,
creation on explicit confirmation) for each approved monitor.

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

**Propose daily schedules by default** — pass `interval_minutes=1440` explicitly.
Schedule is set via two top-level args, not a nested object:

- `schedule_type` — defaults to `fixed`. Valid values: `fixed`, `manual`.
- `interval_minutes` — defaults to `60` (hourly), so omitting it creates an hourly
  monitor. The floor and alignment differ per monitor type — see each reference.

No agent monitor accepts a dynamic schedule — use `fixed` or `manual`. Daily is
the right cadence for most agents. If you judge an agent critical enough that a
same-hour alert would matter, suggest hourly to the user and let them decide —
the default stays daily unless they opt in.

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
| Set up performance coverage (latency, token cost, errors, SLO) | Agent Metric — Performance pillar | `agent-metric-monitor.md` |
| Score output quality with LLM evaluation | Agent Evaluation | `agent-evaluation-monitor.md` |
| Alert on execution patterns or span sequences | Agent Trajectory | `agent-trajectory-monitor.md` |
| Assert a logical rule on span data | Agent Validation | `agent-validation-monitor.md` |
| Monitor span volume over time | Agent Metric | `agent-metric-monitor.md` |
| Detect answer relevance drops | Agent Evaluation | `agent-evaluation-monitor.md` |
| Catch runaway tool call loops | Agent Trajectory | `agent-trajectory-monitor.md` |
| Ensure token count stays below threshold | Agent Validation | `agent-validation-monitor.md` |

After selecting the monitor type, **read the reference doc** for that type to
get the detailed parameter guide, examples, constraints, and creation workflow.
For a blanket "performance monitoring" ask, follow the **Performance pillar**
baseline set in `agent-metric-monitor.md` rather than assembling one-offs.

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
