# Library detection and runtime classification

This reference governs how the instrument-agent skill decides **which AI libraries to instrument** and **what runtime template to use**. The contract has two pieces: `scripts/detect_libraries.py` (a thin discovery layer over the customer's repo) and `scripts/fetch_sdk_docs.py` (the live PyPI lookup that names the SDK's currently-supported instrumentors). The matching between the two is the LLM's job — there is no static map in the skill.

## Inputs the skill works from

`scripts/detect_libraries.py` returns a single JSON document of this shape:

```json
{
  "dependencies": ["anthropic", "boto3", "fastapi", "langchain", "langgraph", "openai"],
  "runtime": "serverless",
  "serverless_signals": ["serverless.yml", "lambda_handler"],
  "existing_setup": {"found": true, "files": ["src/tracing.py"]}
}
```

Field meanings:

- `dependencies` — sorted list of normalized pip package names parsed from `requirements.txt` / `pyproject.toml` / `Pipfile`. Raw surface; the script does not classify which entries are AI-relevant. Everything the customer declared is here, lowercased.
- `runtime` — `serverless`, `long_running`, or `unknown`. `serverless` if any serverless signal is found. `long_running` if a dep manifest was found but no serverless signals. `unknown` when no dep manifest exists at all (so we can't reason about it).
- `serverless_signals` — what triggered the serverless classification (e.g. `lambda_handler`, `serverless.yml`, `mangum`).
- `existing_setup` — `{ found: bool, files: list[str] }` for any pre-existing `mc.setup()` call. `files` contains repo-relative paths.

`scripts/fetch_sdk_docs.py` returns the SDK's live supported-instrumentor list from PyPI:

```json
{
  "source": "pypi",
  "sdk": {"version": "...", "pypi_url": "https://pypi.org/project/montecarlo-opentelemetry/"},
  "supported_instrumentors": [
    {"library": "langchain", "package": "opentelemetry-instrumentation-langchain", "version_constraint": "<=0.53.4"},
    {"library": "openai", "package": "opentelemetry-instrumentation-openai", "version_constraint": "<=0.53.4"},
    {"library": "anthropic", "package": "opentelemetry-instrumentation-anthropic"}
  ]
}
```

That payload is the source of truth for what to install. If PyPI is unreachable, the script exits with `source: "error"` and a `guidance` field pointing at the PyPI page — surface that to the user rather than guessing.

## 1. The supported library set comes from PyPI

The Monte Carlo OpenTelemetry SDK supports a set of AI libraries that is published on PyPI: https://pypi.org/project/montecarlo-opentelemetry/. That page is the source of truth for what's currently supported — full stop.

`scripts/fetch_sdk_docs.py` queries PyPI live to retrieve that set and the per-instrumentor version pins. There is no offline fallback; on PyPI failure, `fetch_sdk_docs.py` exits with an error and the skill must surface that to the user rather than guessing.

A non-exhaustive subset of currently-supported libraries (examples — see PyPI for the current full list):

| Library | Instrumentor package |
|---|---|
| langchain (covers langgraph) | `opentelemetry-instrumentation-langchain` |
| openai | `opentelemetry-instrumentation-openai` |
| anthropic | `opentelemetry-instrumentation-anthropic` |
| crewai | `opentelemetry-instrumentation-crewai` |
| bedrock | `opentelemetry-instrumentation-bedrock` |
| sagemaker | `opentelemetry-instrumentation-sagemaker` |
| vertexai | `opentelemetry-instrumentation-vertexai` |

> **NEVER**: Hardcode a version constraint into a generated `requirements.txt` or `pyproject.toml` without first running `fetch_sdk_docs.py`. If PyPI is unreachable, surface the error to the user — don't invent a pin.

## 2. How matching works (LLM-driven)

There is one supported tier: whatever the SDK currently supports per PyPI. The matching flow:

1. Run `detect_libraries.py` against the target. It returns the raw `dependencies` list (every pip package the customer declared) plus `runtime`, `serverless_signals`, and `existing_setup`.
2. Run `fetch_sdk_docs.py` to get the SDK's `supported_instrumentors` list from PyPI.
3. **Match `dependencies` against `supported_instrumentors`.** The LLM does this — there's no static map. Walk the customer's deps and for each one decide whether an instrumentor covers it. Use the `library` slug in `supported_instrumentors` plus your knowledge of which pip packages each instrumentor wraps (e.g. `langchain-core` and `langchain-community` are part of the `langchain` instrumentor's surface; `langgraph` is also covered by `opentelemetry-instrumentation-langchain`).
4. **Ask the customer when a dep is ambiguous.** Some pip packages don't map cleanly to one instrumentor — see section 4. Always disambiguate explicitly rather than guessing.
5. **Use PyPI as the tiebreaker.** If you're unsure whether a particular dep maps to an instrumentor, the PyPI README (which `fetch_sdk_docs.py` parses) is canonical. If it doesn't appear there, there's no auto-instrumentor for it.

### Decorators and manual spans are independent of auto-instrumentors

`@trace_with_workflow`, `@trace_with_task`, and `mc.create_llm_span` are SDK-level affordances that work regardless of whether an auto-instrumentor exists for the underlying library. Do not present them as a *substitute* for auto-instrumentation — they serve different purposes:

- If an auto-instrumentor exists on PyPI for a customer's AI library, install it.
- Decorators and `mc.create_llm_span` are *additionally* available for orchestration spans and bespoke LLM calls.

## 3. Multi-library detection rules

When multiple AI libraries appear in `dependencies`, treat them as **additive** — install all matched instrumentors. A single `mc.setup()` call lists all of them:

```python
mc.setup(instrumentors=[
    LangchainInstrumentor(),
    OpenAIInstrumentor(),
])
```

> **IMPORTANT**: Multiple libraries can share one instrumentor package (e.g. `langchain` and `langgraph` both ship via `opentelemetry-instrumentation-langchain`). Deduplicate by package when building the install set and the `instrumentors=[...]` list — installing or instantiating the same instrumentor twice is a bug.

> **IMPORTANT**: When `dependencies` contains no AI libraries from the PyPI supported list AND `runtime: "unknown"` — there are no AI libraries to instrument. Exit cleanly. Do **not** scaffold a `mc.setup()` for nothing. See section 7.

## 4. Ambiguous-multipurpose-SDK rule (boto3, etc.)

Some pip packages cover a broad surface and don't tell us which AI service (if any) the customer is using:

- `boto3`, `botocore`, `aioboto3` — cover the entire AWS surface. Could mean Bedrock, SageMaker, or just S3 / DynamoDB / SQS / anything else.
- `google-cloud-aiplatform` — could be Vertex AI inference or Vertex AI Search.
- `azure-ai-*` — covers many distinct Azure AI products.

`detect_libraries.py` doesn't single these out — they appear in `dependencies` like any other package. **The LLM handles the disambiguation by asking the customer.** When `boto3` is present, ask "are you calling Bedrock or SageMaker through boto3, or is it just generic AWS work?". Don't install `opentelemetry-instrumentation-bedrock` until the customer confirms Bedrock usage.

> **NEVER**: Silently install `opentelemetry-instrumentation-bedrock` (or `-sagemaker`) just because `boto3` is in the dependency list. Always ask first.

## 5. Serverless framework detection

`detect_libraries.py` sets `runtime: "serverless"` when **ANY** of the following is present in the customer's project:

**Files**

- `serverless.yml`, `serverless.yaml` — Serverless Framework
- `template.yaml`, `template.yml` — AWS SAM
- `vercel.json` — Vercel
- `netlify.toml` — Netlify
- `wrangler.toml` — Cloudflare Workers
- `zappa_settings.json` — Zappa
- `modal.toml` — Modal

**Dependencies**

- `aws-lambda-powertools`, `mangum`, `chalice`, `zappa`
- `aws-cdk-lib`, `aws-sam-cli`
- `modal`, `sst`

**Code patterns**

- `def lambda_handler(`
- `from chalice import Chalice`
- `from mangum import Mangum`
- `app = Chalice(`

The matched signal name (file name or pattern) appears in `serverless_signals` in the JSON output. Use that list to explain the runtime classification when the user asks "why did you pick the serverless template?".

> **CRITICAL**: When `runtime: "serverless"`, the skill must use the **`SimpleSpanProcessor`** template — see `setup-template.md`. Without it, traces are silently dropped on Lambda when the batch processor is suspended before flushing the queue. This foot-gun is also documented in `troubleshooting.md`.

### Ask the user when serverless signals are ambiguous

Detection is intentionally broad — a single signal is enough to flip `runtime` to `serverless`. That's the right call when the project is clearly Lambda/Vercel/etc., but it's wrong for codebases where the serverless framework applies to only part of the project:

- A monorepo where `template.yaml` lives under one subdirectory and the rest of the code is a long-running service.
- A repo with `serverless.yml` for an auxiliary handler, but the AI code runs in a separate long-running worker.
- A single weak signal (e.g., `mangum` in deps) without any handler entry point or framework config file.

When the picture is borderline — one signal, or signals that don't obviously cover the code where the AI libraries are used — ask the user before committing to the serverless template. Show them `serverless_signals` and confirm whether the AI code actually runs in that serverless context. If only part of the codebase is serverless, the user may need different templates for different entry points.

### Other runtime values

- `runtime: "long_running"` — at least one dependency manifest exists and no serverless signal was observed. Use the standard batch-processor template.
- `runtime: "unknown"` — no dependency manifest found in the target. Ask the user where the agent code lives before scaffolding anything.

> **NEVER**: Auto-scaffold `mc.setup()` when `runtime: "unknown"`. Choosing the wrong span processor will silently drop traces (serverless) or add unnecessary memory pressure (long-running). Ask.

## 6. Existing-`mc.setup()` detection

If `existing_setup.found: true`, the customer already has Monte Carlo OpenTelemetry instrumentation in their codebase. The list under `existing_setup.files` shows where.

> **CRITICAL**: Do **not** scaffold a duplicate `mc.setup()`. Route to the existing-setup decision matrix in `setup-template.md` to walk through whether to update the existing call vs. leave it alone. A second `mc.setup()` will produce duplicate spans and confusing traces.

## 7. No-match exit

If after matching `dependencies` against `fetch_sdk_docs.py`'s `supported_instrumentors` you find no AI library that the SDK supports, exit cleanly with this message:

> "No supported AI libraries were detected in your dependency files. The Monte Carlo OpenTelemetry SDK supports a set of libraries that's published on PyPI: https://pypi.org/project/montecarlo-opentelemetry/. You can run `scripts/fetch_sdk_docs.py` to see the current supported set. If you'd like to share your `requirements.txt` / `pyproject.toml` / `Pipfile`, I'll re-check."

If the user names a specific library that isn't in `dependencies`, run `fetch_sdk_docs.py` to confirm whether PyPI currently lists an instrumentor for it, then proceed per section 2.

> **NEVER**: Scaffold `mc.setup()` against an empty instrumentor list unless the customer is manually reporting every LLM call with `mc.create_llm_span`. An empty setup call without manual spans is worse than no setup call — it implies instrumentation is in place when it isn't.

## 8. Version pinning

For each instrumentor you propose installing, take the `version_constraint` from `fetch_sdk_docs.py`'s `supported_instrumentors[*]` entry. That value is parsed live from the PyPI README's `pip install` lines (e.g. `<=0.53.4`). Apply it directly in the customer's dependency-file diff — never strip it.

Some instrumentor versions have transitive compatibility constraints that aren't expressed in PyPI metadata. The most common one in the current SDK release is the `wrapt<2` requirement for OpenLLMetry instrumentors (they pass `module=` to `wrap_function_wrapper`, which `wrapt` 2.x renamed to `target=`). The skill surfaces these as **symptom-driven fixes** in `troubleshooting.md` rather than baking them into every install diff — if a customer hits the symptom, the troubleshooting reference names the pin.

## Common mistakes

- **Installing the `bedrock` instrumentor when only `boto3` is detected.** Wrong — `boto3` is multi-purpose. Always ask the customer whether they're actually using Bedrock before installing.
- **Hardcoding a version constraint without running `fetch_sdk_docs.py`.** Wrong — PyPI live is the source of truth for instrumentor version pins. If PyPI is unreachable, surface the error rather than inventing a pin.
- **Skipping the disambiguation prompt for ambiguous deps.** Wrong — `boto3`, `google-cloud-aiplatform`, `azure-ai-*` all need explicit user confirmation before installing any instrumentor.
- **Silently auto-scaffolding when `runtime: "unknown"` or when serverless signals are weak/partial.** Wrong — ask the user before picking a template. The wrong span processor drops traces or wastes memory.
- **Treating decorators / `create_llm_span` as a *substitute* for an auto-instrumentor.** Wrong — they are independent. If an auto-instrumentor exists on PyPI, install it. Decorators and manual spans are additionally available for orchestration and bespoke LLM calls.
- **Trusting a stale memory of the supported set instead of `fetch_sdk_docs.py`.** Wrong — the supported set is whatever PyPI currently lists. Re-fetch.
- **Scaffolding a duplicate `mc.setup()` when `existing_setup.found: true`.** Wrong — duplicate setup produces duplicate spans. Route to the existing-setup decision matrix in `setup-template.md`.
- **Scaffolding `mc.setup()` against an empty instrumentor list with no manual reporting.** Wrong — empty `instrumentors=[]` is only useful when every LLM call is manually reported with `mc.create_llm_span`. Otherwise exit cleanly with the no-match message.
- **Editing `requirements.txt` / `pyproject.toml` / `Pipfile` without explicit user approval.** Wrong — always propose the diff and wait for confirmation. See SKILL.md's CRITICAL no-silent-edit guardrail.
- **Forgetting the `wrapt<2` pin and getting a `TypeError` at `mc.setup()` import.** Surface the symptom path in `troubleshooting.md` if the customer hits it — the fix is to pin `wrapt<2` alongside the OpenLLMetry instrumentors.
