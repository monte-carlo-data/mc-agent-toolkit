# Agent Validation Monitor

## When to use

Assert logical conditions on aggregated agent span data. Best for:

- **Business rule assertions** — "total_tokens must be below threshold"
- **Data quality checks on span attributes** — verify expected field values
- **Compliance checks** — e.g., "PII detection must run on every trace"
- **Custom predicate validations** on agent behavior

## Constraints

> **CRITICAL:** Agent monitors can ONLY be created on the `traceTableMcon` returned by
> `get_agent_metadata`. You cannot use any other table or MCON — the API will reject it
> with "table must be validated".

> **CRITICAL:** Always use the exact `traceTableMcon` from `get_agent_metadata` as the
> `data_source.mcon` — NEVER modify, truncate, or reconstruct it.

> **IMPORTANT:** Always use `FIXED` (uppercase) for `scheduleType` in schedule configs.
> All schedule type values must be uppercase. Using lowercase causes
> "Expected type ScheduleType" errors.

> **IMPORTANT:** Always use `ingest_ts` as the `timeField`. The time filter must be
> `{"timeField": {"field": "ingest_ts"}, "lookbackInHrs": <hours>}`. Using any other
> time field will fail.

> **IMPORTANT:** Agent span filters always need at least the `agent` field set.

## Key characteristics

- Uses `alert_condition` as a `FilterGroup` with `left`/`right` typed values
- Requires `time_filter` and `agent_span_filters`
- Optional `is_agent_trace_aggregation` for trace-level assertions
- Returns a `CustomRule`

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `dw_id` | string | Yes | Warehouse UUID |
| `description` | string | Yes | Human-readable monitor description |
| `data_source` | object | Yes | `{"type": "TABLE", "mcon": "<trace_table_mcon>"}` |
| `alert_condition` | object | Yes | FilterGroup with conditions (see below) |
| `time_filter` | object | Yes | `{"timeField": {"field": "ingest_ts"}, "lookbackInHrs": 24}` |
| `schedule_config` | object | Yes | `{"scheduleType": "FIXED", "intervalMinutes": 60}` |
| `agent_span_filters` | array | Yes | Span filters — always include at least `agent` |
| `is_agent_trace_aggregation` | boolean | No | Aggregate per trace for trace-level assertions |
| `dry_run` | boolean | No | Default `True` — preview without creating |

## alert_condition format

```json
{
    "operator": "AND",
    "conditions": [
        {
            "type": "BINARY",
            "predicate": {"name": "greater_than"},
            "left": [{"field": "total_tokens", "type": "FIELD"}],
            "right": [{"literal": "1000", "type": "LITERAL"}]
        }
    ]
}
```

### Field reference

- `type`: `SQL`, `BINARY`, `UNARY`, `GROUP`
- `predicate.name`: `equal`, `not_equal`, `greater_than`, `less_than`, `greater_than_or_equal`, `less_than_or_equal`, `null`, `not_null`
- `left`/`right` entries: `{"field": "<name>", "type": "FIELD"}` or `{"literal": "<value>", "type": "LITERAL"}`
- `operator` (for group-level): `AND`, `OR`

## Examples

### Assert token usage below threshold

```
create_agent_validation(
    dw_id="<warehouse_uuid>",
    description="Assert token usage below threshold",
    data_source={"type": "TABLE", "mcon": "<trace_table_mcon>"},
    alert_condition={
        "operator": "AND",
        "conditions": [
            {
                "type": "BINARY",
                "predicate": {"name": "greater_than"},
                "left": [{"field": "total_tokens", "type": "FIELD"}],
                "right": [{"literal": "10000", "type": "LITERAL"}]
            }
        ]
    },
    time_filter={"timeField": {"field": "ingest_ts"}, "lookbackInHrs": 24},
    schedule_config={"scheduleType": "FIXED", "intervalMinutes": 60},
    agent_span_filters=[
        {"agent": {"value": "My Agent"}, "workflow": {"value": "Chat Agent"}}
    ],
    dry_run=True
)
```

### Assert latency stays reasonable (trace-level)

```
create_agent_validation(
    dw_id="<warehouse_uuid>",
    description="Assert trace duration under 120 seconds",
    data_source={"type": "TABLE", "mcon": "<trace_table_mcon>"},
    alert_condition={
        "operator": "AND",
        "conditions": [
            {
                "type": "BINARY",
                "predicate": {"name": "greater_than"},
                "left": [{"field": "duration_sec", "type": "FIELD"}],
                "right": [{"literal": "120", "type": "LITERAL"}]
            }
        ]
    },
    time_filter={"timeField": {"field": "ingest_ts"}, "lookbackInHrs": 24},
    schedule_config={"scheduleType": "FIXED", "intervalMinutes": 60},
    agent_span_filters=[
        {"agent": {"value": "My Agent"}}
    ],
    is_agent_trace_aggregation=True,
    dry_run=True
)
```

### Compound condition — token usage AND latency

```
create_agent_validation(
    dw_id="<warehouse_uuid>",
    description="Assert token and latency within bounds",
    data_source={"type": "TABLE", "mcon": "<trace_table_mcon>"},
    alert_condition={
        "operator": "OR",
        "conditions": [
            {
                "type": "BINARY",
                "predicate": {"name": "greater_than"},
                "left": [{"field": "total_tokens", "type": "FIELD"}],
                "right": [{"literal": "10000", "type": "LITERAL"}]
            },
            {
                "type": "BINARY",
                "predicate": {"name": "greater_than"},
                "left": [{"field": "duration_sec", "type": "FIELD"}],
                "right": [{"literal": "60", "type": "LITERAL"}]
            }
        ]
    },
    time_filter={"timeField": {"field": "ingest_ts"}, "lookbackInHrs": 24},
    schedule_config={"scheduleType": "FIXED", "intervalMinutes": 1440},
    agent_span_filters=[
        {"agent": {"value": "My Agent"}, "workflow": {"value": "Chat Agent"}}
    ],
    dry_run=True
)
```

## Common errors

| Error message | Cause | Fix |
|--------------|-------|-----|
| "table must be validated" | MCON doesn't match a registered trace table | Verify the exact `traceTableMcon` from `get_agent_metadata` — use it as-is, do not modify |
| "Field X doesn't exist" | Field name not in the PARSED_SPANS schema | Check `agent-span-fields.md` for valid field names |
| "Expected type ScheduleType" | Schedule type is lowercase or invalid | Use `FIXED` (uppercase) — all schedule type values must be uppercase |
