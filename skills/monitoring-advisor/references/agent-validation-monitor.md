# Agent Validation Monitor

## When to use

Assert a logical condition on agent span data and alert on violations. Best for:

- **Business rule assertions** — "total_tokens must be below 10000"
- **Data quality checks on span attributes** — "completions must never be null"
- **Compliance checks** — "PII detection must run on every trace"

Do NOT use it to trend a numeric metric (use `create_or_update_agent_metric_monitor`)
or to alert on span sequences / call counts (use
`create_or_update_agent_trajectory_monitor`).

## Constraints

> **CRITICAL:** The monitor's source is the `agent` reference. Pass the
> `agentReference` value from `get_agent_metadata` verbatim — a platform
> `{database}:{schema}.{name}` reference or an OTel `service_name`. Never modify,
> truncate, or reconstruct it, and never pass an MCON.

> **CRITICAL:** `warehouse` is REQUIRED. Pass the agent's `warehouse_uuid` from
> `get_agent_metadata`; use `get_warehouses` when it is null or to resolve by name.

> **CRITICAL:** `alert_condition` matches the rows to ALERT on. A `null` predicate
> alerts on spans where the field IS null. Express negation with the `negated` flag —
> there is NO `not_equal` and NO `not_null` predicate.

> **IMPORTANT:** BINARY conditions use `left`/`right`; UNARY conditions use `value`
> (NOT `left`). Getting this wrong is the most common failure.

> **IMPORTANT:** `time_filter` is REQUIRED and `timeField` is always
> `{"field": "ingest_ts"}`. `time_filter` is `{"timeField": {"field": "ingest_ts"}, "lookbackInHrs": <hours>}`.

> **IMPORTANT:** `schedule_type` is `fixed` (default) or `manual` — never dynamic.
> `interval_minutes` defaults to `60` and must be at least 5 (sub-hourly is allowed;
> no 60-minute alignment).

## Key characteristics

- Uses `alert_condition` as a `FilterGroup` — an `operator` (`AND`/`OR`) plus a
  `conditions` array of `BINARY` / `UNARY` / `SQL` / `GROUP` entries
- Requires `time_filter` (time field is always `ingest_ts`)
- Optional `is_agent_trace_aggregation` for trace-level assertions (OTel agents only)

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `description` | string | Yes | Human-readable monitor description (shown as display name) |
| `agent` | string | Yes | Agent reference — `agentReference` from `get_agent_metadata` (`{db}:{schema}.{name}` or OTel `service_name`) |
| `alert_condition` | object | Yes | FilterGroup — the condition that marks INVALID rows (see below) |
| `time_filter` | object | Yes | `{"timeField": {"field": "ingest_ts"}, "lookbackInHrs": 24}` |
| `warehouse` | string | Yes | Warehouse name or UUID where the agent's traces live |
| `trace_table` | string | No | Explicit trace table — only for non-ClickHouse OTel agents |
| `agent_span_filters` | array | No | Optional span-scope refinement; at most ONE filter object |
| `is_agent_trace_aggregation` | boolean | No | Aggregate per trace for trace-level assertions (OTel only) |
| `schedule_type` | string | No | `fixed` (default) or `manual` |
| `interval_minutes` | int | No | Default `60`; at least 5 |
| `tags` | array | No | Key-value tags, e.g. `[{"name": "agent", "value": "Support Bot"}]`. Tag every agent monitor with its agent's name — `{"name": "agent", "value": "<AGENT_NAME>"}` — so all of one agent's monitors are filterable as a group |
| `monitor_uuid` | string | No | UUID of an existing monitor to update in place (PUT semantics) |
| `dry_run` | boolean | No | Default `True` — preview YAML; set `False` to deploy |

## alert_condition structure (FilterGroup)

The top level is a group: an `operator` (`AND`/`OR`) and a `conditions` array. Each
condition is one of `BINARY`, `UNARY`, `SQL`, or `GROUP`.

### BINARY (compare two values)

```json
{
  "type": "BINARY",
  "predicate": {"name": "greater_than"},
  "left": [{"type": "FIELD", "field": "total_tokens"}],
  "right": [{"type": "LITERAL", "literal": "10000"}]
}
```

- `left`: exactly one `FIELD` value (the column being validated).
- `right`: exactly one value — usually a `LITERAL` (a string, even for numbers). The
  `in_set` predicate is the exception: it takes several `LITERAL`s in `right`.

### UNARY (single-value check)

```json
{
  "type": "UNARY",
  "predicate": {"name": "null"},
  "value": [{"type": "FIELD", "field": "completions"}]
}
```

- The field list is named **`value`** (NOT `left`), and holds exactly one `FIELD`.
- The example above matches spans where `completions` **is null**. To alert on
  non-null instead, add `"negated": true` (→ IS NOT NULL).

### SQL (custom boolean expression)

```json
{"type": "SQL", "sql": "total_tokens > 1000 AND duration_sec < 60"}
```

Use only when the condition can't be expressed with a predicate.

### GROUP (nested conditions)

```json
{
  "type": "GROUP",
  "operator": "OR",
  "conditions": [
    {"type": "BINARY", "...": "..."},
    {"type": "UNARY", "...": "..."}
  ]
}
```

### Predicates

Predicate names are matched by exact name — call `get_validation_predicates` to list
the full set. Key rules:

- **Express negation with the `negated` flag** — e.g. `{"name": "equal", "negated": true}`
  or `{"name": "null", "negated": true}`. Do NOT prefix names with `not_`. There is
  **no `not_equal` and no `not_null` predicate**.
- **BINARY predicates** include `equal`, `in_set`, `greater_than`,
  `greater_than_or_equal`, `less_than`, `less_than_or_equal`, `contains`,
  `starts_with`, `ends_with`, `matches_regex`. The four comparators (`greater_than` /
  `less_than` / `*_or_equal`) cannot be negated — use the inverse comparator instead.
- **UNARY predicates** include `null`, `empty_string`, `is_zero`, `is_negative`,
  `is_nan`, `is_between_0_and_1`, `is_between_0_and_100`, `is_uuid`, plus many locale /
  PII / timestamp checks. Fetch the full list with `get_validation_predicates`.

### Value types

| Type | Format |
|------|--------|
| `FIELD` | `{"type": "FIELD", "field": "column_name"}` — references a span field |
| `LITERAL` | `{"type": "LITERAL", "literal": "value_string"}` — a static value, always a string even for numbers |
| `SQL` | `{"type": "SQL", "sql": "..."}` — a SQL expression (used inside a BINARY `right`) |

Condition/value/operator keywords are uppercase: `BINARY`, `UNARY`, `SQL`, `GROUP`;
`FIELD`, `LITERAL`; `AND`, `OR`.

## Field notes

Use the span field names from `agent-span-fields.md` in `FIELD` values — not raw
table columns. Note in particular:

- `status_code` is **numeric** — the OTel span status code (`2` = error). Compare
  with a numeric literal (e.g. `equal` / `"2"`), not `"ERROR"`.
- The time field is always `ingest_ts`.

## Trace aggregation

`is_agent_trace_aggregation=True` is **OpenTelemetry-only.** A platform agent reference
(`{database}:{schema}.{name}`) is rejected — target an OTel `service_name`, or pass an
explicit `trace_table` to force the agent to be read as OpenTelemetry. At trace grain,
use trace-level fields (`span_count`, `llm_call_count`, `total_tokens`, …) and filter
only by `agent`.

## Examples

The `agent` value below comes from `get_agent_metadata`'s `agentReference` field —
a platform `{database}:{schema}.{name}` reference or an OTel `service_name`.

### Assert total_tokens stays below a threshold (platform agent reference)

```
create_or_update_agent_validation_monitor(
    description="Alert when total_tokens exceeds 10000",
    agent="analytics:agents.support_bot",
    warehouse="Analytics WH",
    tags=[{"name": "agent", "value": "Support Bot"}],
    alert_condition={
        "operator": "AND",
        "conditions": [
            {
                "type": "BINARY",
                "predicate": {"name": "greater_than"},
                "left": [{"type": "FIELD", "field": "total_tokens"}],
                "right": [{"type": "LITERAL", "literal": "10000"}]
            }
        ]
    },
    time_filter={"timeField": {"field": "ingest_ts"}, "lookbackInHrs": 24},
    dry_run=True
)
```

### Alert when a required field is null (UNARY uses `value`)

Business rule "completions must always be populated" → alert on the violating rows,
i.e. spans where `completions` **is null**, so the condition is a plain `null`
predicate.

```
create_or_update_agent_validation_monitor(
    description="Alert when the completions field is null",
    agent="analytics:agents.support_bot",
    warehouse="Analytics WH",
    alert_condition={
        "operator": "AND",
        "conditions": [
            {
                "type": "UNARY",
                "predicate": {"name": "null"},
                "value": [{"type": "FIELD", "field": "completions"}]
            }
        ]
    },
    time_filter={"timeField": {"field": "ingest_ts"}, "lookbackInHrs": 24},
    dry_run=True
)
```

### Span-level assertion scoped to a workflow

```
create_or_update_agent_validation_monitor(
    description="Alert when Chat Agent spans exceed 120s",
    agent="analytics:agents.support_bot",
    warehouse="Analytics WH",
    alert_condition={
        "operator": "AND",
        "conditions": [
            {
                "type": "BINARY",
                "predicate": {"name": "greater_than"},
                "left": [{"type": "FIELD", "field": "duration_sec"}],
                "right": [{"type": "LITERAL", "literal": "120"}]
            }
        ]
    },
    time_filter={"timeField": {"field": "ingest_ts"}, "lookbackInHrs": 24},
    agent_span_filters=[{"workflow": {"value": "Chat Agent"}}],
    dry_run=True
)
```

### Trace-level assertion (OTel agent)

```
create_or_update_agent_validation_monitor(
    description="Alert when a trace has more than 50 spans",
    agent="checkout-agent",
    warehouse="OTel WH",
    alert_condition={
        "operator": "AND",
        "conditions": [
            {
                "type": "BINARY",
                "predicate": {"name": "greater_than"},
                "left": [{"type": "FIELD", "field": "span_count"}],
                "right": [{"type": "LITERAL", "literal": "50"}]
            }
        ]
    },
    time_filter={"timeField": {"field": "ingest_ts"}, "lookbackInHrs": 24},
    is_agent_trace_aggregation=True,
    dry_run=True
)
```

## Common errors

| Error message | Cause | Fix |
|--------------|-------|-----|
| Warehouse not found | `warehouse` omitted or wrong | Pass the agent's `warehouse_uuid` from `get_agent_metadata`; if null, list warehouses via `get_warehouses` |
| invalid / unresolvable `agent` reference | The `agent` value wasn't taken from `get_agent_metadata` | Use the exact `agentReference` value — do not construct it by hand, and never pass an MCON |
| unknown predicate `not_equal` / `not_null` | Used a `not_`-prefixed predicate | Use the base predicate (`equal` / `null`) with `"negated": true` |
| UNARY condition rejected | Used `left` instead of `value` | UNARY conditions put the field in `value`; only BINARY uses `left`/`right` |
| "Field X doesn't exist" | Field name not in the PARSED_SPANS schema | Check `agent-span-fields.md`; `status_code` is numeric (compare with `"2"`, not `"ERROR"`) |
