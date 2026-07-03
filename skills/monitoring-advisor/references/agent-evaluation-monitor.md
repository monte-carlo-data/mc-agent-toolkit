# Agent Evaluation Monitor

## When to use

Run LLM-evaluated quality checks on agent outputs. Best for:

- **Answer relevance scoring** — is the response relevant to the question?
- **Helpfulness and clarity** — is the response useful and well-structured?
- **Task completion** — did the agent complete what was asked?
- **Banned-keyword check** — does the output avoid specific banned keywords (e.g. password, ssn, api secret)?
- **Custom evaluation criteria** — a custom LLM check (`custom_prompt`) or SQL check (`custom_sql`) over span text

Do NOT use this for a raw numeric metric like latency or token count (use
`create_or_update_agent_metric_monitor`) — evaluation monitors add sampling and
transforms, which those don't need.

## Constraints

> **CRITICAL:** The monitor's source is the `agent` reference. Pass the
> `agentReference` value from `get_agent_metadata` verbatim — a platform
> `{database}:{schema}.{name}` reference or an OTel `service_name`. Never modify,
> truncate, or reconstruct it, and never pass an MCON.

> **CRITICAL:** `warehouse` is REQUIRED. Pass the agent's `warehouse_uuid` from
> `get_agent_metadata`; omitting it fails with "Warehouse not found". Use
> `get_warehouses` when `warehouse_uuid` is null or to resolve a warehouse by name.

> **CRITICAL:** `sampling_config` is REQUIRED. Provide `percentage`, `count`, or
> both. Per-span monitors cap `count` at 10,000; conversation-level monitors cap it
> at 500 (a percentage-only conversation config is capped at 500 per run).

> **IMPORTANT:** `transforms` is a TOP-LEVEL parameter. Each transform produces an
> output field that `alert_conditions.fields` references.

> **IMPORTANT:** `schedule_type` is `fixed` (default) or `manual` — never dynamic.
> `interval_minutes` defaults to `60` and must be at least 60 **and** a multiple of 60.

> **NEVER** set a `field` parameter on any transform. Predefined judges pull their
> inputs automatically; `custom_prompt` reads from its prompt's template variables;
> `custom_sql` reads from the columns in its expression. There is no `field` param,
> and no `context` param either.

> **NEVER** use `classification` or `sentiment` as a transform function. Their output
> column is not added to the evaluated schema, so no `alert_conditions` field can
> reference it — the monitor can't alert on the result (you get "Field `<alias>`
> doesn't exist"). To bucket or pass/fail a response, use a `custom_prompt` with
> `outputType: "boolean"` (a check) or `"string"`.

## Key characteristics

- Requires `sampling_config` — controls how many spans/conversations are sampled
- Supports a top-level `transforms` array — the evaluation logic
- Transform output field names are what `alert_conditions.fields` reference
- Optional `is_agent_conversation_aggregation=True` aggregates per conversation
  (see the conversation-grain section — OTel agents only)

## Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `description` | string | Yes | Human-readable monitor description (shown as display name) |
| `agent` | string | Yes | Agent reference — `agentReference` from `get_agent_metadata` (`{db}:{schema}.{name}` or OTel `service_name`) |
| `warehouse` | string | Yes | Warehouse name or UUID where the agent's traces live |
| `alert_conditions` | array | Yes | Alert conditions using transform output field names |
| `sampling_config` | object | Yes | `{"percentage": 10.0}`, `{"count": 100}`, or both |
| `transforms` | array | No | Evaluation transforms (predefined or custom); top-level |
| `is_agent_conversation_aggregation` | boolean | No | Aggregate evaluation per conversation (OTel agents only) |
| `trace_table` | string | No | Explicit trace table — only for non-ClickHouse OTel agents |
| `agent_span_filters` | array | No | Optional span-scope refinement; at most ONE filter object. At conversation grain (`is_agent_conversation_aggregation=True`) only `agent`/`workflow` are allowed — not `task`/`spanName` |
| `sensitivity` | string | No | Anomaly detection sensitivity for AUTO operators (`low`/`medium`/`high`) |
| `aggregate_by` | string | No | Time-window bucketing (`hour`/`day`/`week`/`month`) |
| `schedule_type` | string | No | `fixed` (default) or `manual` |
| `interval_minutes` | int | No | Default `60`; at least 60 and a multiple of 60 |
| `monitor_uuid` | string | No | UUID of an existing monitor to update in place (PUT semantics) |
| `dry_run` | boolean | No | Default `True` — preview YAML; set `False` to deploy |

## Predefined LLM transforms

Pass only `function` (and an optional `alias`, plus `modelConnectionId` on
BigQuery). Do NOT set `prompt`, `sqlExpression`, `outputType`, or `field` — the tool
rejects them. Each writes a numeric score (1–5, except `semantic_similarity` which is
0–5) to its built-in output field:

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

Same rule: pass only `function` (and an optional `alias`); do NOT set `prompt`,
`sqlExpression`, `outputType`, `modelConnectionId`, or `field`.

| Transform function | Output field | Output type | Description |
|-------------------|-------------|-------------|-------------|
| `output_length` | `word_count` | number | Non-whitespace word count of the first completion |
| `json_validity` | `json_valid` | boolean | Is the first completion valid JSON? |
| `keywords` | `content_safe` | boolean | TRUE if output does NOT contain banned keywords (password, ssn, api secret, credit card). Not a general PII/secrets detector. |

## Custom transforms

Each writes an output column named by its `alias`, and that alias is what
`alert_conditions.fields` references. `outputType` is **camelCase** and one of
`"number"`, `"string"`, `"boolean"`.

| Function | Set these | Do NOT set | Output type |
|----------|-----------|------------|-------------|
| `custom_prompt` | `prompt` (with a `{{variable}}`), `alias`, `outputType` | `field`, `sqlExpression` | number / string / boolean |
| `custom_sql` | `sqlExpression`, `alias`, `outputType` | `field`, `prompt`, `modelConnectionId` | number / string / boolean |

- **`custom_prompt` prompts MUST reference at least one template variable** —
  `{{prompts}}`, `{{completions}}`, or `{{expected_output}}` for a per-span monitor,
  or `{{conversation}}` for a conversation-level monitor. A prompt with no variable,
  an unknown variable, or the wrong variable for the grain is rejected.
- **`custom_sql` runs against warehouse columns.** On Snowflake Cortex agents,
  `prompts`/`completions` are arrays — reference the string columns
  `first_completion` / `full_completion` / `first_prompt` instead. The dry-run does
  not evaluate the SQL, so a bad column surfaces only at run time.
- **`modelConnectionId`** is optional for LLM-based transforms (predefined judges and
  `custom_prompt`) and REQUIRED on BigQuery warehouses. Omit it elsewhere.

## Conversation-grain judges

Each LLM judge has a `*_conversation` variant that evaluates a whole conversation
instead of a single span. These require `is_agent_conversation_aggregation: true`
**AND an OpenTelemetry agent** (platform agents like Snowflake Cortex reject
conversation aggregation). The output/score column is not always the span judge's
name:

| Conversation function | Output/score field |
|-----------------------|--------------------|
| `answer_relevance_conversation` | `relevance_score` |
| `task_completion_conversation` | `task_completion_score` |
| `helpfulness_conversation` | `helpfulness_score` |
| `clarity_conversation` | `clarity_score` |
| `prompt_adherence_conversation` | `adherence_score` |
| `language_match_conversation` | `match_score` |
| `satisfaction_conversation` | `satisfaction_score` (no per-span counterpart) |

At conversation grain, a `custom_prompt` may only reference `{{conversation}}`, and
the predefined SQL checks and `custom_sql` are not supported. At span grain,
`{{conversation}}` is not available. `agent_span_filters` at conversation grain may
scope only by `agent`/`workflow` — `task`/`spanName` are span-level and are rejected.

## Alert conditions

Use `thresholdValue` (camelCase) for threshold operators — NOT `threshold_value`
(snake_case). Each condition names one or more transform output fields in `fields`.

```json
{
    "metric": "NUMERIC_MEAN",
    "operator": "LT",
    "fields": ["relevance_score"],
    "thresholdValue": 2
}
```

**Match the metric to the transform's output type** (a mismatch is rejected at
dry-run):

- **number** (the 1–5 judges, `output_length`, numeric `custom_prompt`/`custom_sql`)
  → `NUMERIC_MEAN` and other numeric metrics.
- **boolean** (`json_validity`, `keywords`, boolean `custom_prompt`/`custom_sql`) →
  `TRUE_RATE` / `FALSE_RATE`. NEVER a numeric metric — a boolean field has no mean.
- `NULL_RATE` works on any output type.

`fields` must name a column in the evaluated schema — a predefined judge's built-in
field, a custom transform's `alias`, or a raw source column (span grain:
`duration_sec`, `total_tokens`, …; conversation grain: `turn_count`,
`duration_seconds`, `status`). Duplicate `(metric, field)` pairs across conditions
are rejected.

## Examples

The `agent` value below comes from `get_agent_metadata`'s `agentReference` field.
The first example uses a platform `{database}:{schema}.{name}` reference; the others
use an OTel `service_name`. Use whichever form your agent returns.

### Answer relevance evaluation (platform agent reference)

```
create_or_update_agent_evaluation_monitor(
    description="Chat Agent relevance evaluation",
    agent="analytics:agents.support_bot",
    warehouse="Prod Warehouse",
    transforms=[
        {"function": "answer_relevance"}
    ],
    alert_conditions=[
        {"metric": "NUMERIC_MEAN", "operator": "LT", "fields": ["relevance_score"],
         "thresholdValue": 2}
    ],
    sampling_config={"percentage": 10.0},
    dry_run=True
)
```

### Banned-keyword check as a boolean rate (OTel service_name)

`keywords` outputs the boolean `content_safe`, so alert on its false rate — a
numeric metric on a boolean field is rejected.

```
create_or_update_agent_evaluation_monitor(
    description="Chat Agent banned-keyword check",
    agent="checkout-agent",
    warehouse="Agent Observability",
    transforms=[
        {"function": "keywords"}
    ],
    alert_conditions=[
        {"metric": "FALSE_RATE", "operator": "GT", "fields": ["content_safe"],
         "thresholdValue": 0.05}
    ],
    sampling_config={"count": 100},
    dry_run=True
)
```

### Custom prompt as a pass/fail (boolean) check

The prompt references `{{completions}}`; there is no `field`; `outputType` is
`boolean` so the alert watches the true/false rate. This is the right shape for
"how often did the agent do X".

```
create_or_update_agent_evaluation_monitor(
    description="Did the agent disambiguate the product before answering?",
    agent="checkout-agent",
    warehouse="Agent Observability",
    transforms=[
        {
            "function": "custom_prompt",
            "alias": "disambiguated_product",
            "prompt": "Did this response either ask which product the user meant, or state which product it assumed, before answering? Response: {{completions}}. Answer true or false.",
            "outputType": "boolean"
        }
    ],
    alert_conditions=[
        {"metric": "FALSE_RATE", "operator": "GT", "fields": ["disambiguated_product"],
         "thresholdValue": 0.2}
    ],
    sampling_config={"percentage": 20.0},
    dry_run=True
)
```

### Custom SQL numeric check

`custom_sql` needs `sqlExpression` + `alias` + `outputType`; alert with a numeric
metric on the alias.

```
create_or_update_agent_evaluation_monitor(
    description="Completion length floor",
    agent="checkout-agent",
    warehouse="Agent Observability",
    transforms=[
        {
            "function": "custom_sql",
            "alias": "answer_chars",
            "sqlExpression": "LENGTH(first_completion)",
            "outputType": "number"
        }
    ],
    alert_conditions=[
        {"metric": "NUMERIC_MEAN", "operator": "LT", "fields": ["answer_chars"],
         "thresholdValue": 40}
    ],
    sampling_config={"percentage": 10.0},
    dry_run=True
)
```

### Conversation-level evaluation (OTel agent only)

Set `is_agent_conversation_aggregation=True`, use a `*_conversation` judge, and alert
on its score field (`task_completion_conversation` → `task_completion_score`).
Sampling `count` ≤ 500.

```
create_or_update_agent_evaluation_monitor(
    description="Task completion across full conversations",
    agent="checkout-agent",
    warehouse="Agent Observability",
    is_agent_conversation_aggregation=True,
    transforms=[
        {"function": "task_completion_conversation"}
    ],
    alert_conditions=[
        {"metric": "NUMERIC_MEAN", "operator": "AUTO", "fields": ["task_completion_score"]}
    ],
    sampling_config={"count": 100},
    dry_run=True
)
```

## Common errors

| Error message | Cause | Fix |
|--------------|-------|-----|
| Warehouse not found | `warehouse` omitted or wrong | Pass the agent's `warehouse_uuid` from `get_agent_metadata`; if null, list warehouses via `get_warehouses` |
| invalid / unresolvable `agent` reference | The `agent` value wasn't taken from `get_agent_metadata` | Use the exact `agentReference` value — do not construct it by hand, and never pass an MCON |
| "Field X doesn't exist" | Wrong transform output field name, or a `classification`/`sentiment` output that isn't in the schema | Use the documented output field (e.g. `relevance_score`) or a custom transform's `alias`; replace `classification`/`sentiment` with a `custom_prompt` (`outputType` `boolean`/`string`) |
| metric/output-type mismatch | Numeric metric on a boolean field (or vice versa) | `NUMERIC_MEAN` for numbers, `TRUE_RATE`/`FALSE_RATE` for booleans, `NULL_RATE` for any type |
| `task`/`spanName` rejected in `agent_span_filters` | Used a span-level filter dimension at conversation grain | At conversation grain (`is_agent_conversation_aggregation=True`), scope only by `agent`/`workflow` — `task`/`spanName` are span-level |
