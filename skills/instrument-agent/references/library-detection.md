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

The fallback table that drives `detected` / `suggested_instrumentors` lives in `scripts/instrumentor_map.json`:

```json
{
  "snapshot_date": "2026-05-06",
  "supported_instrumentors": [
    {
      "library": "langchain",
      "package": "opentelemetry-instrumentation-langchain",
      "version_constraint": "<=0.53.4",
      "additional_pins": ["wrapt<2"],
      "covers_dependencies": ["langchain", "langchain-core", "langchain-community", "langgraph"]
    }
  ]
}
```

Field meanings:

- `version_constraint` — pin for the instrumentor package itself (e.g. `<=0.53.4`).
- `additional_pins` — transitive constraints required for the pinned instrumentor version to import cleanly. The OpenLLMetry instrumentors at `<=0.53.4` pass `module=` to `wrap_function_wrapper`, which `wrapt` 2.x renamed to `target=` — so `wrapt<2` is required alongside the instrumentor. The skill must include these pins in the proposed dependency diff; without them, `pip install` resolves to incompatible versions and `mc.setup()` raises `TypeError` at import.

This schema is shared with `fetch_sdk_docs.py` — treat any field rename as a breaking change to both scripts.

> **CRITICAL**: `version_constraint` in `instrumentor_map.json` is a **stale fallback**, not the source of truth. PyPI live results from `fetch_sdk_docs.py` always win. When the snapshot value is shown to the user, it must be labeled `STALE` so the user understands they should re-fetch.

> **IMPORTANT**: `additional_pins` lives in the snapshot only. The PyPI README does not encode transitive constraints, so live-fetch results don't carry them. When using a live result, fall back to the snapshot's `additional_pins` for the same library — otherwise the proposed deps will install but fail at runtime.

## 1. PRD core library list (the contract)

The skill commits to instrumenting these eight libraries with first-class fallback templates. `detect_libraries.py`, `fetch_sdk_docs.py`, and `instrumentor_map.json` all align on this list. Treat it as a stable contract.

| Library | Instrumentor package | PyPI |
|---|---|---|
| langchain | `opentelemetry-instrumentation-langchain` | https://pypi.org/project/opentelemetry-instrumentation-langchain/ |
| langgraph | `opentelemetry-instrumentation-langchain` (shared) | (no separate package — langchain instrumentor covers it) |
| openai | `opentelemetry-instrumentation-openai` | https://pypi.org/project/opentelemetry-instrumentation-openai/ |
| anthropic | `opentelemetry-instrumentation-anthropic` | https://pypi.org/project/opentelemetry-instrumentation-anthropic/ |
| crewai | `opentelemetry-instrumentation-crewai` | https://pypi.org/project/opentelemetry-instrumentation-crewai/ |
| bedrock | `opentelemetry-instrumentation-bedrock` | https://pypi.org/project/opentelemetry-instrumentation-bedrock/ |
| sagemaker | `opentelemetry-instrumentation-sagemaker` | https://pypi.org/project/opentelemetry-instrumentation-sagemaker/ |
| vertexai | `opentelemetry-instrumentation-vertexai` | https://pypi.org/project/opentelemetry-instrumentation-vertexai/ |

> **CRITICAL**: Version constraints come from PyPI live (`fetch_sdk_docs.py`) — *not* from this file or the snapshot. The snapshot's `version_constraint` is a stale fallback shown with a `STALE` warning when used. Always prefer the PyPI live result.

> **NEVER**: Hardcode a version constraint into a generated `requirements.txt` or `pyproject.toml` from the snapshot without first attempting a PyPI live fetch. If the live fetch fails, surface the snapshot value with the explicit `STALE (snapshot_date=YYYY-MM-DD)` annotation so the user can decide whether to trust it.

## 2. Two-tier supported library handling

There are two tiers of "supported" libraries, and they take different code paths.

### Tier A — Core (the PRD 8)

Ship with fallback templates baked into `instrumentor_map.json`. The skill can install the package and propose a decorator block **without a network call**. These are the only libraries for which the skill auto-scaffolds.

### Tier B — Live-fetch-required

Any other SDK-supported instrumentor not in the PRD 8. Examples (non-exhaustive): `agno`, `chromadb`, `cohere`, `groq`, `haystack`, `llamaindex`, `mcp`, `milvus`, `mistralai`, `ollama`, `pinecone`, `qdrant`, `together`, `transformers`, `voyageai`, `watsonx`, `weaviate`, `writer`.

The skill can detect these **only via the live PyPI fetch** (`fetch_sdk_docs.py`). When detected, surface them as **"supported but no fallback template"** and instruct the user to:

1. `pip install opentelemetry-instrumentation-<library>`
2. Consult PyPI for the current version constraint.
3. Use the manual `create_llm_span` pathway (see `redaction.md`) — this is the V1 manual route.

> **IMPORTANT**: Do **not** auto-scaffold a decorator for Tier B libraries. The skill has no fallback template for them, and guessing will produce broken code. Manual `create_llm_span` is the V1 pathway.

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

> **CRITICAL**: When `runtime: "serverless"`, the skill must use the **`SimpleSpanProcessor`** template — see `setup-template.md` and the cited `saas-serverless` production example. Without it, traces are silently dropped on Lambda when the batch processor is suspended before flushing the queue. This foot-gun is also documented in `troubleshooting.md`.

### Other runtime values

- `runtime: "long_running"` — the default for any AI-library codebase without serverless signals. Use the standard batch-processor template.
- `runtime: "unknown"` — no clear signal either way. The skill must ask the user before scaffolding anything.

> **NEVER**: Auto-scaffold `mc.setup()` when `runtime: "unknown"`. Choosing the wrong span processor will silently drop traces (serverless) or add unnecessary memory pressure (long-running). Ask.

## 6. Existing-`mc.setup()` detection

If `existing_setup.found: true`, the customer already has Monte Carlo OpenTelemetry instrumentation in their codebase. The list under `existing_setup.files` shows where.

> **CRITICAL**: Do **not** scaffold a duplicate `mc.setup()`. Route to the existing-setup decision matrix in `setup-template.md` to walk through whether to update the existing call vs. leave it alone. A second `mc.setup()` will produce duplicate spans and confusing traces.

## 7. No-match exit

If `detected: []` AND `unsupported: []`, exit cleanly with one of these responses:

- **No hint from the user**:

  > "No supported AI libraries found. The PRD core libraries are: langchain, langgraph, openai, anthropic, crewai, bedrock, sagemaker, vertexai. If you're using one of these but `detect_libraries.py` didn't pick it up, share your `requirements.txt` / `pyproject.toml` / `Pipfile` and I'll diagnose."

- **The user mentioned a non-PRD library** (e.g., LlamaIndex):

  > Point at the live-fetch-required path: `pip install opentelemetry-instrumentation-<library>`, plus the manual `create_llm_span` pathway from `redaction.md`.

> **NEVER**: Scaffold `mc.setup()` against an empty instrumentor list. An empty setup call is worse than no setup call — it implies instrumentation is in place when it isn't.

## Common mistakes

- **Installing the `bedrock` instrumentor when only `boto3` is detected.** Wrong — `boto3` is multi-purpose. That match goes to `unsupported`, and the skill must confirm with the user before installing.
- **Hardcoding the version constraint from `instrumentor_map.json` instead of preferring PyPI live.** Wrong — the snapshot is a stale fallback. PyPI is the source of truth at runtime; the snapshot must be labeled `STALE` when used.
- **Treating `detected` and `unsupported` as the same bucket.** Wrong — `detected` is auto-installable; `unsupported` requires explicit user confirmation before any install or dependency-file edit.
- **Silently auto-scaffolding when `runtime: "unknown"`.** Wrong — picking the wrong span processor drops traces or wastes memory. Ask the user to disambiguate.
- **Auto-scaffolding a decorator for a Tier B library** (e.g., `llamaindex`, `cohere`). Wrong — there is no fallback template for Tier B in v1. Direct the user to `pip install opentelemetry-instrumentation-<library>` and the manual `create_llm_span` pathway in `redaction.md`.
- **Scaffolding a duplicate `mc.setup()` when `existing_setup.found: true`.** Wrong — duplicate setup produces duplicate spans. Route to the existing-setup decision matrix in `setup-template.md`.
- **Scaffolding `mc.setup()` against an empty instrumentor list.** Wrong — exit cleanly with the no-match message instead.
- **Editing `requirements.txt` / `pyproject.toml` / `Pipfile` without explicit user approval.** Wrong — always propose the diff and wait for confirmation. See SKILL.md's CRITICAL no-silent-edit guardrail.
