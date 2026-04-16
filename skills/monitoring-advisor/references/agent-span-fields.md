# Known Span Field Names (PARSED_SPANS Layer)

Monte Carlo maintains a **PARSED_SPANS** transformation view on top of each
agent's raw trace table. This view extracts structured fields from the raw
OTLP JSON. **You cannot query PARSED_SPANS directly via SQL** — it is not
a real table. However, all agent monitors operate on these parsed fields,
so you MUST use these field names when creating monitors.

Do NOT run `SHOW COLUMNS` or `SELECT *` on the trace table to discover
field names for monitors — the raw table has different columns (e.g.,
`VALUE`, `FILENAME`, `INGEST_TS`, `DATE_PART`) that are NOT the fields
monitors use. Instead, use the field names listed below.

## Span-level fields (default, per-span rows)

| Field | Type | Description |
|-------|------|-------------|
| `agent` | STRING | Agent name |
| `trace_id` | STRING | Trace identifier |
| `span_id` | STRING | Span identifier |
| `workflow` | STRING | Workflow name |
| `task` | STRING | Task name |
| `span_name` | STRING | Span operation name |
| `prompts` | ARRAY | LLM prompt messages |
| `completions` | ARRAY | LLM completion messages |
| `total_tokens` | INTEGER | Total token count (prompt + completion) |
| `prompt_tokens` | INTEGER | Input/prompt token count |
| `completion_tokens` | INTEGER | Output/completion token count |
| `start_time` | TIMESTAMP | Span start timestamp |
| `end_time` | TIMESTAMP | Span end timestamp |
| `duration_sec` | FLOAT | Span duration in seconds |
| `ingest_ts` | TIMESTAMP | Ingestion timestamp (use for time filters) |

## Trace-aggregation fields (is_agent_trace_aggregation=True)

When `is_agent_trace_aggregation=True`, rows are aggregated per trace:

| Field | Type | Description |
|-------|------|-------------|
| `agent` | STRING | Agent name |
| `trace_id` | STRING | Trace identifier |
| `span_count` | INT | Number of spans in the trace |
| `llm_call_count` | INT | Number of LLM calls in the trace |
| `prompt_tokens` | INTEGER | Total prompt tokens across the trace |
| `completion_tokens` | INTEGER | Total completion tokens across the trace |
| `total_tokens` | INTEGER | Total tokens across the trace |
| `start_time` | TIMESTAMP | Earliest span start in the trace |
| `end_time` | TIMESTAMP | Latest span end in the trace |
| `duration_sec` | FLOAT | Total trace duration in seconds |
| `ingest_ts` | TIMESTAMP | Ingestion timestamp |
