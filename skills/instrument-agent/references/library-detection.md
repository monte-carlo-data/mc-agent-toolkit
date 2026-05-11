# Library detection and runtime classification

This reference governs how the instrument-agent skill decides **which AI libraries to instrument** and **what runtime template to use**. It is the contract between `scripts/detect_libraries.py`, `scripts/fetch_sdk_docs.py`, and `scripts/instrumentor_map.json`. Read this file when adjudicating any decision involving detected libraries, unsupported candidates, or serverless classification.

## Inputs the skill works from

`scripts/detect_libraries.py` returns a single JSON document of this shape:

```json
{
  "detected": ["langchain", "openai"],
  "suggested_instrumentors": [
    {"library": "langchain", "package": "opentelemetry-instrumentation-langchain"}
  ],
  "unsupported": [
    {"library": "bedrock", "matched_dependencies": ["boto3"], "reason": "..."}
  ],
  "runtime": "serverless",
  "serverless_signals": ["serverless.yml", "lambda_handler"],
  "existing_setup": {"found": true, "files": ["src/tracing.py"]}
}
```

The static package-name→library detection map used by `detect_libraries.py` lives in `scripts/instrumentor_map.json`:

```json
{
  "supported_instrumentors": [
    {
      "library": "langchain",
      "package": "opentelemetry-instrumentation-langchain",
      "additional_pins": ["wrapt<2"],
      "covers_dependencies": ["langchain", "langchain-core", "langchain-community", "langgraph"]
    }
  ]
}
```

Field meanings:

- `library` / `package` — the canonical library name and the OpenTelemetry instrumentor package that covers it.
- `covers_dependencies` — the customer-facing dependency names that map to this library/instrumentor. `detect_libraries.py` uses this to translate `requirements.txt` / `pyproject.toml` / `Pipfile` entries into `detected[]` and `suggested_instrumentors[]`.
- `additional_pins` — transitive constraints required for the instrumentor to import cleanly. For example, several OpenLLMetry instrumentors pass `module=` to `wrap_function_wrapper`, which `wrapt` 2.x renamed to `target=` — so `wrapt<2` is required alongside the instrumentor. The skill must include these pins in the proposed dependency diff; without them, `pip install` resolves to incompatible versions and `mc.setup()` raises `TypeError` at import. PyPI doesn't expose transitive pins, so this field is the canonical source for them.

Version pins for the instrumentor packages themselves come from PyPI live via `fetch_sdk_docs.py`. They are **not** encoded in `instrumentor_map.json`.

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

## 2. How detection works

There is one supported tier: whatever the SDK currently supports per PyPI. The skill uses two complementary scripts:

### 2.1 `detect_libraries.py` — static dependency-file scan

`detect_libraries.py` reads the customer's `requirements.txt` / `pyproject.toml` / `Pipfile` and consults `instrumentor_map.json` (a static package-name→library map) to identify libraries it recognises. This works offline and is fast.

For any matched library, the script returns it under `detected[]` with the corresponding instrumentor package under `suggested_instrumentors[]`.

### 2.2 `fetch_sdk_docs.py` — live PyPI lookup

For libraries the static map doesn't know about — or to confirm the full current supported set — the user can run `fetch_sdk_docs.py`. It queries PyPI live and returns the currently-supported libraries plus their version pins. This is the authoritative source for what the SDK supports today.

### 2.3 Install decision

For each detected library:

1. **Is there an auto-instrumentor for this library on PyPI?** If yes, install it and wire it into `mc.setup(instrumentors=[...])`.
2. **Independently**, the customer can use `@trace_with_workflow` / `@trace_with_task` decorators on their orchestration and task functions, and can use `mc.create_llm_span` for manual LLM-call spans where useful. Decorator and manual-span availability does **not** depend on whether an auto-instrumentor exists for the underlying library — those are SDK-level affordances that work alongside (or in the absence of) any auto-instrumentor.

> **IMPORTANT**: Do not present manual spans / decorators as a *substitute* for auto-instrumentation. They serve different purposes. If an auto-instrumentor exists, install it. Decorators and `mc.create_llm_span` are additionally available for orchestration spans and bespoke LLM calls regardless.

## 3. Multi-library detection rules

`detect_libraries.py` returns multiple entries in `detected` when multiple libraries are present. Treat them as **additive** — install all matched instrumentors. A single `mc.setup()` call lists all of them:

```python
mc.setup(instrumentors=[
    LangchainInstrumentor(),
    OpenAIInstrumentor(),
])
```

> **IMPORTANT**: `suggested_instrumentors` deduplicates by package, so libraries that share an instrumentor (e.g. `langchain` and `langgraph` both ship via `opentelemetry-instrumentation-langchain`) appear **once** in the install set even though both still appear in `detected`. Drive dependency edits and `mc.setup(instrumentors=[...])` from the deduped list — never iterate `detected` to build the install set, or you'll wire and install the same instrumentor twice.

> **IMPORTANT**: When `detected: []` AND `unsupported: []` AND `runtime: "unknown"` — there are no AI libraries to instrument. Exit cleanly. Do **not** scaffold a `mc.setup()` for nothing. See section 7.

## 4. Ambiguous-multipurpose-SDK rule (boto3, etc.)

`boto3`, `botocore`, and `aioboto3` cover the entire AWS surface — they don't tell us whether the customer is calling Bedrock, SageMaker, S3, DynamoDB, or anything else. `detect_libraries.py` routes those matches to **`unsupported`**, never `detected`, with:

- `matched_dependencies`: the exact AWS SDK packages that triggered the match.
- `reason`: a string asking the user to confirm which AWS AI service (if any) they actually use.

> **NEVER**: Silently install `opentelemetry-instrumentation-bedrock` (or `-sagemaker`) just because `boto3` is in the dependency list. Always surface the candidate to the user and confirm "are you using Bedrock?" / "are you using SageMaker?" before adding the instrumentor or editing dependency files.

This pattern generalizes — any library that piggybacks on a multi-purpose SDK should follow the same ambiguous-bucket rule:

- `google-cloud-aiplatform` could be Vertex AI inference *or* Vertex AI Search.
- `azure-ai-*` covers many distinct Azure AI products.

For v1, only the AWS multi-purpose SDKs (`boto3` family) trigger this branch. The rule exists in this reference so future expansion follows the same shape.

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

- `runtime: "long_running"` — the default for any AI-library codebase without serverless signals. Use the standard batch-processor template.
- `runtime: "unknown"` — no clear signal either way. The skill must ask the user before scaffolding anything.

> **NEVER**: Auto-scaffold `mc.setup()` when `runtime: "unknown"`. Choosing the wrong span processor will silently drop traces (serverless) or add unnecessary memory pressure (long-running). Ask.

## 6. Existing-`mc.setup()` detection

If `existing_setup.found: true`, the customer already has Monte Carlo OpenTelemetry instrumentation in their codebase. The list under `existing_setup.files` shows where.

> **CRITICAL**: Do **not** scaffold a duplicate `mc.setup()`. Route to the existing-setup decision matrix in `setup-template.md` to walk through whether to update the existing call vs. leave it alone. A second `mc.setup()` will produce duplicate spans and confusing traces.

## 7. No-match exit

If `detected: []` AND `unsupported: []`, exit cleanly with this message:

> "No supported AI libraries were detected in your dependency files. The Monte Carlo OpenTelemetry SDK supports a set of libraries that's published on PyPI: https://pypi.org/project/montecarlo-opentelemetry/. You can run `scripts/fetch_sdk_docs.py` to see the current supported set. If you'd like to share your `requirements.txt` / `pyproject.toml` / `Pipfile`, I'll re-check."

If the user names a specific library that isn't in `detected[]`, run `fetch_sdk_docs.py` to confirm whether PyPI currently lists an instrumentor for it, then proceed per section 2.3.

> **NEVER**: Scaffold `mc.setup()` against an empty instrumentor list. An empty setup call is worse than no setup call — it implies instrumentation is in place when it isn't.

## Common mistakes

- **Installing the `bedrock` instrumentor when only `boto3` is detected.** Wrong — `boto3` is multi-purpose. That match goes to `unsupported`, and the skill must confirm with the user before installing.
- **Hardcoding a version constraint without running `fetch_sdk_docs.py`.** Wrong — PyPI live is the source of truth for instrumentor version pins. If PyPI is unreachable, surface the error rather than inventing a pin.
- **Treating `detected` and `unsupported` as the same bucket.** Wrong — `detected` is auto-installable; `unsupported` requires explicit user confirmation before any install or dependency-file edit.
- **Silently auto-scaffolding when `runtime: "unknown"` or when serverless signals are weak/partial.** Wrong — ask the user before picking a template. The wrong span processor drops traces or wastes memory.
- **Treating decorators / `create_llm_span` as a *substitute* for an auto-instrumentor.** Wrong — they are independent. If an auto-instrumentor exists on PyPI, install it. Decorators and manual spans are additionally available for orchestration and bespoke LLM calls.
- **Skipping `fetch_sdk_docs.py` for a library the static map doesn't know.** Wrong — `instrumentor_map.json` is a static detection convenience, not the canonical supported set. The supported set is whatever PyPI currently lists.
- **Scaffolding a duplicate `mc.setup()` when `existing_setup.found: true`.** Wrong — duplicate setup produces duplicate spans. Route to the existing-setup decision matrix in `setup-template.md`.
- **Scaffolding `mc.setup()` against an empty instrumentor list.** Wrong — exit cleanly with the no-match message instead.
- **Editing `requirements.txt` / `pyproject.toml` / `Pipfile` without explicit user approval.** Wrong — always propose the diff and wait for confirmation. See SKILL.md's CRITICAL no-silent-edit guardrail.
