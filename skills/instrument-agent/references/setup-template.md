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

    # By default this template DOES NOT capture prompt/completion content. To
    # capture prompts (after reviewing redaction options in references/redaction.md),
    # set OTEL_INSTRUMENTATION_LANGCHAIN_TRACE_PROMPTS=true (or the equivalent
    # env var for your instrumentor).
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

    # mc.setup() only auto-injects MCD_DEFAULT_* headers when it builds the
    # default exporter. With a custom span_processor we build the exporter
    # ourselves, so we must pass auth headers explicitly. Self-hosted
    # collectors can omit `headers=...` — auth is handled at the collector.
    mcd_headers = {
        "x-mcd-id": os.environ["MCD_DEFAULT_API_ID"],
        "x-mcd-token": os.environ["MCD_DEFAULT_API_TOKEN"],
    }

    # SimpleSpanProcessor flushes each span before the runtime can suspend the
    # process. BatchSpanProcessor would queue spans and lose them at freeze.
    exporter = OTLPSpanExporter(endpoint=http_otel_endpoint, headers=mcd_headers)
    simple_span_processor = SimpleSpanProcessor(exporter)

    # By default this template DOES NOT capture prompt/completion content. To
    # capture prompts (after reviewing redaction options in references/redaction.md),
    # set OTEL_INSTRUMENTATION_LANGCHAIN_TRACE_PROMPTS=true (or the equivalent
    # env var for your instrumentor).
    mc.setup(
        agent_name=AGENT_NAME,
        otlp_endpoint=http_otel_endpoint,  # required by signature; ignored when span_processor is set
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

## 3. Default snippet — prompts disabled

The default template the skill proposes has prompt/completion capture **disabled**. Customers who want to capture prompts must opt in explicitly.

**Why default-off:** prompts and completions can contain PII, PHI, credentials, and other sensitive data. Default-on capture means a customer who runs the happy path is sending raw inputs to MC's OTLP collector before they ever read `redaction.md`. Default-off is the safe default; opt-in is the explicit choice.

The exact mechanism for disabling depends on the instrumentor — most accept env vars like `OTEL_INSTRUMENTATION_LANGCHAIN_TRACE_PROMPTS=false` or constructor arguments. Document the canonical mechanism for the customer's instrumentor as a comment in the template:

```python
# By default this template DOES NOT capture prompt/completion content. To
# capture prompts (after reviewing redaction options in references/redaction.md),
# set OTEL_INSTRUMENTATION_LANGCHAIN_TRACE_PROMPTS=true (or the equivalent
# env var for your instrumentor).
```

> **CRITICAL — do not propose a prompt-capturing template when sensitive data is in scope.** If the workflow's redaction step (step 3) returned "yes — sensitive data," route the customer to `redaction.md` *before* generating the snippet. Generating an opt-in-prompts template for a customer who said they handle PHI is a privacy footgun.

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
- **Building `OTLPSpanExporter` for a custom `span_processor` without passing `MCD_DEFAULT_*` headers explicitly.** `mc.setup()` only auto-injects auth headers when it constructs the default exporter; with a custom `span_processor` you build the exporter, so the headers are your responsibility. Symptom: traces emit but never appear in MC because the collector rejects them as unauthenticated. Fix: pass `headers={"x-mcd-id": ..., "x-mcd-token": ...}` to `OTLPSpanExporter`, or set `OTEL_EXPORTER_OTLP_HEADERS` and let the exporter pick it up. (Self-hosted collectors handle auth at the collector and don't need this.)
