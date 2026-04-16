# Agent Evaluation Monitor

## When to use

Run LLM-evaluated quality checks on agent outputs. Best for:

- **Answer relevance scoring** — is the response relevant to the question?
- **Helpfulness and clarity** — is the response useful and well-structured?
- **Task completion** — did the agent complete what was asked?
- **Content safety** — does the output avoid PII/secrets?
- **Custom evaluation criteria** — via custom transforms

## Key characteristics

- Requires `sampling_config` — controls how many traces are sampled for evaluation
- Supports `transforms` in `data_source` — defines the evaluation logic
- Transform output field names are used in `alert_conditions.fields`
- Does NOT support a `context` field on transforms — do not use it
- For predefined transforms, do NOT set the `field` parameter — omit it entirely

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `dw_id` | string | Yes | Warehouse UUID |
| `description` | string | Yes | Human-readable monitor description |
| `data_source` | object | Yes | Includes `type`, `mcon`, and `transforms` array |
| `alert_conditions` | array | Yes | Alert conditions using transform output field names |
| `schedule_config` | object | Yes | `{"scheduleType": "FIXED", "intervalMinutes": 60}` |
| `agent_span_filters` | array | Yes | Span filters — always include at least `agent` |
| `sampling_config` | object | Yes | `{"percentage": 10.0}` or `{"count": 100}` (max 10,000) |
| `dry_run` | boolean | No | Default `True` — preview without creating |

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
| `word_count` | `word_count` | number | Word count of the completion |
| `json_validity` | `json_valid` | boolean | Is the completion valid JSON? |
| `content_safety` | `content_safe` | boolean | Does the completion avoid PII/secrets? |

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

### Answer relevance evaluation

```
create_agent_evaluation_monitor(
    dw_id="<warehouse_uuid>",
    description="Chat Agent relevance evaluation",
    data_source={
        "type": "TABLE",
        "mcon": "<trace_table_mcon>",
        "transforms": [
            {"function": "answer_relevance"}
        ]
    },
    alert_conditions=[
        {"metric": "NUMERIC_MEAN", "operator": "LT", "fields": ["relevance_score"],
         "thresholdValue": 2}
    ],
    schedule_config={"scheduleType": "FIXED", "intervalMinutes": 60},
    agent_span_filters=[
        {"agent": {"value": "My Agent"}, "workflow": {"value": "Chat Agent"}}
    ],
    sampling_config={"percentage": 10.0},
    dry_run=True
)
```

### Content safety check

```
create_agent_evaluation_monitor(
    dw_id="<warehouse_uuid>",
    description="Chat Agent content safety check",
    data_source={
        "type": "TABLE",
        "mcon": "<trace_table_mcon>",
        "transforms": [
            {"function": "content_safety"}
        ]
    },
    alert_conditions=[
        {"metric": "NUMERIC_MEAN", "operator": "LT", "fields": ["content_safe"],
         "thresholdValue": 1}
    ],
    schedule_config={"scheduleType": "FIXED", "intervalMinutes": 60},
    agent_span_filters=[
        {"agent": {"value": "My Agent"}}
    ],
    sampling_config={"count": 100},
    dry_run=True
)
```

### Custom classification

```
create_agent_evaluation_monitor(
    dw_id="<warehouse_uuid>",
    description="Chat Agent response tone classification",
    data_source={
        "type": "TABLE",
        "mcon": "<trace_table_mcon>",
        "transforms": [
            {
                "function": "classification",
                "alias": "tone_label",
                "categories": [
                    {"label": "professional", "description": "Business-appropriate tone"},
                    {"label": "casual", "description": "Informal or overly relaxed tone"},
                    {"label": "inappropriate", "description": "Rude, dismissive, or harmful tone"}
                ]
            }
        ]
    },
    alert_conditions=[
        {"metric": "NUMERIC_MEAN", "operator": "GT", "fields": ["tone_label"],
         "thresholdValue": 0}
    ],
    schedule_config={"scheduleType": "FIXED", "intervalMinutes": 360},
    agent_span_filters=[
        {"agent": {"value": "My Agent"}}
    ],
    sampling_config={"percentage": 5.0},
    dry_run=True
)
```
