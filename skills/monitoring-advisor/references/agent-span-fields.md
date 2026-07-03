# Known Span Field Names (PARSED_SPANS Layer)

> **CRITICAL:** Do NOT run `SHOW COLUMNS` or `SELECT *` on the trace table to discover
> field names — the raw table has different columns. Use the field names listed below.

Monte Carlo maintains a **PARSED_SPANS** transformation view on top of each
agent's raw trace table. This view extracts structured fields from the raw
OTLP JSON. **You cannot query PARSED_SPANS directly via SQL** — it is not
a real table. However, all agent monitors operate on these parsed fields,
so you MUST use these field names when creating monitors.

Do NOT run `SHOW COLUMNS` or `SELECT *` on the trace table to discover
field names for monitors — the raw table has different columns (e.g.,
`VALUE`, `FILENAME`, `INGEST_TS`, `DATE_PART`) that are NOT the fields
monitors use. Instead, use the field names listed below.

> **The read tools use different names and units for some fields.** The names below
> are the **monitor** field names. The tools you sample with do not all match them:
> `get_agent_traces` returns `duration_seconds` and `count_llm_calls` (the monitor
> fields are `duration_sec` and `llm_call_count`), and `get_agent_trace` reports
> `duration` in **milliseconds** (the monitor field `duration_sec` is in seconds).
> Always use the monitor field names below in monitor payloads — never copy a read
> tool's column name or unit into a monitor.

## Span-level fields (default, per-span rows)

| Field | Type | Description |
|-------|------|-------------|
| `agent` | STRING | Agent name |
| `trace_id` | STRING | Trace identifier |
| `span_id` | STRING | Span identifier |
| `parent_span_id` | STRING | Parent span identifier |
| `workflow` | STRING | Workflow name |
| `task` | STRING | Task name |
| `span_name` | STRING | Span operation name |
| `model_name` | STRING | Model used |
| `prompts` | ARRAY | LLM prompt messages (evaluation transforms) |
| `completions` | ARRAY | LLM completion messages (evaluation transforms) |
| `total_tokens` | INTEGER | Total token count (prompt + completion) |
| `prompt_tokens` | INTEGER | Input/prompt token count |
| `completion_tokens` | INTEGER | Output/completion token count |
| `duration_sec` | FLOAT | Span duration in seconds |
| `status_code` | INTEGER | Span status code (`2` = error) — numeric; compare with `"2"`, not `"ERROR"` |
| `is_tool_call` | BOOLEAN | Whether the span is a tool call |
| `is_llm_call` | BOOLEAN | Whether the span is an LLM call *(OTel/ClickHouse only)* |
| `has_prompts` | BOOLEAN | Whether the span has prompt messages *(OTel/ClickHouse only)* |
| `has_completions` | BOOLEAN | Whether the span has completion messages *(OTel/ClickHouse only)* |
| `start_time` | TIMESTAMP | Span start timestamp |
| `end_time` | TIMESTAMP | Span end timestamp |
| `ingest_ts` | TIMESTAMP | Ingestion timestamp (use for time filters) |

### Platform vs OpenTelemetry availability

Platform (Snowflake Cortex / Databricks native) agents expose the core numeric and
text fields — `duration_sec`, `total_tokens`, `prompt_tokens`, `completion_tokens`,
`status_code`, `is_tool_call` — but **not** `is_llm_call`, `has_prompts`, or
`has_completions`. Those presence/kind flags exist only for OTel/ClickHouse agents.
Stick to the core fields unless you know the agent is OTel-instrumented.

## Trace-aggregation fields (is_agent_trace_aggregation=True)

When `is_agent_trace_aggregation=True`, rows are aggregated per trace (OpenTelemetry
agents only):

| Field | Type | Description |
|-------|------|-------------|
| `agent` | STRING | Agent name |
| `trace_id` | STRING | Trace identifier |
| `span_count` | INT | Number of spans in the trace |
| `llm_call_count` | INT | Number of LLM calls in the trace |
| `prompt_tokens` | INTEGER | Total prompt tokens across the trace |
| `completion_tokens` | INTEGER | Total completion tokens across the trace |
| `total_tokens` | INTEGER | Total tokens across the trace |
| `duration_sec` | FLOAT | Total trace duration in seconds |
| `start_time` | TIMESTAMP | Earliest span start in the trace |
| `end_time` | TIMESTAMP | Latest span end in the trace |
| `ingest_ts` | TIMESTAMP | Ingestion timestamp |

## Conversation-aggregation fields (is_agent_conversation_aggregation=True)

Agent evaluation monitors can aggregate per conversation
(`is_agent_conversation_aggregation=True`, OpenTelemetry agents only). At this grain,
`alert_conditions.fields` may reference these raw conversation columns alongside any
judge output field:

| Field | Type | Description |
|-------|------|-------------|
| `turn_count` | INTEGER | Number of turns in the conversation |
| `duration_seconds` | FLOAT | Total conversation duration in seconds |
| `status` | STRING | Conversation status |

Plus the conversation-grain judge output fields (e.g. `relevance_score`,
`task_completion_score`) — see `agent-evaluation-monitor.md`.
