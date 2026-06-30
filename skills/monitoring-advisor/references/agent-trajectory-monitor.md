# Agent Trajectory Monitor

## When to use

Alert on specific execution patterns or span sequences. Best for:

- **Detecting excessive tool calls** — e.g., "search called more than 5 times"
- **Alerting on missing steps** — expected span didn't occur
- **Monitoring span relationships** — span A always followed by span B
- **Catching runaway loops** — unexpected execution paths

## Constraints

> **CRITICAL:** The monitor's source is authored via the `agent` reference, NOT a
> `dw_id` + `data_source`/MCON. Pass the `agentReference` value from `get_agent_metadata`
> — a platform `{database}:{schema}.{name}` reference or an OTel `service_name`. Do NOT
> pass an MCON as `agent`.

> **CRITICAL:** Trajectory `agent_span_filters`: only the `agent` field is allowed.
> Setting `workflow`, `task`, or `spanName` in `agent_span_filters` will cause a
> "workflow should not be set" validation error. Use `spanField` in the
> `agent_span_alert_condition` for workflow/task/spanName filtering instead.

> **IMPORTANT:** `schedule_type` defaults to `fixed` (lowercase) and `interval_minutes`
> defaults to `60`. Valid `schedule_type` values: `fixed`, `dynamic`, `manual`.

> **IMPORTANT:** Always use `ingest_ts` as the `timeField`. The time filter must be
> `{"timeField": {"field": "ingest_ts"}, "lookbackInHrs": <hours>}`. Using any other
> time field will fail. `time_filter` is REQUIRED.

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
| `description` | string | Yes | Human-readable monitor description (shown as display name) |
| `agent` | string | Yes | Agent reference — `agentReference` from `get_agent_metadata` (`{db}:{schema}.{name}` or OTel `service_name`) |
| `agent_span_alert_condition` | object | Yes | Span occurrence conditions (see below) |
| `time_filter` | object | Yes | `{"timeField": {"field": "ingest_ts"}, "lookbackInHrs": 24}` |
| `warehouse` | string | No | Warehouse name or UUID — only when the agent reference doesn't pin it down |
| `trace_table` | string | No | Explicit trace table — only for non-ClickHouse OTel agents |
| `agent_span_filters` | array | No | Optional — **only the `agent` field allowed** (no `workflow`, `task`, or `spanName`) |
| `schedule_type` | string | No | Defaults to `fixed`. `fixed`/`dynamic`/`manual` |
| `interval_minutes` | int | No | Defaults to `60` for `fixed` |
| `monitor_uuid` | string | No | UUID of an existing monitor to update in place (PUT semantics) |
| `dry_run` | boolean | No | Default `True` — preview YAML; set `False` to deploy |

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

The `agent` value below comes from `get_agent_metadata`'s `agentReference` field — a
platform `{database}:{schema}.{name}` reference or an OTel `service_name`. Use whichever
form `get_agent_metadata` returns for your agent.

### Alert on excessive LLM calls (platform agent reference)

```
create_or_update_agent_trajectory_monitor(
    description="Alert on excessive LLM calls",
    agent="analytics:agents.support_bot",
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
    agent_span_filters=[
        {"agent": {"value": "My Agent"}}
    ],
    dry_run=True
)
```

### Alert on missing expected step (OTel service_name)

```
create_or_update_agent_trajectory_monitor(
    description="Alert when validation step is missing",
    agent="checkout-agent",
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
    agent_span_filters=[
        {"agent": {"value": "My Agent"}}
    ],
    dry_run=True
)
```

## Common errors

| Error message | Cause | Fix |
|--------------|-------|-----|
| invalid / unresolvable `agent` reference | The `agent` value wasn't taken from `get_agent_metadata` | Use the exact `agentReference` value from `get_agent_metadata` — do not construct it by hand |
| "workflow should not be set" in agentSpanFilters | Trajectory monitors only allow the `agent` field in `agent_span_filters` | Remove `workflow`, `task`, and `spanName` from `agent_span_filters`; use `spanField` in the `agent_span_alert_condition` instead |
