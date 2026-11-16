# `mc.setup()` Template Reference

How to wire `mc.setup()` correctly for a customer's agent. This is a Tier 3 reference — use it once the workflow has classified runtime, picked an OTLP endpoint, and decided on prompt/completion capture.

Single concern: how the skill turns the workflow's answers into a correct, runnable `mc.setup()` snippet.

## SDK shape

```python
import montecarlo_opentelemetry as mc

mc.setup(
    agent_name=...,
    otlp_endpoint=...,
    instrumentors=[...],
    span_processor=...,  # optional; required for serverless
)
```

> **Source of truth for the `span_processor` kwarg contract:** the [`montecarlo-opentelemetry` PyPI page](https://pypi.org/project/montecarlo-opentelemetry/) (which mirrors the package README). When the SDK changes the kwarg's behavior, default, or auth-header injection rules, that page is the canonical source — re-read it before regenerating templates.

---

## 1. Choosing the template

Branch on `runtime` from `scripts/detect_libraries.py` **and** the collector / auth choices from workflow steps #2 and #9. Each combination has its own self-contained template below — pick one and paste it as-is (after substituting `agent_name`, endpoint resolution, and the instrumentor list). Do not mix-and-match between blocks.

| `runtime` value | Collector | Auth env vars | Template |
|---|---|---|---|
| `long_running` | any | any | [Long-running container](#long-running-container-default-batchspanprocessor) |
| `serverless` | MC-hosted | `MCD_DEFAULT_API_ID` / `MCD_DEFAULT_API_TOKEN` | [Serverless + MC-hosted + MCD_DEFAULT_*](#serverless--mc-hosted-collector--mcd_default_-env-vars) |
| `serverless` | MC-hosted | `OTEL_EXPORTER_OTLP_HEADERS` | [Serverless + MC-hosted + OTEL_EXPORTER_OTLP_HEADERS](#serverless--mc-hosted-collector--otel_exporter_otlp_headers) |
| `serverless` | Self-hosted | (auth at collector) | [Serverless + self-hosted collector](#serverless--self-hosted-collector) |
| `unknown` | — | — | Ask the user. Default to long-running, with an explicit note that the customer should switch to a serverless template if the agent runs on Lambda or another suspendable runtime. |

> **CRITICAL — serverless without `SimpleSpanProcessor` silently drops traces.** Lambda freezes the process between invocations. The default `BatchSpanProcessor` is suspended before its flush interval fires, and the spans never reach Monte Carlo. Symptom: customer instrumented their Lambda agent, ran it, and sees no traces in `get_agent_metadata`. Fix: switch to one of the serverless templates below. See `troubleshooting.md`.

> **CRITICAL — match the auth-path branch to the customer's actual setup before generating the snippet.** The `MCD_DEFAULT_*` template references `os.environ["MCD_DEFAULT_API_ID"]`; if the customer is on `OTEL_EXPORTER_OTLP_HEADERS` or self-hosted, that line raises `KeyError` at startup and tracing never initializes. Walk the customer through which auth path they're using *before* proposing the diff.

### Long-running container (default `BatchSpanProcessor`)

The default template. The SDK's built-in `BatchSpanProcessor` batches spans for efficient export, which is correct for any process that stays resident (containers, VMs, long-running workers).

```python
import os

import montecarlo_opentelemetry as mc
from opentelemetry.instrumentation.langchain import LangchainInstrumentor

# Resolve endpoint from env. If unset, skip setup so the agent runs uninstrumented.
otel_endpoint = os.getenv("OTEL_ENDPOINT")
if otel_endpoint:
    base_endpoint = otel_endpoint.rstrip("/")
    http_otel_endpoint = (
        base_endpoint
        if base_endpoint.endswith("/v1/traces")
        else f"{base_endpoint}/v1/traces"
    )

    mc.setup(
        agent_name="ai-agent",
        otlp_endpoint=http_otel_endpoint,
        instrumentors=[LangchainInstrumentor()],
    )
```

This template lets the OpenLLMetry instrumentors capture prompt/completion content (their default). For customers who want to suppress content capture, see the [prompts-disabled variant](#prompts-disabled-variant-opt-in-for-stricter-customers).

### Serverless + MC-hosted collector + `MCD_DEFAULT_*` env vars

The customer runs on Lambda (or another suspendable runtime), sends traces to Monte Carlo's hosted collector, and has `MCD_DEFAULT_API_ID` / `MCD_DEFAULT_API_TOKEN` set in their environment (workflow Step 9's preferred path).

`mc.setup()` only auto-injects `MCD_DEFAULT_*` headers when it builds the default exporter. With a custom `span_processor` we build the exporter ourselves, so we pass the auth headers explicitly.

```python
import logging
import os

import montecarlo_opentelemetry as mc
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.langchain import LangchainInstrumentor
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

AGENT_NAME = "monitoring-agent"


def init_tracing():
    otel_endpoint = os.getenv("OTEL_ENDPOINT")
    if not otel_endpoint:
        return  # tracing disabled

    # Use .get() (not os.environ[...]) so a partial-config window — endpoint set
    # but credentials missing — skips tracing instead of crashing the Lambda at
    # cold start with a KeyError.
    api_id = os.environ.get("MCD_DEFAULT_API_ID")
    api_token = os.environ.get("MCD_DEFAULT_API_TOKEN")
    if not api_id or not api_token:
        logging.warning(
            "Monte Carlo tracing disabled: OTEL_ENDPOINT is set but "
            "MCD_DEFAULT_API_ID / MCD_DEFAULT_API_TOKEN are missing."
        )
        return

    base_endpoint = otel_endpoint.rstrip("/")
    http_otel_endpoint = (
        base_endpoint
        if base_endpoint.endswith("/v1/traces")
        else f"{base_endpoint}/v1/traces"
    )

    mcd_headers = {"x-mcd-id": api_id, "x-mcd-token": api_token}

    # SimpleSpanProcessor flushes each span before the runtime can suspend the
    # process. BatchSpanProcessor would queue spans and lose them at freeze.
    exporter = OTLPSpanExporter(endpoint=http_otel_endpoint, headers=mcd_headers)
    simple_span_processor = SimpleSpanProcessor(exporter)

    mc.setup(
        agent_name=AGENT_NAME,
        otlp_endpoint=http_otel_endpoint,  # required by signature; ignored when span_processor is set
        instrumentors=[LangchainInstrumentor()],
        span_processor=simple_span_processor,
    )
```

### Serverless + MC-hosted collector + `OTEL_EXPORTER_OTLP_HEADERS`

The customer runs on Lambda, sends to Monte Carlo's hosted collector, and packs auth into the standard OTel env var (`OTEL_EXPORTER_OTLP_HEADERS=x-mcd-id=...,x-mcd-token=...`). `OTLPSpanExporter` reads that env var automatically, so the exporter takes no explicit `headers=` kwarg.

```python
import os

import montecarlo_opentelemetry as mc
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.langchain import LangchainInstrumentor
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

AGENT_NAME = "monitoring-agent"


def init_tracing():
    otel_endpoint = os.getenv("OTEL_ENDPOINT")
    if not otel_endpoint:
        return  # tracing disabled

    base_endpoint = otel_endpoint.rstrip("/")
    http_otel_endpoint = (
        base_endpoint
        if base_endpoint.endswith("/v1/traces")
        else f"{base_endpoint}/v1/traces"
    )

    # OTLPSpanExporter reads OTEL_EXPORTER_OTLP_HEADERS from the environment
    # automatically — no explicit `headers=` kwarg needed.
    exporter = OTLPSpanExporter(endpoint=http_otel_endpoint)
    simple_span_processor = SimpleSpanProcessor(exporter)

    mc.setup(
        agent_name=AGENT_NAME,
        otlp_endpoint=http_otel_endpoint,
        instrumentors=[LangchainInstrumentor()],
        span_processor=simple_span_processor,
    )
```

### Serverless + self-hosted collector

The customer runs on Lambda and sends to their own collector. Auth is handled at the collector — Monte Carlo never sees credentials. **Do not** reference `MCD_DEFAULT_*` anywhere in this template (not as a value read, not as a comment, not in a fallback).

```python
import os

import montecarlo_opentelemetry as mc
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.langchain import LangchainInstrumentor
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

AGENT_NAME = "monitoring-agent"


def init_tracing():
    otel_endpoint = os.getenv("OTEL_ENDPOINT")
    if not otel_endpoint:
        return  # tracing disabled

    base_endpoint = otel_endpoint.rstrip("/")
    http_otel_endpoint = (
        base_endpoint
        if base_endpoint.endswith("/v1/traces")
        else f"{base_endpoint}/v1/traces"
    )

    # Auth is enforced at the customer's collector; no headers from the exporter.
    exporter = OTLPSpanExporter(endpoint=http_otel_endpoint)
    simple_span_processor = SimpleSpanProcessor(exporter)

    mc.setup(
        agent_name=AGENT_NAME,
        otlp_endpoint=http_otel_endpoint,
        instrumentors=[LangchainInstrumentor()],
        span_processor=simple_span_processor,
    )
```

---

## 2. OTLP endpoint normalization

Customers provide either a collector base URL or a full `/v1/traces` endpoint. The skill must normalize **idempotently** — the same input run twice must produce the same output.

```python
base = customer_provided_url.rstrip("/")
if base.endswith("/v1/traces"):
    http_otel_endpoint = base
else:
    http_otel_endpoint = f"{base}/v1/traces"
```

Rules:

- If the URL already ends in `/v1/traces`, use as-is.
- Otherwise, append `/v1/traces` to the base.
- **NEVER double-append** (`https://collector/v1/traces/v1/traces` is broken).
- Strip trailing slashes before checking the suffix — `https://collector/v1/traces/` should not become `https://collector/v1/traces//v1/traces`.

> **IMPORTANT — show the resolved final URL to the user before generating any code.** Do not silently rewrite the customer's input. Ask: "I'll use `<resolved-url>` as the OTLP endpoint — is that correct?" and wait for confirmation. The customer needs to recognize the URL their collector is actually going to receive.

### Endpoint sources

| Source | Base URL | Resolved endpoint |
|---|---|---|
| MC-hosted collector | `https://integrations.getmontecarlo.com/otel` (per https://docs.getmontecarlo.com/docs/mcp-server) | `https://integrations.getmontecarlo.com/otel/v1/traces` |
| Self-hosted collector | Customer's own deploy | Ask the customer for the base URL, then normalize |

---

## 3. Prompt/completion capture — default on, opt-out for stricter customers

The default template the skill proposes **captures** prompt and completion content. That is the core value proposition: low-lift auto-instrumentation that records what the agent said and what the model said back. The OpenLLMetry instrumentors (`opentelemetry-instrumentation-langchain`, `-openai`, `-anthropic`, etc.) wrap the LLM SDK call and record full content as span attributes by default — no extra wiring needed.

**Data residency.** Whether the customer routes through the MC-hosted collector or a self-hosted one, trace content lives in the **customer's environment**. The MC-hosted collector is a write-back pass-through; it does not persist content on Monte Carlo's side. The decision about capturing content is a question of the customer's own risk tolerance and compliance posture, not about data leaving their network. See `redaction.md` for the full framing.

For most customers, ship the default templates in Section 1 unchanged.

### Prompts-disabled variant (opt-in for stricter customers)

A subset of customers (HIPAA workloads, regulated industries, company policy) prefer to suppress prompt/completion capture and rely on the structural value of traces (span shapes, latency, token counts, error rates) rather than the content itself.

When the workflow's redaction step (Step 3) returned "yes, redact," use this variant of whichever Section 1 template the runtime/collector branch picked. The only differences:

1. Set `TRACELOOP_TRACE_CONTENT=false` in code, before any instrumentor import. The OpenLLMetry instrumentors at `<=0.53.4` read this env var at span-emit time; setting it in code (rather than as a comment) is the only way to flip the default from inside the template.
2. Optionally wrap LLM calls with `mc.create_llm_span(...)` using placeholder-substitution to emit redacted prompt/completion attributes. See `redaction.md` for the substitution pattern.

The privacy default lives in code via `os.environ.setdefault(...)` rather than a comment because the instrumentors only honor an actual env var; a comment alone changes nothing at runtime.

```python
import os

# Stricter-customer variant: suppress prompt/completion content capture in the
# auto-instrumentors. Must be set before any opentelemetry.instrumentation.*
# import — the instrumentors read TRACELOOP_TRACE_CONTENT at span-emit time.
os.environ.setdefault("TRACELOOP_TRACE_CONTENT", "false")

import montecarlo_opentelemetry as mc
from opentelemetry.instrumentation.langchain import LangchainInstrumentor

otel_endpoint = os.getenv("OTEL_ENDPOINT")
if otel_endpoint:
    base_endpoint = otel_endpoint.rstrip("/")
    http_otel_endpoint = (
        base_endpoint
        if base_endpoint.endswith("/v1/traces")
        else f"{base_endpoint}/v1/traces"
    )

    mc.setup(
        agent_name="ai-agent",
        otlp_endpoint=http_otel_endpoint,
        instrumentors=[LangchainInstrumentor()],
    )
```

`os.environ.setdefault` preserves an explicit operator override (`TRACELOOP_TRACE_CONTENT=true`) while defaulting to off when unset.

> **CRITICAL — set `TRACELOOP_TRACE_CONTENT` at module scope, NOT inside `init_tracing()`.** The OpenLLMetry instrumentors read this env var when their package is *imported* (the `from opentelemetry.instrumentation.langchain import LangchainInstrumentor` line at the top of every serverless template). By the time `init_tracing()` runs the import has already happened and a `setdefault` call inside the function is a no-op. The splice point is **between `import os` and any `opentelemetry.instrumentation.*` import**.

#### Serverless splice — concrete example

For any of the Section 1 serverless templates (2, 3, or 4 — they share the same import layout), the patch is a single block inserted between `import os` and the first instrumentation import. Below is Template 2 with the splice applied; Templates 3 and 4 follow the same shape.

```python
import logging
import os

# Stricter-customer variant: suppress prompt/completion content capture in the
# auto-instrumentors. Must be set before any opentelemetry.instrumentation.*
# import — the instrumentors read TRACELOOP_TRACE_CONTENT at import time, so
# setting it inside init_tracing() below would be a no-op.
os.environ.setdefault("TRACELOOP_TRACE_CONTENT", "false")

import montecarlo_opentelemetry as mc
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.langchain import LangchainInstrumentor
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

AGENT_NAME = "monitoring-agent"


def init_tracing():
    # ... unchanged from Template 2 ...
    pass
```

The body of `init_tracing()` is identical to the unredacted Template 2 — the only difference is the three-line splice above the instrumentation imports.

> **IMPORTANT — `TRACELOOP_TRACE_CONTENT=false` is a prerequisite for any redaction under auto-instrumentation.** Manual `mc.create_llm_span` calls do not unwire the auto-instrumentor; if content capture is still on, the raw prompt/completion will be emitted alongside the redacted version. Set `TRACELOOP_TRACE_CONTENT=false` first, then layer manual spans on top if needed.

---

## 4. Env vars (only on the MC-hosted path)

Branch on the answer to workflow step #2 (collector source):

### MC-hosted collector

The customer needs auth credentials for the MC ingest endpoint. Either:

- `MCD_DEFAULT_API_ID` and `MCD_DEFAULT_API_TOKEN` (preferred), **or**
- `OTEL_EXPORTER_OTLP_HEADERS=x-mcd-id=...,x-mcd-token=...`

Confirm presence with a presence-only check:

```python
import os

assert os.environ.get("MCD_DEFAULT_API_TOKEN"), (
    "MCD_DEFAULT_API_TOKEN is not set. Configure it before running the agent."
)
```

> **CRITICAL — never log, echo, or include the value of `MCD_DEFAULT_API_TOKEN` or `OTEL_EXPORTER_OTLP_HEADERS` in any tool argument, diff, or transcript.** These are long-lived credentials. Editor transcripts get pasted into Slack and bug reports — a single `print(os.environ["MCD_DEFAULT_API_TOKEN"])` in a verify step would leak the token broadly without anyone realizing it. Use **only** presence-only checks (`bool(os.environ.get(...))`). Never read the value, never include it in a `Bash` command echo, never paste it into a confirmation message.

### Self-hosted collector

Auth is handled at the customer's collector — MC does not see the credentials. **Skip** the `MCD_*` prompt entirely. Do not generate env-var setup code, do not ask the customer for tokens, do not reference `MCD_DEFAULT_API_TOKEN` in the template.

---

## 5. Existing-`mc.setup()` decision matrix

When `scripts/detect_libraries.py` returns `existing_setup.found: true`, walk this decision tree. **Do not auto-scaffold a second `mc.setup()`** — the customer already has one, and silently adding another will create two agents with confusing telemetry.

| Scenario | What the skill does |
|---|---|
| Different `agent_name` (existing != intended) | Ask the user to confirm intent. Different names create different agents in MC. If the user wants a fresh one, propose **adding** the new `mc.setup()` next to the existing one (with explicit per-file approval). |
| Different `instrumentors` list | Propose merging the lists as a diff to the existing `mc.setup()` call. Wait for approval. Don't auto-merge. |
| Using `BatchSpanProcessor` but the runtime is now serverless (e.g. customer migrated to Lambda) | Propose switching to `SimpleSpanProcessor` (with `OTLPSpanExporter`) as a diff. Cite the matching serverless template from Section 1. Wait for approval. |
| Identical (same `agent_name`, same `instrumentors`, correct `span_processor` for the runtime) | No-op. Tell the user the existing setup is already correct and exit cleanly. |

> **IMPORTANT — read the existing `mc.setup()` source carefully before proposing a diff.** Do not assume the structure; the customer may have customizations the skill should preserve (custom resource attributes, conditional setup, env-var handling, logging hooks). The decision matrix above is the minimum — preserving customizations is also required.

---

## 6. CRITICAL — never edit any file without explicit user approval

This rule from `SKILL.md` applies to every file this reference covers:

> **CRITICAL — Never modify the customer's code without explicit per-file user approval.** Always propose the diff and wait for confirmation before writing the file. The skill is not a code generator that runs autonomously — it's an assistant that proposes changes for the customer to accept or reject.

This rule covers, at minimum:

- Source files where `mc.setup()` lands (the file the workflow proposes editing).
- Dependency files (`requirements.txt`, `pyproject.toml`, `Pipfile`, etc. — handled in `library-detection.md`).
- Env files (`.env`, `.env.example`, deployment manifests).

Surface every diff. Wait for `yes` per file. Never batch-approve across files.

---

## Common mistakes

- **Generating the default `BatchSpanProcessor` template for a Lambda agent.** Silent trace loss. Always check `runtime` first and pick a serverless template from Section 1.
- **Mixing-and-matching between Section 1 templates** (e.g., taking the `MCD_DEFAULT_*` block's `headers=` line and pasting it into the self-hosted template). Each template is self-contained — pick one and use it as-is.
- **Double-appending `/v1/traces`** (e.g. `https://collector/v1/traces/v1/traces`). Broken endpoint. Normalize idempotently — check the suffix before appending.
- **Forgetting to render the resolved final endpoint to the user** before generating code. Opaque magic. Always show the resolved URL and wait for confirmation.
- **Layering manual redaction on top of an auto-instrumentor without setting `TRACELOOP_TRACE_CONTENT=false`.** The raw content still gets emitted by the auto-instrumentor alongside the redacted version. The env var is a prerequisite for any redaction under auto-instrumentation — see `redaction.md`.
- **Reading or echoing `MCD_DEFAULT_API_TOKEN` to confirm it's set.** Credential leak. Use presence-only (`bool(os.environ.get(...))`).
- **Auto-scaffolding a duplicate `mc.setup()` when one already exists.** Confusing telemetry, two agents in MC. Walk the decision matrix instead.
- **Editing `requirements.txt` / `pyproject.toml` / source files without explicit per-file approval.** Violates the SKILL.md guardrail. Propose every diff, wait for `yes` per file.
- **Forgetting that `mc.setup()` does not auto-inject auth headers when `span_processor=` is set.** With the default exporter, `mc.setup()` injects `MCD_DEFAULT_*` from env vars automatically. With a custom `span_processor` the customer constructs the `OTLPSpanExporter`, so the auth path must be made explicit at exporter-construction time. Match the customer's setup: (a) MC-hosted with `MCD_DEFAULT_*` env vars → pass `headers={"x-mcd-id": ..., "x-mcd-token": ...}` to `OTLPSpanExporter`; (b) MC-hosted with `OTEL_EXPORTER_OTLP_HEADERS` → omit `headers=` (the exporter reads the env var); (c) self-hosted collector → omit `headers=` (auth is at the collector). Symptom of getting it wrong: traces emit but never appear in MC because the collector rejects them as unauthenticated, **or** `init_tracing()` raises `KeyError` at startup because the template references `MCD_DEFAULT_*` that the customer isn't using.
