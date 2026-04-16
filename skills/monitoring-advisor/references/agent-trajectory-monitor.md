# Agent Trajectory Monitor

## When to use

Alert on specific execution patterns or span sequences. Best for:

- **Detecting excessive tool calls** — e.g., "search called more than 5 times"
- **Alerting on missing steps** — expected span didn't occur
- **Monitoring span relationships** — span A always followed by span B
- **Catching runaway loops** — unexpected execution paths

## Constraints

> **CRITICAL:** Agent monitors can ONLY be created on the `traceTableMcon` returned by
> `get_agent_metadata`. You cannot use any other table or MCON — the API will reject it
> with "table must be validated".

> **CRITICAL:** Always use the exact `traceTableMcon` from `get_agent_metadata` as the
> `data_source.mcon` — NEVER modify, truncate, or reconstruct it.

> **CRITICAL:** Trajectory `agent_span_filters`: only the `agent` field is allowed.
> Setting `workflow`, `task`, or `spanName` in `agent_span_filters` will cause a
> "workflow should not be set" validation error. Use `spanField` in the
> `agent_span_alert_condition` for workflow/task/spanName filtering instead.

> **IMPORTANT:** Always use `FIXED` (uppercase) for `scheduleType` in schedule configs.
> All schedule type values must be uppercase. Using lowercase causes
> "Expected type ScheduleType" errors.

> **IMPORTANT:** Always use `ingest_ts` as the `timeField`. The time filter must be
> `{"timeField": {"field": "ingest_ts"}, "lookbackInHrs": <hours>}`. Using any other
> time field will fail.

> **IMPORTANT:** Agent span filters always need at least the `agent` field set.

## Key characteristics

- Uses `agent_span_alert_condition` (not `alert_conditions`) — span-specific predicates
- Requires `time_filter` with `timeField` (object `{"field": "ingest_ts"}`) and `lookbackInHrs`
- Returns a `CustomRule` with YAML preview
- **`agent_span_filters` constraint:** Trajectory monitors can ONLY use the `agent` field in
  `agent_span_filters`. Setting `workflow`, `task`, or `spanName` in `agent_span_filters` will
  cause a validation error. Workflow/task/spanName filtering is done via the
  `spanField` in the `agent_span_alert_condition`, NOT via `agent_span_filters`.

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `dw_id` | string | Yes | Warehouse UUID |
| `description` | string | Yes | Human-readable monitor description |
| `data_source` | object | Yes | `{"type": "TABLE", "mcon": "<trace_table_mcon>"}` |
| `agent_span_alert_condition` | object | Yes | Span occurrence conditions (see below) |
| `time_filter` | object | Yes | `{"timeField": {"field": "ingest_ts"}, "lookbackInHrs": 24}` |
| `schedule_config` | object | Yes | `{"scheduleType": "FIXED", "intervalMinutes": 60}` |
| `agent_span_filters` | array | Yes | **Only `agent` field allowed** — no `workflow`, `task`, or `spanName` |
| `dry_run` | boolean | No | Default `True` — preview without creating |

## agent_span_alert_condition format

```json
{
    "operator": "AND",
    "conditions": [
        {
            "type": "SPAN_OCCURRENCE",
            "predicate": {"name": "occurs"},
            "spanField": {
                "spanName": {"literal": "ChatBedrockConverse.chat"},
                "task": {"literal": "call_model"},
                "workflow": {"literal": "Chat Agent"},
                "type": "SPAN_FIELD"
            },
            "count": 5,
            "comparisonOperator": "MORE_THAN"
        }
    ]
}
```

### Field reference

- `type`: Always `SPAN_OCCURRENCE`
- `predicate.name`: `occurs` or `occurs_with`
- `comparisonOperator`: `MORE_THAN`, `LESS_THAN`, `EXACTLY`
- `spanField.type`: Always `SPAN_FIELD`
- `spanField.spanName`, `spanField.task`, `spanField.workflow`: Each is `{"literal": "value"}`

**IMPORTANT:** When `spanName` is set in `spanField`, `task` and `workflow` MUST also be set.

## Examples

### Alert on excessive LLM calls

```
create_agent_trajectory(
    dw_id="<warehouse_uuid>",
    description="Alert on excessive LLM calls",
    data_source={"type": "TABLE", "mcon": "<trace_table_mcon>"},
    agent_span_alert_condition={
        "operator": "AND",
        "conditions": [
            {
                "type": "SPAN_OCCURRENCE",
                "predicate": {"name": "occurs"},
                "spanField": {
                    "spanName": {"literal": "ChatBedrockConverse.chat"},
                    "task": {"literal": "call_model"},
                    "workflow": {"literal": "Chat Agent"},
                    "type": "SPAN_FIELD"
                },
                "count": 5,
                "comparisonOperator": "MORE_THAN"
            }
        ]
    },
    time_filter={"timeField": {"field": "ingest_ts"}, "lookbackInHrs": 24},
    schedule_config={"scheduleType": "FIXED", "intervalMinutes": 60},
    agent_span_filters=[
        {"agent": {"value": "My Agent"}}
    ],
    dry_run=True
)
```

### Alert on missing expected step

```
create_agent_trajectory(
    dw_id="<warehouse_uuid>",
    description="Alert when validation step is missing",
    data_source={"type": "TABLE", "mcon": "<trace_table_mcon>"},
    agent_span_alert_condition={
        "operator": "AND",
        "conditions": [
            {
                "type": "SPAN_OCCURRENCE",
                "predicate": {"name": "occurs"},
                "spanField": {
                    "spanName": {"literal": "validate_output"},
                    "task": {"literal": "post_process"},
                    "workflow": {"literal": "Chat Agent"},
                    "type": "SPAN_FIELD"
                },
                "count": 0,
                "comparisonOperator": "EXACTLY"
            }
        ]
    },
    time_filter={"timeField": {"field": "ingest_ts"}, "lookbackInHrs": 24},
    schedule_config={"scheduleType": "FIXED", "intervalMinutes": 60},
    agent_span_filters=[
        {"agent": {"value": "My Agent"}}
    ],
    dry_run=True
)
```

## Common errors

| Error message | Cause | Fix |
|--------------|-------|-----|
| "table must be validated" | MCON doesn't match a registered trace table | Verify the exact `traceTableMcon` from `get_agent_metadata` — use it as-is, do not modify |
| "workflow should not be set" in agentSpanFilters | Trajectory monitors only allow the `agent` field in `agent_span_filters` | Remove `workflow`, `task`, and `spanName` from `agent_span_filters`; use `spanField` in the `agent_span_alert_condition` instead |
| "Expected type ScheduleType" | Schedule type is lowercase or invalid | Use `FIXED` (uppercase) — all schedule type values must be uppercase |
