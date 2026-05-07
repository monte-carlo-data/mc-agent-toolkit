# Redaction pathways (V1)

Reference for the three V1 redaction pathways supported by the Monte Carlo
instrument-agent skill. Read this before generating any `mc.setup()` snippet
or proposing instrumentation that touches LLM calls.

---

## 1. Honest defaults — what the SDK captures and where it goes

> **CRITICAL — by default, prompt and completion content is sent to the OTLP
> endpoint as span attributes.** Customers who handle sensitive data must opt
> into one of the three pathways below before instrumenting. The default
> `setup-template.md` snippet ships with prompt capture **disabled** to make
> this an explicit opt-in rather than a surprise.

The four facts the customer needs to hear up front:

1. **SDK default.** The Monte Carlo OpenTelemetry SDK plus the
   `opentelemetry-instrumentation-*` packages capture full LLM **prompt** and
   **completion** content as span attributes whenever an instrumentor is
   loaded.
2. **Capture destination.** That content is sent over OTLP to whatever URL
   is configured in `mc.setup(otlp_endpoint=...)` — typically Monte Carlo's
   collector.
3. **Storage.** The content is stored alongside the rest of the trace in
   MC's pipeline.
4. **Mitigation.** Customers handling PII, PHI, credentials, or
   customer-content under privacy contracts must pick one of the three V1
   pathways below before any instrumentor is loaded in production.

This is fine for non-sensitive workloads. **It is a compliance footgun for
regulated workloads** (HIPAA, FedRAMP, EU data residency, customer-content
under privacy contracts).

---

## 2. Pathway A — Manual `create_llm_span` with redacted `prompts_to_record`

**When to use.** The customer wants spans to record an audit trail of LLM
calls, but wants the recorded version to be redacted (e.g., PII fields
scrubbed, credentials removed, customer identifiers hashed).

**How.** Replace the auto-instrumentor's recording with a manual
`mc.create_llm_span` call. Pass a redacted version of the messages to
`prompts_to_record`. Send the un-redacted version to the LLM separately.

Real production example —
[`monte-carlo-data/saas-serverless/ai-recommendations/llm_models/graph_creation.py @ ec2af0c L92`](https://github.com/monte-carlo-data/saas-serverless/blob/ec2af0ceb4346fa0489e010713b91bb5c0983f5d/ai-recommendations/llm_models/graph_creation.py#L92):

```python
# Redacted messages for tracing
converted_messages = []
redacted_messages = [{"role": "system", "content": system_prompt}]
try:
    converted_messages = _convert_prompt_messages(messages_for_tracing)
    redacted_messages.extend(converted_messages)
except ValueError as e:
    logger.warning(f"Failed to convert messages for tracing: {e}")

with mc.create_llm_span(
    span_name="anthropic.chat",
    provider="anthropic",
    model=model_name,
    operation="chat",
    prompts_to_record=redacted_messages,  # <- redacted version recorded in span
) as span:
    # Send the FULL (un-redacted) version to the LLM:
    result = invoke_model(model, full_messages, logger, model_type)

    # Helpers populate response-side span attributes:
    mc.add_llm_response_model(span, model_config.bedrock_model)
    mc.add_llm_completions(span, [{"role": "assistant", "content": str(result.content)}])
    mc.add_llm_tokens(
        span,
        prompt_tokens=result.usage.input_tokens,
        completion_tokens=result.usage.output_tokens,
        total_tokens=result.usage.total_tokens,
    )
```

The key idea: **`prompts_to_record`** is what gets stored in the span, and it
can differ from what is actually sent to the LLM. The customer redacts before
passing to `prompts_to_record`, then sends the un-redacted version through to
the LLM separately.

Walk-through points to cover with the customer:

- `prompts_to_record` takes a list of `{"role": ..., "content": ...}` dicts.
- The customer is responsible for the redaction logic. **The SDK does not
  redact.**
- Common redaction strategies:
  - Regex-based PII scrubbing (SSN, credit card, email patterns).
  - Structured redaction for known field names (e.g., scrub `password`,
    `api_key`, `ssn`).
  - Replacing entire prompt content with a hash + length (preserves "a
    prompt of N chars happened" without the content).
- The span context manager records request-side attributes. Helper
  functions populate response-side attributes after the LLM call returns:
  - `mc.add_llm_response_model(span, ...)` — model identifier of the
    response.
  - `mc.add_llm_completions(span, [...])` — completion content (also
    accepts a redacted list).
  - `mc.add_llm_tokens(span, prompt_tokens=..., completion_tokens=...,
    total_tokens=...)` — token counts (no content).

> **NEVER** pass the un-redacted messages as `prompts_to_record`. The whole
> point of this pathway is that the customer's redactor produces a separate
> clean version for tracing. Mixing the two defeats the pathway entirely.

> **IMPORTANT** — the same redaction discipline applies to
> `mc.add_llm_completions`. If the response can contain sensitive content
> (e.g., a model that summarizes PII), the customer must redact before
> passing to `add_llm_completions` too.

---

## 3. Pathway B — Disable prompt/completion capture entirely

**When to use.** The customer wants the trace tree (workflow / task / span
hierarchy plus timings, latency, tokens) but does **not** want prompt or
completion content captured anywhere.

**How.** Set instrumentor-specific environment variables to disable content
capture. Most openllmetry instrumentors honor environment variables like:

- `OTEL_INSTRUMENTATION_OPENAI_TRACE_PROMPTS=false`
- `OTEL_INSTRUMENTATION_LANGCHAIN_TRACE_PROMPTS=false`
- `OTEL_INSTRUMENTATION_ANTHROPIC_TRACE_PROMPTS=false`
- `TRACELOOP_TRACE_CONTENT=false` — global switch covering most
  openllmetry instrumentors.

The exact env var depends on the instrumentor. Direct the customer to the
specific instrumentor's PyPI page for the authoritative list.

> **IMPORTANT — this is the default the skill's `setup-template.md` snippet
> uses.** When the workflow's redaction question (step #3) returns "no — no
> sensitive data," the skill **still** proposes the prompts-disabled snippet
> with an explicit opt-in comment. Customers who want capture must edit the
> env var consciously.

What is still captured under Pathway B:

- The full trace tree (workflow → task → span hierarchy).
- Span timings and latency.
- Token counts.
- Model identifiers.
- Tool call structure (which tools were called, in what order).

What is dropped:

- Prompt text.
- Completion text.
- Tool call argument values (depending on the instrumentor — verify per
  instrumentor before promising the customer this).

---

## 4. Pathway C — Selective manual instrumentation for sensitive sections

**When to use.** Most of the agent is non-sensitive but a specific
tool/path handles sensitive data (e.g., one tool reads from a PII database,
the rest do not).

**How.** A hybrid:

- Keep the auto-instrumentor enabled with content capture turned **on** for
  the bulk of the agent.
- For the sensitive sections, **manually wrap** with
  `mc.create_llm_span(prompts_to_record=...)` (Pathway A) so the customer
  controls exactly what is recorded for those calls.
- For non-LLM sensitive operations, skip the `@trace_with_task` decorator on
  that function and let the auto-instrumentor's defaults apply only to the
  surrounding code.

This is the most surgical option. It requires the customer to know which
functions are sensitive. The skill's job is to walk through the customer's
code with them, mark the sensitive functions, and propose Pathway A for
those — and Pathway B globally — as a hybrid.

> **IMPORTANT** — Pathway C is easy to get wrong. If the customer
> misidentifies even one sensitive function, the auto-instrumentor will
> capture its prompts under the global default. When in doubt, default to
> Pathway B and let the customer upgrade selectively.

---

## 5. Choosing between pathways

| Scenario | Recommended pathway |
|---|---|
| Mostly non-sensitive, one or two sensitive tools | **C (selective)** — disable globally, manual span on sensitive paths |
| All prompts could contain PII (e.g., customer support transcripts) | **A (redact)** — manual `create_llm_span` with a redactor function |
| Compliance posture forbids any prompt content leaving the customer's network | **B (disable)** — keep the trace tree, drop the content |
| Customer hasn't decided / ambiguous | **B + revisit** — start with B (no content capture); upgrade to A when they have a redactor |

> **IMPORTANT — default the skill's first proposal to Pathway B** unless the
> customer explicitly opts into capturing content. "I don't think my prompts
> are sensitive" is not an opt-in. Pathway B with a clear opt-in path is.

---

## 6. What V1 does NOT do

> **OUT OF SCOPE for v1** — The skill does **not** auto-detect sensitive
> content (no automatic PII scanning) and does **not** scaffold redactor
> functions for the customer. The PRD lists those as future work.

The skill is *conversant* in the three pathways above and walks the customer
through them. **The customer writes their redactor.** If a customer asks the
skill to "build me a redactor," the correct response is to walk them through
Pathway A with their existing redaction utility (or to recommend they write
one) — not to scaffold one in their codebase.

---

## 7. NEVER edit any file without explicit user approval

When proposing a redaction pathway, the SKILL.md rule applies to every
single code change:

- **Pathway A** → propose the manual span wrap as a diff to the relevant
  function. Wait for per-file approval. Don't auto-apply.
- **Pathway B** → propose the env var documentation in the relevant config
  (e.g., `.env.example` or a README note). Wait for approval.
- **Pathway C** → walk through the customer's code, propose specific
  function-level diffs. Wait for per-file approval.

> **NEVER** apply a redaction pathway in the customer's repo without their
> explicit approval for that specific file. Redaction changes touch the
> data plane; a wrong default here can leak PII into traces or silently
> drop content the customer expected to see.

---

## Common mistakes

- **Auto-applying Pathway B as default without flagging the privacy
  implications.** The customer needs to know what the SDK captures by
  default, even when you're recommending the safer option. Don't bury the
  default behavior — name it.
- **Passing un-redacted messages to `prompts_to_record`.** Defeats the
  entire purpose of Pathway A. Always confirm the customer's redactor runs
  before the value reaches `prompts_to_record`.
- **Treating "no, my prompts aren't sensitive" as a license to capture
  everything.** Still default-disable. Customers can change their minds
  when their use case evolves; capture content only when they explicitly
  opt in.
- **Auto-scaffolding a redactor function.** Out of scope for v1. Walk the
  customer through the pathway; they write the redactor.
- **Skipping the redaction question in the workflow.** Step #3 is
  non-optional. Always ask before generating `mc.setup()`.
- **Forgetting that completions are content too.** Pathway A applies to
  `mc.add_llm_completions` as well. A redacted prompt with an un-redacted
  completion still leaks.
- **Recommending Pathway C without auditing every LLM call site.** A single
  missed call site under a global "capture on" default leaks. When in
  doubt, recommend B as the global default and layer A surgically.
