# Agent Evaluation Monitor

## When to use

Run LLM-evaluated quality checks on agent outputs. Best for:

- **Answer relevance scoring** — is the response relevant to the question?
- **Helpfulness and clarity** — is the response useful and well-structured?
- **Task completion** — did the agent complete what was asked?
- **Banned-keyword check** — does the output avoid specific banned keywords (e.g. password, ssn, api secret)?
- **Custom evaluation criteria** — via custom transforms

## Constraints

> **CRITICAL:** The monitor's source is authored via the `agent` reference, NOT a
> `dw_id` + `data_source`/MCON. Pass the `agentReference` value from `get_agent_metadata`
> — a platform `{database}:{schema}.{name}` reference or an OTel `service_name`. Do NOT
> pass an MCON as `agent`.

> **IMPORTANT:** `transforms` is now a TOP-LEVEL parameter (not nested under
> `data_source`). It defines the evaluation logic.

> **IMPORTANT:** `schedule_type` defaults to `fixed` (lowercase) and `interval_minutes`
> defaults to `60`. Valid `schedule_type` values: `fixed`, `dynamic`, `manual`.

> **IMPORTANT:** `agent_span_filters` is an optional refinement; when used, include at
> least the `agent` field.

> **IMPORTANT:** Use predefined transforms when possible — they have known output field
> names (see the predefined transforms tables below). Custom transforms require you to
> set the `alias` parameter correctly, which becomes the output field name used in
> `alert_conditions.fields`.

> **NEVER** set the `field` parameter on predefined transforms — omit it entirely.
> Setting `field` on a predefined transform causes "Field X doesn't exist" errors
> because the transform output field name is predetermined.

> **NEVER** use a `context` field on transforms — it is not supported and will cause errors.

## Key characteristics

- Requires `sampling_config` — controls how many spans are sampled for evaluation
- Supports a top-level `transforms` array — defines the evaluation logic
- Transform output field names are used in `alert_conditions.fields`
- Optional `is_agent_conversation_aggregation=True` to aggregate per conversation
- Does NOT support a `context` field on transforms — do not use it
- For predefined transforms, do NOT set the `field` parameter — omit it entirely

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `description` | string | Yes | Human-readable monitor description (shown as display name) |
| `agent` | string | Yes | Agent reference — `agentReference` from `get_agent_metadata` (`{db}:{schema}.{name}` or OTel `service_name`) |
| `alert_conditions` | array | Yes | Alert conditions using transform output field names |
| `sampling_config` | object | Yes | `{"percentage": 10.0}` or `{"count": 100}` |
| `transforms` | array | No | Evaluation transforms (predefined or custom); top-level, not under `data_source` |
| `is_agent_conversation_aggregation` | boolean | No | Aggregate evaluation per conversation instead of per span |
| `warehouse` | string | No | Warehouse name or UUID — only when the agent reference doesn't pin it down |
| `trace_table` | string | No | Explicit trace table — only for non-ClickHouse OTel agents |
| `agent_span_filters` | array | No | Optional span-scope refinement (`agent`, `workflow`, `task`, `spanName`) |
| `sensitivity` | string | No | Anomaly detection sensitivity for AUTO operators |
| `aggregate_by` | string | No | Time-window bucketing (`hour`/`day`/`week`/`month`) |
| `schedule_type` | string | No | Defaults to `fixed`. `fixed`/`dynamic`/`manual` |
| `interval_minutes` | int | No | Defaults to `60` for `fixed` |
| `monitor_uuid` | string | No | UUID of an existing monitor to update in place (PUT semantics) |
| `dry_run` | boolean | No | Default `True` — preview YAML; set `False` to deploy |

## Predefined LLM transforms

These have default output field names — no `alias` needed and do NOT set `field`:

| Transform function | Output field | Output type | Description |
|-------------------|-------------|-------------|-------------|
| `answer_relevance` | `relevance_score` | number (1-5) | Is the response relevant to the question? |
| `helpfulness` | `helpfulness_score` | number (1-5) | Is the response helpful? |
| `task_completion` | `completion_score` | number (1-5) | Did the agent complete the task? |
| `language_match` | `match_score` | number (1-5) | Does the response match the expected language? |
| `clarity` | `clarity_score` | number (1-5) | Is the response clear and well-structured? |
| `prompt_adherence` | `adherence_score` | number (1-5) | Does the response follow the prompt instructions? |
| `semantic_similarity` | `similarity_score` | number (0-5) | How similar is the response to a reference? |

## Predefined SQL transforms (rule-based, no LLM needed)

| Transform function | Output field | Output type | Description |
|-------------------|-------------|-------------|-------------|
| `output_length` | `word_count` | number | Word count of the completion |
| `json_validity` | `json_valid` | boolean | Is the completion valid JSON? |
| `keywords` | `content_safe` | boolean | TRUE if output does NOT contain banned keywords (password, ssn, api secret, credit card). Not a general PII/secrets detector. |

## Custom transforms

For `custom_prompt`, `custom_sql`, and `classification` transforms, the `alias`
parameter becomes the output field name — you MUST set `alias`.

Transform `categories` must be objects with `label` and optional `description`:
```json
[
    {"label": "relevant", "description": "The response addresses the user's question"},
    {"label": "not_relevant"}
]
```

## Alert conditions

Use `thresholdValue` (camelCase) for threshold operators — NOT `threshold_value` (snake_case).

```json
{
    "metric": "NUMERIC_MEAN",
    "operator": "LT",
    "fields": ["relevance_score"],
    "thresholdValue": 2
}
```

## Examples

The `agent` value below comes from `get_agent_metadata`'s `agentReference` field. The
first example uses a platform `{database}:{schema}.{name}` reference; the others use an
OTel `service_name`. Use whichever form `get_agent_metadata` returns for your agent.
Note that `transforms` is now a top-level parameter, no longer nested under `data_source`.

### Answer relevance evaluation (platform agent reference)

```
create_or_update_agent_evaluation_monitor(
    description="Chat Agent relevance evaluation",
    agent="analytics:agents.support_bot",
    transforms=[
        {"function": "answer_relevance"}
    ],
    alert_conditions=[
        {"metric": "NUMERIC_MEAN", "operator": "LT", "fields": ["relevance_score"],
         "thresholdValue": 2}
    ],
    sampling_config={"percentage": 10.0},
    agent_span_filters=[
        {"agent": {"value": "My Agent"}, "workflow": {"value": "Chat Agent"}}
    ],
    dry_run=True
)
```

### Banned-keyword check (OTel service_name)

```
create_or_update_agent_evaluation_monitor(
    description="Chat Agent content safety check",
    agent="checkout-agent",
    transforms=[
        {"function": "keywords"}
    ],
    alert_conditions=[
        {"metric": "NUMERIC_MEAN", "operator": "LT", "fields": ["content_safe"],
         "thresholdValue": 1}
    ],
    sampling_config={"count": 100},
    dry_run=True
)
```

### Custom classification

```
create_or_update_agent_evaluation_monitor(
    description="Chat Agent response tone classification",
    agent="checkout-agent",
    transforms=[
        {
            "function": "classification",
            "alias": "tone_label",
            "categories": [
                {"label": "professional", "description": "Business-appropriate tone"},
                {"label": "casual", "description": "Informal or overly relaxed tone"},
                {"label": "inappropriate", "description": "Rude, dismissive, or harmful tone"}
            ]
        }
    ],
    alert_conditions=[
        {"metric": "NUMERIC_MEAN", "operator": "GT", "fields": ["tone_label"],
         "thresholdValue": 0}
    ],
    sampling_config={"percentage": 5.0},
    schedule_type="fixed",
    interval_minutes=360,
    dry_run=True
)
```

## Common errors

| Error message | Cause | Fix |
|--------------|-------|-----|
| invalid / unresolvable `agent` reference | The `agent` value wasn't taken from `get_agent_metadata` | Use the exact `agentReference` value from `get_agent_metadata` — do not construct it by hand |
| "Field X doesn't exist" | Wrong transform output field name used in `alert_conditions.fields` | For predefined transforms, use the documented output field name (e.g., `relevance_score` for `answer_relevance`); for custom transforms, verify the `alias` matches |
