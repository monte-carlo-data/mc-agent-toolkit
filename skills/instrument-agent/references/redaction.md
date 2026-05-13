# Redaction guidance (V1)

Reference for the V1 redaction guidance supported by the Monte Carlo
instrument-agent skill. Read this before generating any `mc.setup()` snippet or
proposing instrumentation that touches LLM calls.

---

## 1. What the SDK captures by default — and where it lives

> **CRITICAL — capture-on is the value proposition, not a footgun.** The
> Monte Carlo OpenTelemetry SDK plus the `opentelemetry-instrumentation-*`
> auto-instrumentors capture full LLM **prompt** and **completion** content
> as span attributes whenever an instrumentor is loaded. This is the core use
> case: low-lift auto-instrumentation that records what the agent said and what
> the model said back.

The facts the customer needs to hear up front:

1. **SDK default.** When an OpenLLMetry instrumentor is loaded
   (`opentelemetry-instrumentation-langchain`, `-openai`, `-anthropic`,
   `-bedrock`, `-vertexai`, etc.), the auto-instrumentor wraps the LLM SDK
   call directly and records full prompt and completion content as span
   attributes. No decorator or manual span is required for capture.
2. **Transport.** Spans are sent over OTLP to whatever endpoint is
   passed to `mc.setup(otlp_endpoint=...)`. The customer always supplies
   the endpoint explicitly — the SDK has no built-in default. The
   templates in `setup-template.md` resolve it from an env var
   (`OTEL_ENDPOINT`). The MC-hosted collector also requires credentials
   or OTLP headers as shown in `setup-template.md`; a self-hosted
   collector handles auth at the collector.
3. **Data residency — traces live in the customer's environment.** The
   MC-hosted collector is a write-back pass-through. It routes spans back
   to the customer's storage and **does not persist trace content on
   Monte Carlo's side.** Trace content stays in the customer's environment.

For most customers, ship with full capture. **Prompt/completion content is
the most valuable thing the SDK records** — token counts and span shapes
alone don't answer "why did the agent say that?"

---

## 2. When customers want redaction

Most customers ship with full capture. A subset with stricter requirements
choose to redact. Examples of stricter situations:

- **HIPAA workloads** where prompts or completions can contain PHI, and
  the customer's policy is that PHI never enters any tracing or
  observability tool regardless of where it's stored.
- **Customers whose contracts forbid PII in tracing tools** — some
  enterprise contracts treat tracing systems as a separate data-handling
  surface, independent of where the underlying data lives.
- **Multi-tenant agents** where prompts contain another customer's content
  and the operator wants to scrub before it lands in their own trace store.
- **Credential / secret leakage risk** — agents that occasionally receive
  API keys or tokens in user input.

Redaction is a choice for these customers, not a default privacy posture.
The skill walks them through how to opt out of content capture (and
optionally substitute placeholders) when they ask.

---

## 3. Layer 1 for redaction: disable auto-instrumentor content capture

> **CRITICAL — disabling auto-capture is a hard prerequisite for ALL redaction.** If
> the customer keeps the auto-instrumentor with content capture on AND
> also calls `mc.create_llm_span` with redacted prompts, they end up with
> **duplicate spans** — one redacted (manual) and one with the full
> content (auto). That defeats the redaction. Any redaction story starts
> with disabling auto-capture.

**How.** The OpenLLMetry instrumentors all read a single env var:
`TRACELOOP_TRACE_CONTENT`. Set it to `"false"` to disable content capture
across the entire OpenLLMetry instrumentor family.

```bash
export TRACELOOP_TRACE_CONTENT=false
```

Or in code, **before any instrumentor imports**:

```python
import os
os.environ.setdefault("TRACELOOP_TRACE_CONTENT", "false")

# Only AFTER the env var is set can the instrumentor imports be safe:
import monte_carlo_observability_sdk as mc
mc.setup(...)
```

> **NEVER document `OTEL_INSTRUMENTATION_<lib>_TRACE_PROMPTS`** as the
> mechanism. Those env vars do not exist in the OpenLLMetry instrumentors.
> `TRACELOOP_TRACE_CONTENT` is the single source of truth.

**What is still captured with content capture disabled:**

- The full trace tree (workflow → task → span hierarchy).
- Span timings and latency.
- Token counts.
- Model identifiers.
- Tool call structure (which tools were called, in what order).

**What is dropped:**

- Prompt text.
- Completion text.
- Tool call argument values (depending on the instrumentor — verify
  per-instrumentor before promising the customer this).

For customers who want zero content but still want trace shape, this is
the complete answer. For customers who want some content with sensitive
fields scrubbed, layer manual redacted spans on top.

---

## 4. Layer 2 for selective content: manual `mc.create_llm_span` with placeholder-substituted `prompts_to_record`

**When to use.** The customer has already disabled auto-capture and wants
spans to record an audit trail of LLM calls with sensitive fields replaced
by placeholders — instead of having no content at all.

**How — the placeholder-substitution technique.** Keep **two sets of
prompts** in memory:

- One set with placeholder values where sensitive fields would go (e.g.,
  `"<SSN>"`, `"<EMAIL>"`, `"<CUSTOMER_NAME>"`). This set is what gets
  passed to `prompts_to_record`.
- One set with the real sensitive values. This set is what gets sent to
  the LLM.

The structure of the recorded prompt is preserved (role, shape,
non-sensitive context) while the sensitive fields are replaced with stable
placeholders that are useful for debugging without leaking content.

```python
# Build two prompt sets: one with placeholders for tracing, one real for the LLM.
redacted_messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": f"Look up account for customer <CUSTOMER_NAME>"},
]
full_messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": f"Look up account for customer {real_customer_name}"},
]

with mc.create_llm_span(
    span_name="anthropic.chat",
    provider="anthropic",
    model=model_name,
    operation="chat",
    prompts_to_record=redacted_messages,  # <- placeholder version recorded in span
) as span:
    # Send the FULL (un-redacted) version to the LLM:
    result = invoke_model(model, full_messages, logger, model_type)

    # Helpers populate response-side span attributes:
    mc.add_llm_response_model(span, model_config.bedrock_model)
    mc.add_llm_completions(
        span,
        # Redact the completion too if the response can contain sensitive content:
        [{"role": "assistant", "content": redact_completion(str(result.content))}],
    )
    mc.add_llm_tokens(
        span,
        prompt_tokens=result.usage.input_tokens,
        completion_tokens=result.usage.output_tokens,
        total_tokens=result.usage.total_tokens,
    )
```

The key idea: **`prompts_to_record`** is what gets stored in the span, and
it can differ from what is sent to the LLM. The customer builds the
placeholder-substituted version and passes it to `prompts_to_record`; the
real values go to the LLM separately.

Walk-through points to cover with the customer:

- `prompts_to_record` takes a list of `{"role": ..., "content": ...}`
  dicts. Shape it the same as `full_messages` so spans remain readable.
- The customer is responsible for the substitution logic. **The SDK does
  not redact.**
- Pick stable placeholder tokens (e.g., `<SSN>`, `<EMAIL>`) so future
  debuggers reading the trace can recognize the structure.
- Response-side helpers populate span attributes after the LLM call:
  - `mc.add_llm_response_model(span, ...)` — model identifier of the
    response.
  - `mc.add_llm_completions(span, [...])` — completion content (also
    accepts a placeholder-substituted list).
  - `mc.add_llm_tokens(span, prompt_tokens=..., completion_tokens=...,
    total_tokens=...)` — token counts (no content).

> **NEVER** pass the un-substituted messages as `prompts_to_record`. The
> whole point is that the placeholder version is what reaches the span.
> Mixing the two defeats redaction entirely.

> **IMPORTANT** — the same discipline applies to `mc.add_llm_completions`.
> If the response can contain sensitive content (e.g., a model that
> summarizes PHI), substitute placeholders in the completion before
> passing it to `add_llm_completions` too. A scrubbed prompt with a raw
> completion still leaks.
>
> Completion redaction is often harder than prompt redaction because model
> output is nondeterministic. Ask the customer what the expected output is
> and whether it can contain sensitive data. If the completion is
> unstructured or there is no reliable way to know which part is sensitive,
> redact the whole completion or omit completion content rather than
> recording a partial scrub that may leak.

> **IMPORTANT** — decorators (e.g., `@trace_with_task`) only add
> workflow/task metadata around a function. They do **not** gate what the
> auto-instrumentor captures inside that function. If auto-capture is on,
> the LLM SDK call is wrapped regardless of decorator presence. The
> `TRACELOOP_TRACE_CONTENT=false` env-var disable is the only way to stop
> auto-capture.

---

## 5. Choosing redaction configurations

| Scenario | Required setup |
|---|---|
| No redaction needed — capture everything (default) | Leave auto-instrumentor alone with full content capture. No env var change, no manual spans. |
| Want trace tree but **no** content at all | Disable auto-capture only — set `TRACELOOP_TRACE_CONTENT=false` before instrumentor imports. |
| Want trace tree + selective content with placeholders | Disable auto-capture, then call `mc.create_llm_span` with placeholder-substituted `prompts_to_record` (and `add_llm_completions`) at sensitive call sites. |

> **IMPORTANT — do not propose manual redacted spans without disabling auto-capture.** Without the
> env-var disable, the auto-instrumentor and the manual span both fire,
> producing duplicate spans (one redacted, one full-content). The
> redaction is silently undone.

---

## 6. What V1 does NOT do

> **OUT OF SCOPE for v1** — The skill does **not** auto-detect sensitive
> content (no automatic PII scanning) and does **not** scaffold redactor
> or placeholder-substitution functions for the customer.

The skill is *conversant* in the options above and walks the customer
through them. **The customer writes their substitution logic.** If a
customer asks the skill to "build me a redactor," the correct response is
to walk them through disabling auto-capture plus optional manual redacted
spans with their existing utilities (or to recommend they write the
substitution helpers themselves) — not to
scaffold one in their codebase.

---

## 7. NEVER edit any file without explicit user approval

When proposing a redaction change, the SKILL.md rule applies to every
single code change:

- **Disable auto-capture** → propose the env var setting in the relevant config
  (e.g., `.env.example`, deployment manifest, or the `mc.setup()` module
  with `os.environ.setdefault(...)` before imports). Wait for per-file
  approval.
- **Optional manual redacted spans** → propose the manual span wrap as a diff
  to the relevant function. Wait for per-file approval. Don't auto-apply.

> **NEVER** apply a redaction change in the customer's repo without
> their explicit approval for that specific file. Redaction changes
> touch the data plane; a wrong default here can leak sensitive content
> into traces or silently drop content the customer expected to see.

---

## Common mistakes

- **Treating env-var disable as optional when redaction is wanted.**
  Disabling auto-capture is mandatory for any redaction story. Without it,
  the auto-instrumentor still fires alongside the manual span and produces
  duplicate spans — one redacted, one full-content. The redaction is defeated.
- **Misstating data residency.** Trace content lives in the customer's
  environment. The MC-hosted collector routes spans back to the customer's
  storage without persisting content on the MC side. Don't tell customers
  "MC stores your prompts" — that's wrong.
- **Framing redaction as a privacy default.** Capture-on is the value
  proposition. Redaction is a choice for stricter customers, not a
  required privacy posture.
- **Recommending lossy fingerprints (e.g., hashing the prompt with its
  character count) as the primary technique.** Placeholder-substitution
  is the recommended
  structured technique — it preserves prompt shape and is useful for
  debugging. Hashes throw away the structure that makes the trace
  readable.
- **Assuming decorators gate auto-capture.** They don't. The
  auto-instrumentor wraps the LLM SDK call regardless of whether the
  surrounding function is decorated. Only `TRACELOOP_TRACE_CONTENT=false`
  stops auto-capture.
- **Setting `TRACELOOP_TRACE_CONTENT` *after* instrumentor imports.** Too
  late — the instrumentors read the env var at import/init time. Set it
  before any `mc.setup()` or instrumentor import runs.
- **Passing un-substituted messages to `prompts_to_record`.** Defeats
  the entire purpose of manual redacted spans. Confirm the placeholder
  version is what reaches `prompts_to_record`.
- **Forgetting that completions are content too.** Manual redacted spans apply to
  `mc.add_llm_completions` as well. A placeholder-substituted prompt with a
  raw completion still leaks. If the completion can contain sensitive data
  and cannot be scrubbed reliably, redact or omit the whole completion.
- **Auto-scaffolding a redactor or substitution helper.** Out of scope
  for v1. Walk the customer through the redaction options; they write the
  substitution logic.
