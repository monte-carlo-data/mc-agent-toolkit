# Agent Metric Monitor

## When to use

Track quantitative span-level metrics over time. Best for:

- **Latency monitoring** — `duration_sec` trending up
- **Token usage tracking** — `total_tokens`, `prompt_tokens`, `completion_tokens` per call
- **Volume monitoring** — number of spans per time window

## Key characteristics

- Uses `alert_conditions` with metric + operator (same as standard metric monitors)
- Supports AUTO (anomaly detection) and threshold operators (GT, LT, EQ, GTE, LTE, NE)
- Optional `is_agent_trace_aggregation=True` to aggregate per trace instead of per span
- Does NOT support transforms or sampling — raw numeric fields only

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `dw_id` | string | Yes | Warehouse UUID |
| `description` | string | Yes | Human-readable monitor description |
| `data_source` | object | Yes | `{"type": "TABLE", "mcon": "<trace_table_mcon>"}` |
| `alert_conditions` | array | Yes | List of alert condition objects (see below) |
| `schedule_config` | object | Yes | `{"scheduleType": "FIXED", "intervalMinutes": 60}` |
| `agent_span_filters` | array | Yes | Span filters — always include at least `agent` |
| `is_agent_trace_aggregation` | boolean | No | Aggregate per trace instead of per span |
| `dry_run` | boolean | No | Default `True` — preview without creating |

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
- `GT`, `LT`, `EQ`, `GTE`, `LTE`, `NE` — threshold-based (requires `thresholdValue`)

**Important:** For `ROW_COUNT_CHANGE`, do NOT include the `fields` array — it operates on row counts, not specific fields.

## Examples

### Latency monitoring

```
create_agent_metric_monitor(
    dw_id="<warehouse_uuid>",
    description="Chat Agent latency monitor",
    data_source={"type": "TABLE", "mcon": "<trace_table_mcon>"},
    alert_conditions=[
        {"metric": "NUMERIC_MEAN", "operator": "AUTO", "fields": ["duration_sec"]}
    ],
    schedule_config={"scheduleType": "FIXED", "intervalMinutes": 60},
    agent_span_filters=[
        {"agent": {"value": "My Agent"}, "workflow": {"value": "Chat Agent"}}
    ],
    dry_run=True
)
```

### Token usage monitoring

```
create_agent_metric_monitor(
    dw_id="<warehouse_uuid>",
    description="Chat Agent token usage monitor",
    data_source={"type": "TABLE", "mcon": "<trace_table_mcon>"},
    alert_conditions=[
        {"metric": "NUMERIC_MEAN", "operator": "GT", "fields": ["total_tokens"],
         "thresholdValue": 5000}
    ],
    schedule_config={"scheduleType": "FIXED", "intervalMinutes": 60},
    agent_span_filters=[
        {"agent": {"value": "My Agent"}, "workflow": {"value": "Chat Agent"}}
    ],
    dry_run=True
)
```

### Volume monitoring (ROW_COUNT_CHANGE — no fields array)

```
create_agent_metric_monitor(
    dw_id="<warehouse_uuid>",
    description="Chat Agent span volume monitor",
    data_source={"type": "TABLE", "mcon": "<trace_table_mcon>"},
    alert_conditions=[
        {"metric": "ROW_COUNT_CHANGE", "operator": "AUTO"}
    ],
    schedule_config={"scheduleType": "FIXED", "intervalMinutes": 60},
    agent_span_filters=[
        {"agent": {"value": "My Agent"}, "workflow": {"value": "Chat Agent"}}
    ],
    dry_run=True
)
```

### Trace-level latency (aggregated per trace)

```
create_agent_metric_monitor(
    dw_id="<warehouse_uuid>",
    description="Chat Agent end-to-end trace latency",
    data_source={"type": "TABLE", "mcon": "<trace_table_mcon>"},
    alert_conditions=[
        {"metric": "NUMERIC_MEAN", "operator": "AUTO", "fields": ["duration_sec"]}
    ],
    schedule_config={"scheduleType": "FIXED", "intervalMinutes": 60},
    agent_span_filters=[
        {"agent": {"value": "My Agent"}}
    ],
    is_agent_trace_aggregation=True,
    dry_run=True
)
```
