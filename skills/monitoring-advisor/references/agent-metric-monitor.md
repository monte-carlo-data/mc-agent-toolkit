# Agent Metric Monitor

## When to use

Track quantitative span-level metrics over time. Best for:

- **Latency monitoring** — `duration_sec` trending up
- **Token usage tracking** — `total_tokens`, `prompt_tokens`, `completion_tokens` per call
- **Volume monitoring** — number of spans per time window

## Constraints

> **CRITICAL:** The monitor's source is authored via the `agent` reference, NOT a
> `dw_id` + `data_source`/MCON. Pass the `agentReference` value from `get_agent_metadata`
> — a platform `{database}:{schema}.{name}` reference or an OTel `service_name`. Do NOT
> pass an MCON as `agent`.

> **IMPORTANT:** `schedule_type` defaults to `fixed` (lowercase) and `interval_minutes`
> defaults to `60`. Valid `schedule_type` values: `fixed`, `dynamic`, `manual`.

> **IMPORTANT:** `agent_span_filters` is an optional refinement — the `agent` reference
> already scopes the monitor. When you do filter, include at least the `agent` field.

> **IMPORTANT:** Use `duration_sec` (not `duration_ms`) for latency monitoring. The field
> is named `duration_sec` in the PARSED_SPANS layer — `duration_ms` does not exist.

> **IMPORTANT:** Use `total_tokens`, `prompt_tokens`, `completion_tokens` for token
> monitoring. These are the only token-related fields available.

> **IMPORTANT:** Use `ROW_COUNT_CHANGE` metric without the `fields` array for volume
> monitoring. Including `fields` with `ROW_COUNT_CHANGE` will cause an error.

## Key characteristics

- Uses `alert_conditions` with metric + operator (same as standard metric monitors)
- Supports AUTO (anomaly detection) and threshold operators (GT, LT, EQ, GTE, LTE, NEQ)
- Optional `is_agent_trace_aggregation=True` to aggregate per trace instead of per span
- Optional `sensitivity` to tune anomaly detection for AUTO operators
- Does NOT support transforms or sampling — raw numeric fields only

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `description` | string | Yes | Human-readable monitor description (shown as display name) |
| `agent` | string | Yes | Agent reference — `agentReference` from `get_agent_metadata` (`{db}:{schema}.{name}` or OTel `service_name`) |
| `alert_conditions` | array | Yes | List of alert condition objects (see below) |
| `warehouse` | string | No | Warehouse name or UUID — only when the agent reference doesn't pin it down |
| `trace_table` | string | No | Explicit trace table — only for non-ClickHouse OTel agents |
| `agent_span_filters` | array | No | Optional span-scope refinement (`agent`, `workflow`, `task`, `spanName`) |
| `is_agent_trace_aggregation` | boolean | No | Aggregate per trace instead of per span |
| `aggregate_by` | string | No | Time-window bucketing (`hour`/`day`/`week`/`month`) |
| `sensitivity` | string | No | Anomaly detection sensitivity for AUTO operators |
| `schedule_type` | string | No | Defaults to `fixed`. `fixed`/`dynamic`/`manual` |
| `interval_minutes` | int | No | Defaults to `60` for `fixed` |
| `monitor_uuid` | string | No | UUID of an existing monitor to update in place (PUT semantics) |
| `dry_run` | boolean | No | Default `True` — preview YAML; set `False` to deploy |

## Alert condition format

```json
{
    "metric": "NUMERIC_MEAN",
    "operator": "AUTO",
    "fields": ["duration_sec"]
}
```

Available metrics: `NUMERIC_MEAN`, `NUMERIC_MIN`, `NUMERIC_MAX`, `ROW_COUNT_CHANGE`

Available operators:
- `AUTO` — anomaly detection (recommended for most cases)
- `GT`, `LT`, `EQ`, `GTE`, `LTE`, `NEQ` — threshold-based (requires `thresholdValue`)

**Important:** For `ROW_COUNT_CHANGE`, do NOT include the `fields` array — it operates on row counts, not specific fields.

## Examples

The `agent` value below comes from `get_agent_metadata`'s `agentReference` field. The
first example uses a platform `{database}:{schema}.{name}` reference; the others use an
OTel `service_name`. Use whichever form `get_agent_metadata` returns for your agent.

### Latency monitoring (platform agent reference)

```
create_or_update_agent_metric_monitor(
    description="Chat Agent latency monitor",
    agent="analytics:agents.support_bot",
    alert_conditions=[
        {"metric": "NUMERIC_MEAN", "operator": "AUTO", "fields": ["duration_sec"]}
    ],
    agent_span_filters=[
        {"agent": {"value": "My Agent"}, "workflow": {"value": "Chat Agent"}}
    ],
    dry_run=True
)
```

### Token usage monitoring (OTel service_name)

```
create_or_update_agent_metric_monitor(
    description="Chat Agent token usage monitor",
    agent="checkout-agent",
    alert_conditions=[
        {"metric": "NUMERIC_MEAN", "operator": "GT", "fields": ["total_tokens"],
         "thresholdValue": 5000}
    ],
    agent_span_filters=[
        {"agent": {"value": "My Agent"}, "workflow": {"value": "Chat Agent"}}
    ],
    dry_run=True
)
```

### Volume monitoring (ROW_COUNT_CHANGE — no fields array)

```
create_or_update_agent_metric_monitor(
    description="Chat Agent span volume monitor",
    agent="checkout-agent",
    alert_conditions=[
        {"metric": "ROW_COUNT_CHANGE", "operator": "AUTO"}
    ],
    agent_span_filters=[
        {"agent": {"value": "My Agent"}, "workflow": {"value": "Chat Agent"}}
    ],
    dry_run=True
)
```

### Trace-level latency (aggregated per trace)

```
create_or_update_agent_metric_monitor(
    description="Chat Agent end-to-end trace latency",
    agent="checkout-agent",
    alert_conditions=[
        {"metric": "NUMERIC_MEAN", "operator": "AUTO", "fields": ["duration_sec"]}
    ],
    is_agent_trace_aggregation=True,
    dry_run=True
)
```

## Common errors

| Error message | Cause | Fix |
|--------------|-------|-----|
| invalid / unresolvable `agent` reference | The `agent` value wasn't taken from `get_agent_metadata` | Use the exact `agentReference` value from `get_agent_metadata` — do not construct it by hand |
| "Field X doesn't exist" | Field name not in the PARSED_SPANS schema | Check `agent-span-fields.md` for valid field names; use `duration_sec` not `duration_ms` |
