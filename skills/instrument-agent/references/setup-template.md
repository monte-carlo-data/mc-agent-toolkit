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

> **Source of truth for the `span_processor` kwarg contract:** [`montecarlo-opentelemetry` README — Configuring the span processor / Serverless and other suspendable runtimes](https://github.com/monte-carlo-data/montecarlo-opentelemetry/blob/main/README.md#configuring-the-span-processor). When the SDK changes the kwarg's behavior, default, or auth-header injection rules, that README is the canonical source — re-read it before regenerating templates.

---

## 1. Choosing the template (serverless vs long-running)

Branch on `runtime` from `scripts/detect_libraries.py`:

| `runtime` value | Template |
|---|---|
| `long_running` | Default template (`BatchSpanProcessor`, no `span_processor` kwarg). |
| `serverless` | **MUST** use the `SimpleSpanProcessor` template. |
| `unknown` | Ask the user. Default to long-running, with an explicit note that the customer should switch to `SimpleSpanProcessor` if the agent runs on Lambda or another suspendable runtime. |

> **CRITICAL — serverless without `SimpleSpanProcessor` silently drops traces.** Lambda freezes the process between invocations. The default `BatchSpanProcessor` is suspended before its flush interval fires, and the spans never reach Monte Carlo. Symptom: customer instrumented their Lambda agent, ran it, and sees no traces in `get_agent_metadata`. Fix: switch to `SimpleSpanProcessor`. See `troubleshooting.md`.

### Long-running container template (default `BatchSpanProcessor`)

Source: [`monte-carlo-data/ai-agent/ai_agent/app.py @ 854235b L84`](https://github.com/monte-carlo-data/ai-agent/blob/854235bf9e004611584138945c928f58e8493e6c/ai-agent/ai_agent/app.py#L84)

```python
import os

# Default to NOT capturing prompt/completion content. The OpenLLMetry
# instrumentors (langchain, openai, anthropic, etc.) read TRACELOOP_TRACE_CONTENT
# at span-emit time and default to "true" — so the template must explicitly
# set it to "false" before any spans are produced. Customers who want capture
# (after reviewing redaction options in references/redaction.md) can override
# by setting TRACELOOP_TRACE_CONTENT=true in their environment.
os.environ.setdefault("TRACELOOP_TRACE_CONTENT", "false")

import montecarlo_opentelemetry as mc
from opentelemetry.instrumentation.langchain import LangchainInstrumentor

# Resolve endpoint from env. If unset, skip setup so the agent runs uninstrumented.
MC_OTEL_ENDPOINT = os.getenv("MC_OTEL_ENDPOINT")
if MC_OTEL_ENDPOINT:
    base_endpoint = MC_OTEL_ENDPOINT.rstrip("/")
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

### Serverless template (`SimpleSpanProcessor` REQUIRED)

Source: [`montecarlo-opentelemetry` README — Serverless and other suspendable runtimes](https://github.com/monte-carlo-data/montecarlo-opentelemetry/blob/main/README.md#serverless-and-other-suspendable-runtimes). Production usage cross-reference: [`monte-carlo-data/saas-serverless/ai-recommendations/common/tracing.py @ ec2af0c L5`](https://github.com/monte-carlo-data/saas-serverless/blob/ec2af0ceb4346fa0489e010713b91bb5c0983f5d/ai-recommendations/common/tracing.py#L5).

```python
import os

# Default to NOT capturing prompt/completion content. The OpenLLMetry
# instrumentors (langchain, openai, anthropic, etc.) read TRACELOOP_TRACE_CONTENT
# at span-emit time and default to "true" — so the template must explicitly
# set it to "false" before any spans are produced. Customers who want capture
# (after reviewing redaction options in references/redaction.md) can override
# by setting TRACELOOP_TRACE_CONTENT=true in their environment.
os.environ.setdefault("TRACELOOP_TRACE_CONTENT", "false")

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

    # This template assumes the MC-hosted collector with MCD_DEFAULT_API_ID
    # and MCD_DEFAULT_API_TOKEN env vars (section 4's preferred path). For
    # OTEL_EXPORTER_OTLP_HEADERS or self-hosted collectors, see "Variants for
    # other auth paths" below.
    #
    # mc.setup() only auto-injects MCD_DEFAULT_* headers when it builds the
    # default exporter. With a custom span_processor we build the exporter
    # ourselves, so we pass auth headers explicitly here.
    mcd_headers = {
        "x-mcd-id": os.environ["MCD_DEFAULT_API_ID"],
        "x-mcd-token": os.environ["MCD_DEFAULT_API_TOKEN"],
    }

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

#### Variants for other auth paths

The template above is for the MC-hosted collector with `MCD_DEFAULT_*` env vars (section 4's preferred path). The other two valid auth paths take small adjustments — propose the matching shape based on the customer's answer to workflow step #2 (collector source) and step #9 (env vars).

**MC-hosted collector + `OTEL_EXPORTER_OTLP_HEADERS`** (the customer packs `x-mcd-id` / `x-mcd-token` into the standard OTel env var):

- Drop the `mcd_headers` construction.
- Build the exporter without `headers=`: `exporter = OTLPSpanExporter(endpoint=http_otel_endpoint)`.
- `OTLPSpanExporter` reads `OTEL_EXPORTER_OTLP_HEADERS` from the environment automatically — no explicit kwarg needed.

**Self-hosted collector** (auth is handled at the collector, MC does not see credentials):

- Drop the `mcd_headers` construction entirely.
- Build the exporter without `headers=`: `exporter = OTLPSpanExporter(endpoint=http_otel_endpoint)`.
- **Do not** reference `MCD_DEFAULT_*` in the customer's code — not as a value read, not as a comment, not in a fallback. Per section 4, self-hosted is a clean skip of the `MCD_*` surface.

> **CRITICAL — match the auth-path branch to the customer's actual setup before generating the snippet.** The default template references `os.environ["MCD_DEFAULT_API_ID"]`; if the customer is on `OTEL_EXPORTER_OTLP_HEADERS` or self-hosted, that line raises `KeyError` at startup and tracing never initializes. Walk the customer through which auth path they're using *before* proposing the diff.

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

## 3. Default snippet — prompts disabled

The default template the skill proposes has prompt/completion capture **disabled**. Customers who want to capture prompts must opt in explicitly.

**Why default-off:** prompts and completions can contain PII, PHI, credentials, and other sensitive data. Default-on capture means a customer who runs the happy path is sending raw inputs to MC's OTLP collector before they ever read `redaction.md`. Default-off is the safe default; opt-in is the explicit choice.

The mechanism: the OpenLLMetry instrumentors (`opentelemetry-instrumentation-langchain`, `-openai`, `-anthropic`, and the rest) read the `TRACELOOP_TRACE_CONTENT` env var at span-emit time. **Their default is `"true"`** — content is captured unless the env var is explicitly `"false"`. This means a comment alone does **not** flip the default; the template must set the env var in code, before the instrumentors run, to deliver the privacy-default-off promise:

```python
import os

# Default to NOT capturing prompt/completion content. Customers who want
# capture (after reviewing redaction options in references/redaction.md)
# can override by setting TRACELOOP_TRACE_CONTENT=true in their environment.
os.environ.setdefault("TRACELOOP_TRACE_CONTENT", "false")
```

`os.environ.setdefault` preserves an explicit operator override (`TRACELOOP_TRACE_CONTENT=true`) while defaulting to off when unset. Place this line at the top of the tracing module, before any `opentelemetry.instrumentation.*` import.

> **CRITICAL — do not propose a prompt-capturing template when sensitive data is in scope.** If the workflow's redaction step (step 3) returned "yes — sensitive data," route the customer to `redaction.md` *before* generating the snippet. Generating an opt-in-prompts template for a customer who said they handle PHI is a privacy footgun.

> **CRITICAL — a comment alone is not the privacy default.** Earlier versions of this template suggested a per-instrumentor env var (`OTEL_INSTRUMENTATION_LANGCHAIN_TRACE_PROMPTS=false`) in a comment. That env var **does not exist** in the OpenLLMetry instrumentors at `<=0.53.4`, and a comment instructing the customer to set it would not have changed the actual default. The fix is the `os.environ.setdefault(...)` line above, which makes the privacy default a code guarantee.

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
| Using `BatchSpanProcessor` but the runtime is now serverless (e.g. customer migrated to Lambda) | Propose switching to `SimpleSpanProcessor` (with `OTLPSpanExporter`) as a diff. Cite the serverless example. Wait for approval. |
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

- **Generating the default `BatchSpanProcessor` template for a Lambda agent.** Silent trace loss. Always check `runtime` first.
- **Double-appending `/v1/traces`** (e.g. `https://collector/v1/traces/v1/traces`). Broken endpoint. Normalize idempotently — check the suffix before appending.
- **Forgetting to render the resolved final endpoint to the user** before generating code. Opaque magic. Always show the resolved URL and wait for confirmation.
- **Capturing prompts/completions by default.** Privacy footgun. Default-disabled with opt-in, and route to `redaction.md` first if sensitive data is in scope.
- **Reading or echoing `MCD_DEFAULT_API_TOKEN` to confirm it's set.** Credential leak. Use presence-only (`bool(os.environ.get(...))`).
- **Auto-scaffolding a duplicate `mc.setup()` when one already exists.** Confusing telemetry, two agents in MC. Walk the decision matrix instead.
- **Editing `requirements.txt` / `pyproject.toml` / source files without explicit per-file approval.** Violates the SKILL.md guardrail. Propose every diff, wait for `yes` per file.
- **Forgetting that `mc.setup()` does not auto-inject auth headers when `span_processor=` is set.** With the default exporter, `mc.setup()` injects `MCD_DEFAULT_*` from env vars automatically. With a custom `span_processor` the customer constructs the `OTLPSpanExporter`, so the auth path must be made explicit at exporter-construction time. Match the customer's setup: (a) MC-hosted with `MCD_DEFAULT_*` env vars → pass `headers={"x-mcd-id": ..., "x-mcd-token": ...}` to `OTLPSpanExporter`; (b) MC-hosted with `OTEL_EXPORTER_OTLP_HEADERS` → omit `headers=` (the exporter reads the env var); (c) self-hosted collector → omit `headers=` (auth is at the collector). Symptom of getting it wrong: traces emit but never appear in MC because the collector rejects them as unauthenticated, **or** `init_tracing()` raises `KeyError` at startup because the template references `MCD_DEFAULT_*` that the customer isn't using.
