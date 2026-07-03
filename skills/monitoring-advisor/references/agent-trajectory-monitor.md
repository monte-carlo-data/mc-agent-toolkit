# Agent Trajectory Monitor

## When to use

Flag a whole trace by its execution pattern. Best for:

- **Detecting excessive tool/step calls** — e.g. "search called more than 5 times"
- **Detecting too-few calls** — e.g. "the retry step ran fewer than 2 times"
- **Catching runaway loops**
- **Broken execution order or a missing follow-up** — e.g. "generation runs before
  retrieval", "planning runs without validation"

Do NOT use it to assert a rule on a single span's field values (token ceilings,
non-null) — that's `create_or_update_agent_validation_monitor`. Do NOT use it to
trend a numeric metric (mean latency, token counts) — that's
`create_or_update_agent_metric_monitor`.

## Constraints

> **CRITICAL:** The monitor's source is the `agent` reference. Pass the
> `agentReference` value from `get_agent_metadata` verbatim — a platform
> `{database}:{schema}.{name}` reference or an OTel `service_name`. Never modify,
> truncate, or reconstruct it, and never pass an MCON.

> **CRITICAL:** Conditions are OR-combined — a trace is flagged if ANY condition
> matches. `operator` defaults to `OR`; **`operator: "AND"` is rejected.** To require
> several patterns to all hold, use separate monitors.

> **CRITICAL:** Trajectory `agent_span_filters` allow only the `agent` field — at
> most one filter, e.g. `agent_span_filters=[{"agent": {"value": "My Agent"}}]`.
> Setting `workflow`, `task`, or `spanName` there causes a validation error — those go
> in the condition's `spanField` instead. For OpenTelemetry agents the filter's
> `agent` value must equal the top-level `agent` reference.

> **CRITICAL:** A span that never appears produces no rows to count, so "occurs 0
> times" (a missing span) cannot be expressed with SPAN_OCCURRENCE — `EXACTLY 0` and
> `LESS_THAN 1` are rejected. Use a SPAN_RELATION with a negated predicate to check a
> span is absent relative to another span (see the missing-step example).

> **IMPORTANT:** `time_filter` is REQUIRED; `timeField` is always
> `{"field": "ingest_ts"}`.

> **IMPORTANT:** `schedule_type` is `fixed` (default) or `manual` — never dynamic.
> `interval_minutes` defaults to `60` and must be at least 5 (sub-hourly allowed).

> **IMPORTANT:** `warehouse` is OPTIONAL here — when omitted, the backend falls back
> to the account's default warehouse, which may not be where the agent's traces live.
> Prefer passing the agent's `warehouse_uuid` from `get_agent_metadata` explicitly.

## Key characteristics

- Uses `agent_span_alert_condition` (not `alert_conditions`) — `{"operator": "OR", "conditions": [...]}`
- Two condition types: `SPAN_OCCURRENCE` (count) and `SPAN_RELATION` (relate two spans)
- Requires `time_filter` with `timeField` (object `{"field": "ingest_ts"}`) and `lookbackInHrs`

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `description` | string | Yes | Human-readable monitor description (shown as display name) |
| `agent` | string | Yes | Agent reference — `agentReference` from `get_agent_metadata` (`{db}:{schema}.{name}` or OTel `service_name`) |
| `agent_span_alert_condition` | object | Yes | The span pattern that flags a trace (see below) |
| `time_filter` | object | Yes | `{"timeField": {"field": "ingest_ts"}, "lookbackInHrs": 24}` |
| `warehouse` | string | No | Warehouse name or UUID; defaults to the account default |
| `trace_table` | string | No | Explicit trace table — only for non-ClickHouse OTel agents |
| `agent_span_filters` | array | No | Optional — **only the `agent` field allowed** (no `workflow`/`task`/`spanName`); at most one |
| `schedule_type` | string | No | `fixed` (default) or `manual` |
| `interval_minutes` | int | No | Default `60`; at least 5 |
| `monitor_uuid` | string | No | UUID of an existing monitor to update in place (PUT semantics) |
| `dry_run` | boolean | No | Default `True` — preview YAML; set `False` to deploy |

## agent_span_alert_condition structure

`{"operator": "OR", "conditions": [...]}`. Supply at least one condition. Each is one
of two types. To OR several patterns together, list them as multiple entries in
`conditions` — a trace is flagged if any one matches.

### SPAN_OCCURRENCE — count how many times a span occurs

```json
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
```

| Field | Required | Description |
|-------|----------|-------------|
| `type` | Yes | `"SPAN_OCCURRENCE"`. |
| `predicate` | Yes | Always `{"name": "occurs"}`. `occurs` **cannot** be negated. |
| `spanField` | Yes | The span to count (see spanField below). |
| `comparisonOperator` | Yes | `"MORE_THAN"`, `"LESS_THAN"`, or `"EXACTLY"`. |
| `count` | Yes | Occurrences to compare against. `EXACTLY` requires count ≥ 1; `LESS_THAN` requires count ≥ 2; `MORE_THAN` requires count ≥ 0. |

Use `LESS_THAN 2` for "occurred exactly once when it should occur more". Occurrences
are counted per `(trace, parent span, span name)` group — pin the `task`/`workflow`
in `spanField` to the step you mean.

### SPAN_RELATION — relate two spans in a trace

```json
{
  "type": "SPAN_RELATION",
  "predicate": {"name": "occurs_before"},
  "spanField": {
    "spanName": {"literal": "generate"},
    "task": {"literal": "generate_answer"},
    "workflow": {"literal": "RAG Agent"},
    "type": "SPAN_FIELD"
  },
  "relatedSpanFields": [
    {
      "spanName": {"literal": "retrieve"},
      "task": {"literal": "generate_answer"},
      "workflow": {"literal": "RAG Agent"},
      "type": "SPAN_FIELD"
    }
  ]
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `type` | Yes | `"SPAN_RELATION"`. |
| `predicate` | Yes | `{"name": "occurs_with" \| "occurs_before" \| "occurs_after"}`. Add `"negated": true` for the inverse (e.g. `occurs_with` + negated = "occurs without"). |
| `spanField` | Yes | The primary span (see spanField below). |
| `relatedSpanFields` | Yes | One or more related spans. Each must share the same coarser `workflow` / `task` as `spanField` — a span-name comparison needs matching `task` and `workflow`; a task-level comparison needs matching `workflow`. |

### spanField structure

Identifies a span by workflow / task / span name. Fill in from coarse to fine.

| Field | Required | Format |
|-------|----------|--------|
| `type` | No (defaults `"SPAN_FIELD"`) | `"SPAN_FIELD"` |
| `workflow` | **Yes — always** | `{"literal": "workflow name"}` |
| `task` | Yes when `spanName` is set | `{"literal": "task name"}` — requires `workflow` |
| `spanName` | No | `{"literal": "span operation name"}` — requires `task` AND `workflow` |

**`workflow` is the minimum.** If you set `spanName`, you MUST also set `task` and
`workflow`. If you set `task`, you MUST also set `workflow`. All values use the
`{"literal": "..."}` format. Discover the real names with `get_agent_segments` and
`get_agent_trace`.

## Examples

The `agent` value below comes from `get_agent_metadata`'s `agentReference` field —
a platform `{database}:{schema}.{name}` reference or an OTel `service_name`.

### Alert when a specific span occurs more than 5 times

```
create_or_update_agent_trajectory_monitor(
    description="Alert when ChatBedrockConverse.chat exceeds 5 calls in a trace",
    agent="analytics:agents.support_bot",
    agent_span_alert_condition={
        "operator": "OR",
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
    dry_run=True
)
```

### Alert when a required step is missing (negated SPAN_RELATION)

"occurs 0 times" can't be expressed with SPAN_OCCURRENCE. To catch a missing step,
relate it to a step that always runs and negate the co-occurrence: alert when
`generate` occurs **without** the `validate_output` step that should follow it.

```
create_or_update_agent_trajectory_monitor(
    description="Alert when generation runs without a validation step",
    agent="checkout-agent",
    agent_span_alert_condition={
        "operator": "OR",
        "conditions": [
            {
                "type": "SPAN_RELATION",
                "predicate": {"name": "occurs_with", "negated": true},
                "spanField": {
                    "spanName": {"literal": "generate"},
                    "task": {"literal": "generate_answer"},
                    "workflow": {"literal": "Chat Agent"},
                    "type": "SPAN_FIELD"
                },
                "relatedSpanFields": [
                    {
                        "spanName": {"literal": "validate_output"},
                        "task": {"literal": "generate_answer"},
                        "workflow": {"literal": "Chat Agent"},
                        "type": "SPAN_FIELD"
                    }
                ]
            }
        ]
    },
    time_filter={"timeField": {"field": "ingest_ts"}, "lookbackInHrs": 24},
    dry_run=True
)
```

### Alert when a step runs fewer than 2 times

```
create_or_update_agent_trajectory_monitor(
    description="Alert when the safety_check step runs fewer than 2 times",
    agent="analytics:agents.support_bot",
    agent_span_alert_condition={
        "operator": "OR",
        "conditions": [
            {
                "type": "SPAN_OCCURRENCE",
                "predicate": {"name": "occurs"},
                "spanField": {
                    "spanName": {"literal": "safety_check"},
                    "task": {"literal": "validate_output"},
                    "workflow": {"literal": "Chat Agent"},
                    "type": "SPAN_FIELD"
                },
                "count": 2,
                "comparisonOperator": "LESS_THAN"
            }
        ]
    },
    time_filter={"timeField": {"field": "ingest_ts"}, "lookbackInHrs": 24},
    dry_run=True
)
```

## Common errors

| Error message | Cause | Fix |
|--------------|-------|-----|
| invalid / unresolvable `agent` reference | The `agent` value wasn't taken from `get_agent_metadata` | Use the exact `agentReference` value — do not construct it by hand, and never pass an MCON |
| "workflow should not be set" in agentSpanFilters | Trajectory monitors only allow the `agent` field in `agent_span_filters` | Remove `workflow`/`task`/`spanName`; put them in the condition's `spanField` |
| `AND` operator rejected | `agent_span_alert_condition.operator` set to `"AND"` | Use `"OR"` (or omit it); split an all-must-hold rule into separate monitors |
| `EXACTLY 0` / `LESS_THAN 1` rejected | Tried to express "occurs 0 times" | Use a negated SPAN_RELATION for a missing span, or `LESS_THAN 2` for "occurred only once" |
| spanField rejected | Set `spanName` without `task`+`workflow`, or `task` without `workflow` | Fill coarse-to-fine: `workflow` always; `task` needs `workflow`; `spanName` needs `task`+`workflow` |
