# Agent Metric Monitor

## When to use

Track quantitative span-level metrics over time. Best for:

- **Latency monitoring** — `duration_sec` trending up
- **Token usage tracking** — `total_tokens`, `prompt_tokens`, `completion_tokens` per call
- **Volume monitoring** — number of spans per time window (`ROW_COUNT_CHANGE`)
- **Boolean rates** — e.g. tool-call rate via `is_tool_call`
- **Anomaly detection** on any of the above with automatic thresholds

Do NOT use this for LLM-evaluated quality (relevance, correctness, tone) — that's
`create_or_update_agent_evaluation_monitor`, which adds sampling + transforms.

## Constraints

> **CRITICAL:** The monitor's source is the `agent` reference. Pass the
> `agentReference` value from `get_agent_metadata` verbatim — a platform
> `{database}:{schema}.{name}` reference or an OTel `service_name`. Never modify,
> truncate, or reconstruct it, and never pass an MCON.

> **CRITICAL:** `warehouse` is REQUIRED. Pass the agent's `warehouse_uuid` from
> `get_agent_metadata`; use `get_warehouses` when it is null or to resolve by name.

> **IMPORTANT:** `schedule_type` is `fixed` (default) or `manual` — never dynamic.
> `interval_minutes` defaults to `60` and must be at least 60 **and** a multiple of 60.

> **IMPORTANT:** Use `duration_sec` (not `duration_ms`) for latency. The field is
> named `duration_sec` in the PARSED_SPANS layer — `duration_ms` does not exist.

> **IMPORTANT:** `ROW_COUNT_CHANGE` is table-level — do NOT include a `fields` array,
> and use only an anomaly operator (`AUTO`/`AUTO_HIGH`/`AUTO_LOW`) or `NOOP`. A manual
> comparison operator has no field to bind to and is rejected.

> **IMPORTANT:** Match the metric to the field type — numeric metrics need numeric
> fields, boolean metrics need boolean fields. A numeric metric on a non-numeric
> field is rejected at dry-run.

## Key characteristics

- Uses `alert_conditions` with metric + operator (no transforms, no sampling)
- Supports anomaly (`AUTO`) and threshold operators
- Optional `is_agent_trace_aggregation=True` aggregates per trace instead of per span
  (OTel agents only — see Trace aggregation)
- Optional `sensitivity` (`low`/`medium`/`high`) tunes AUTO operators

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `description` | string | Yes | Human-readable monitor description (shown as display name) |
| `agent` | string | Yes | Agent reference — `agentReference` from `get_agent_metadata` (`{db}:{schema}.{name}` or OTel `service_name`) |
| `warehouse` | string | Yes | Warehouse name or UUID holding the agent's traces |
| `alert_conditions` | array | Yes | List of alert condition objects (see below) |
| `trace_table` | string | No | Explicit trace table — only for non-ClickHouse OTel agents |
| `agent_span_filters` | array | No | Optional span-scope refinement; at most ONE filter object |
| `is_agent_trace_aggregation` | boolean | No | Aggregate per trace instead of per span (OTel only) |
| `aggregate_by` | string | No | Time-window bucketing (`hour`/`day`/`week`/`month`) |
| `sensitivity` | string | No | Anomaly detection sensitivity for AUTO operators |
| `schedule_type` | string | No | `fixed` (default) or `manual` |
| `interval_minutes` | int | No | Default `60`; at least 60 and a multiple of 60 |
| `monitor_uuid` | string | No | UUID of an existing monitor to update in place (PUT semantics) |
| `dry_run` | boolean | No | Default `True` — preview YAML; set `False` to deploy |

## Alert conditions

Each condition has:

| Field | Required | Description |
|-------|----------|-------------|
| `metric` | Yes | The metric to compute (see Metrics below). |
| `operator` | Yes | See Operators below. |
| `fields` | Depends | PARSED_SPANS field name(s). Required for every manual operator and range. Omit for `ROW_COUNT_CHANGE`. |
| `thresholdValue` | Depends | Required for single-value operators (`GT`/`GTE`/`LT`/`LTE`/`EQ`/`NEQ`). camelCase — NOT `threshold_value`. |
| `lowerThreshold` / `upperThreshold` | Depends | Both required for `INSIDE_RANGE` / `OUTSIDE_RANGE`; `lowerThreshold` ≤ `upperThreshold`. |
| `type` | No | `threshold` (default) or `noop` (collect without alerting; pair with `operator: "NOOP"`). |

### Operators

- **Anomaly detection:** `AUTO`, `AUTO_HIGH`, `AUTO_LOW` — learn thresholds
  automatically. Do NOT pass any threshold.
- **Single threshold:** `GT`, `GTE`, `LT`, `LTE`, `EQ`, `NEQ` — require
  `thresholdValue` **and** `fields`. (The not-equal operator is `NEQ`, not `NE`.)
- **Range:** `INSIDE_RANGE`, `OUTSIDE_RANGE` — require both `lowerThreshold` and
  `upperThreshold` (and `fields`).
- **Collect-only:** `NOOP` — record the metric without alerting; pair with
  `type: "noop"`.

### Metrics

**Table-level metric (no `fields`; anomaly / NOOP operators only):**

| Metric | Notes |
|--------|-------|
| `ROW_COUNT_CHANGE` | Anomalous span volume. `AUTO` / `AUTO_HIGH` / `AUTO_LOW` (or `NOOP`) only; no `fields`. |

**Field-level metrics (must specify `fields`), by field type:**

| Metric | Field type |
|--------|-----------|
| `NUMERIC_MEAN`, `NUMERIC_MEDIAN`, `NUMERIC_MIN`, `NUMERIC_MAX`, `NUMERIC_STDDEV`, `SUM` | numeric |
| `PERCENTILE_20`, `PERCENTILE_40`, `PERCENTILE_60`, `PERCENTILE_80`, `PERCENTILE_95`, `PERCENTILE_99` | numeric |
| `ZERO_RATE`, `ZERO_COUNT`, `NEGATIVE_RATE`, `NEGATIVE_COUNT` | numeric |
| `TRUE_RATE`, `TRUE_COUNT`, `FALSE_RATE`, `FALSE_COUNT` | boolean |
| `NULL_RATE`, `NULL_COUNT`, `NON_NULL_COUNT` | any |
| `UNIQUE_COUNT` | numeric / text / date |

Numeric metrics apply to `duration_sec` / `*_tokens` / `status_code`; boolean metrics
apply to `is_tool_call` / `is_llm_call` / `has_prompts` / `has_completions` (the last
three are OTel/ClickHouse only — platform/Cortex agents lack them); `NULL_RATE`
applies to any field. Duplicate `(metric, field)` pairs across conditions
are rejected.

Common numeric fields: `duration_sec`, `total_tokens`, `prompt_tokens`,
`completion_tokens`, `status_code` (span grain); `span_count`, `llm_call_count`,
token totals, `duration_sec` (trace grain). Do NOT use `duration_ms` or raw table
column names.

## Trace aggregation

`is_agent_trace_aggregation=True` rolls spans up per trace. Constraints:

- **OTel agents only.** Platform agent references (`{database}:{schema}.{name}`) are
  rejected — the per-trace query isn't built for them. Target an OTel `service_name`,
  or pass an explicit `trace_table`.
- **Only the `agent` span filter is allowed** — remove `workflow` / `task` /
  `spanName` from `agent_span_filters`, since the per-trace result has no such column.
- Use the trace-aggregation field names (`span_count`, `llm_call_count`, trace-summed
  tokens, total `duration_sec`). See `agent-span-fields.md`.

## Examples

The `agent` value below comes from `get_agent_metadata`'s `agentReference` field —
a platform `{database}:{schema}.{name}` reference or an OTel `service_name`.

### Latency anomaly detection (platform agent reference)

```
create_or_update_agent_metric_monitor(
    description="Chat Agent latency monitor",
    agent="analytics:agents.support_bot",
    warehouse="Prod Warehouse",
    alert_conditions=[
        {"metric": "NUMERIC_MEAN", "operator": "AUTO", "fields": ["duration_sec"]}
    ],
    dry_run=True
)
```

### Span volume anomaly detection (OTel service_name, ROW_COUNT_CHANGE — no fields)

```
create_or_update_agent_metric_monitor(
    description="Chat Agent span volume monitor",
    agent="checkout-agent",
    warehouse="Prod Warehouse",
    alert_conditions=[
        {"metric": "ROW_COUNT_CHANGE", "operator": "AUTO"}
    ],
    agent_span_filters=[
        {"workflow": {"value": "Chat Agent"}}
    ],
    dry_run=True
)
```

### Token usage with threshold (span grain)

```
create_or_update_agent_metric_monitor(
    description="Alert when mean token usage exceeds 5000",
    agent="analytics:agents.support_bot",
    warehouse="Prod Warehouse",
    alert_conditions=[
        {"metric": "NUMERIC_MEAN", "operator": "GT", "fields": ["total_tokens"],
         "thresholdValue": 5000}
    ],
    dry_run=True
)
```

### Trace-level token rollup (OTel agent, trace aggregation)

```
create_or_update_agent_metric_monitor(
    description="Alert on anomalous per-trace token totals",
    agent="checkout-agent",
    warehouse="Prod Warehouse",
    alert_conditions=[
        {"metric": "NUMERIC_MEAN", "operator": "AUTO", "fields": ["total_tokens"]}
    ],
    is_agent_trace_aggregation=True,
    dry_run=True
)
```

### Tool-call rate (OTel agent, boolean field)

```
create_or_update_agent_metric_monitor(
    description="Alert when tool-call rate drops",
    agent="checkout-agent",
    warehouse="Prod Warehouse",
    alert_conditions=[
        {"metric": "TRUE_RATE", "operator": "LT", "fields": ["is_tool_call"],
         "thresholdValue": 0.1}
    ],
    dry_run=True
)
```

## Common errors

| Error message | Cause | Fix |
|--------------|-------|-----|
| Warehouse not found | `warehouse` omitted or wrong | Pass the agent's `warehouse_uuid` from `get_agent_metadata`; if null, list warehouses via `get_warehouses` |
| invalid / unresolvable `agent` reference | The `agent` value wasn't taken from `get_agent_metadata` | Use the exact `agentReference` value — do not construct it by hand, and never pass an MCON |
| "Field X doesn't exist" | Field name not in the PARSED_SPANS schema | Check `agent-span-fields.md`; use `duration_sec` not `duration_ms` |
| metric/field-type mismatch | Numeric metric on a boolean field (or vice versa) | Numeric metrics on numeric fields, boolean metrics on boolean fields, `NULL_RATE` on any |
| `ROW_COUNT_CHANGE` rejected | Included `fields`, or used a manual operator | Drop `fields`; use `AUTO`/`AUTO_HIGH`/`AUTO_LOW` or `NOOP` |
