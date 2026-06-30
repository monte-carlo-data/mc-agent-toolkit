# Agent Validation Monitor

## When to use

Assert logical conditions on aggregated agent span data. Best for:

- **Business rule assertions** — "total_tokens must be below threshold"
- **Data quality checks on span attributes** — verify expected field values
- **Compliance checks** — e.g., "PII detection must run on every trace"
- **Custom predicate validations** on agent behavior

## Constraints

> **CRITICAL:** The monitor's source is authored via the `agent` reference, NOT a
> `dw_id` + `data_source`/MCON. Pass the `agentReference` value from `get_agent_metadata`
> — a platform `{database}:{schema}.{name}` reference or an OTel `service_name`. Do NOT
> pass an MCON as `agent`.

> **IMPORTANT:** `schedule_type` defaults to `fixed` (lowercase) and `interval_minutes`
> defaults to `60`. Valid `schedule_type` values: `fixed`, `dynamic`, `manual`.

> **IMPORTANT:** Always use `ingest_ts` as the `timeField`. The time filter must be
> `{"timeField": {"field": "ingest_ts"}, "lookbackInHrs": <hours>}`. Using any other
> time field will fail. `time_filter` is REQUIRED.

> **IMPORTANT:** `agent_span_filters` is an optional refinement; when used, include at
> least the `agent` field.

## Key characteristics

- Uses `alert_condition` as a `FilterGroup` with `left`/`right` typed values
- Requires `time_filter`
- Optional `is_agent_trace_aggregation` for trace-level assertions
- Returns a `CustomRule`

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `description` | string | Yes | Human-readable monitor description (shown as display name) |
| `agent` | string | Yes | Agent reference — `agentReference` from `get_agent_metadata` (`{db}:{schema}.{name}` or OTel `service_name`) |
| `alert_condition` | object | Yes | FilterGroup with conditions (see below) |
| `time_filter` | object | Yes | `{"timeField": {"field": "ingest_ts"}, "lookbackInHrs": 24}` |
| `warehouse` | string | No | Warehouse name or UUID — only when the agent reference doesn't pin it down |
| `trace_table` | string | No | Explicit trace table — only for non-ClickHouse OTel agents |
| `agent_span_filters` | array | No | Optional span-scope refinement (`agent`, `workflow`, `task`, `spanName`) |
| `is_agent_trace_aggregation` | boolean | No | Aggregate per trace for trace-level assertions |
| `schedule_type` | string | No | Defaults to `fixed`. `fixed`/`dynamic`/`manual` |
| `interval_minutes` | int | No | Defaults to `60` for `fixed` |
| `monitor_uuid` | string | No | UUID of an existing monitor to update in place (PUT semantics) |
| `dry_run` | boolean | No | Default `True` — preview YAML; set `False` to deploy |

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

The `agent` value below comes from `get_agent_metadata`'s `agentReference` field. The
first example uses a platform `{database}:{schema}.{name}` reference; the others use an
OTel `service_name`. Use whichever form `get_agent_metadata` returns for your agent.

### Assert token usage below threshold (platform agent reference)

```
create_or_update_agent_validation_monitor(
    description="Assert token usage below threshold",
    agent="analytics:agents.support_bot",
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
    agent_span_filters=[
        {"agent": {"value": "My Agent"}, "workflow": {"value": "Chat Agent"}}
    ],
    dry_run=True
)
```

### Assert latency stays reasonable (trace-level, OTel service_name)

```
create_or_update_agent_validation_monitor(
    description="Assert trace duration under 120 seconds",
    agent="checkout-agent",
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
    is_agent_trace_aggregation=True,
    dry_run=True
)
```

### Compound condition — token usage AND latency

```
create_or_update_agent_validation_monitor(
    description="Assert token and latency within bounds",
    agent="checkout-agent",
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
    agent_span_filters=[
        {"agent": {"value": "My Agent"}, "workflow": {"value": "Chat Agent"}}
    ],
    schedule_type="fixed",
    interval_minutes=1440,
    dry_run=True
)
```

## Common errors

| Error message | Cause | Fix |
|--------------|-------|-----|
| invalid / unresolvable `agent` reference | The `agent` value wasn't taken from `get_agent_metadata` | Use the exact `agentReference` value from `get_agent_metadata` — do not construct it by hand |
| "Field X doesn't exist" | Field name not in the PARSED_SPANS schema | Check `agent-span-fields.md` for valid field names |
