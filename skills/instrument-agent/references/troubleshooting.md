# Troubleshooting — diagnosing why traces aren't flowing

Tier 3 reference for the `instrument-agent` skill. Use this when verification has failed and traces aren't reaching the agent metadata endpoint. Walk the failure modes in priority order — order matters.

## 1. When to read this file

The workflow's verification step (step #10) calls `get_agent_metadata` and compares to the BEFORE snapshot. If the new agent doesn't appear (or appears but with no spans), branch here.

Walk the failure modes in priority order — the order matters because some are more common than others, and some have cheaper diagnostics. Resolve one cause at a time; don't change five things at once and re-test.

## 2. Diagnostic priority order

Given the symptom "traces aren't appearing in `get_agent_metadata`," check in this order:

| # | Failure mode | Cheap signal to look for first |
|---|---|---|
| 1 | Serverless `BatchSpanProcessor` foot-gun | Did `detect_libraries.py` flag `runtime: serverless`? Did the customer's `mc.setup()` use the `SimpleSpanProcessor` variant? |
| 2 | SDK init not running | Is `mc.setup()` actually called at agent startup? Or is it defined in a module that's never imported? |
| 3 | Missing credentials | MC-hosted collector path: are the selected auth env vars set in the runtime env (`MCD_DEFAULT_API_ID` / `MCD_DEFAULT_API_TOKEN` or `OTEL_EXPORTER_OTLP_HEADERS`)? |
| 4 | Wrong instrumentor versions | Did `pip install` succeed without resolver complaints? Are the installed versions compatible with the SDK? |
| 5 | Upstream pipeline not deployed | Did the customer's MC AO setup actually finish? Has anyone confirmed the collector endpoint accepts traffic? |

Most "no traces showing up" reports turn out to be #1 (serverless) or #2 (init not running). Walk through each in order.

## 3. Failure mode #1 — Serverless `BatchSpanProcessor` foot-gun

> **CRITICAL — incomplete or missing traces on Lambda are usually the `BatchSpanProcessor` foot-gun.** Lambda freezes the process between invocations; the default span processor is suspended before flushing, and the spans never leave the function. The fix is `SimpleSpanProcessor`.

This applies to any suspendable runtime — AWS Lambda, Google Cloud Functions, Vercel Functions, Cloudflare Workers, Azure Functions. Anywhere the process can be frozen mid-batch and resumed later (or never).

### Diagnostic

- Was `runtime: "serverless"` reported by `detect_libraries.py`?
- Does the customer's `mc.setup()` call include `span_processor=SimpleSpanProcessor(OTLPSpanExporter(endpoint=...))`?
- If serverless was detected but the customer used the default template (no `span_processor` kwarg), this is the bug.

### Fix

Propose a small diff switching to the serverless template from `setup-template.md`. Wait for per-file approval before applying.

## 4. Failure mode #2 — SDK init not running

The setup code exists in the codebase but is never executed at runtime. Common bug: `mc.setup()` lives in a module that nobody imports.

### Diagnostic

- Is `mc.setup()` defined in a module that's actually imported at agent startup? (Common bug: `mc.setup()` lives in `tracing.py` but `tracing.py` is never imported.)
- Is the import path correct? `import montecarlo_opentelemetry as mc` should not raise `ModuleNotFoundError`.
- Is `mc.setup()` called at the top level of the module (or in an `init_tracing()` function that's actually invoked)?
- If wrapped in a guard like `if otel_endpoint:`, is `OTEL_ENDPOINT` set? Print **presence** (NOT value) to confirm.

### Fix

- Add the missing import in the entry-point file.
- Or call `init_tracing()` explicitly at agent startup.
- Or set the missing env var.

Each fix is a per-file diff that needs approval.

> **IMPORTANT — never `print(os.environ["MCD_DEFAULT_API_TOKEN"])` to debug "is the value set."** Use `bool(os.environ.get(...))` or `"set" if os.environ.get(...) else "missing"`. Echoing token values into the agent's logs is a credential leak. Same for `OTEL_EXPORTER_OTLP_HEADERS`.

## 5. Failure mode #3 — Missing credentials (MC-hosted collector path only)

Only applies if the customer is using the MC-hosted collector (`https://integrations.getmontecarlo.com/otel`). Self-hosted collectors handle auth at the collector — skip this section in that branch.

### Diagnostic

- Is the customer using `MCD_DEFAULT_API_ID` / `MCD_DEFAULT_API_TOKEN`, and are both set in the runtime env (Lambda env vars, container env, dev shell, etc.)? Use presence-only checks.
- Or is the customer using `OTEL_EXPORTER_OTLP_HEADERS=x-mcd-id=...,x-mcd-token=...`, and is that env var set?
- Are the values current (not rotated)?
- **If the customer is on the serverless template (custom `span_processor`), is the auth path made explicit at exporter-construction time?** `mc.setup()` only auto-injects auth headers when it builds the default exporter; with a custom `span_processor` the customer constructs the `OTLPSpanExporter`, so the auth path must be picked explicitly. Three valid shapes: (a) `MCD_DEFAULT_*` env vars + `OTLPSpanExporter(endpoint=..., headers={"x-mcd-id": ..., "x-mcd-token": ...})`; (b) `OTEL_EXPORTER_OTLP_HEADERS` env var + `OTLPSpanExporter(endpoint=...)` with no explicit `headers=` (the exporter reads the env var); (c) self-hosted collector + `OTLPSpanExporter(endpoint=...)` with no headers (auth at the collector). If none of those match, env vars may exist but never reach the wire — symptom looks like missing credentials but the actual bug is the exporter is unauthenticated. See the SDK docs on PyPI (https://pypi.org/project/montecarlo-opentelemetry/) for the current auth-header guidance.

### Fix

- Set the missing auth env vars in the runtime (`MCD_DEFAULT_API_ID` / `MCD_DEFAULT_API_TOKEN`, or `OTEL_EXPORTER_OTLP_HEADERS` if the customer uses the standard OTel header path).
- For Lambda, that's the function's environment configuration (or, better, AWS Secrets Manager if the customer has a rotation policy).
- For containers, the deployment manifest.

> **NEVER include the actual token value in any diff, transcript, or log.** Walk the customer through setting the env var; don't echo it back.

## 6. Failure mode #4 — Wrong instrumentor versions

The instrumentor package version is incompatible with the SDK version, or with the AI library version it's instrumenting.

### Diagnostic

- What instrumentor version did `pip install` resolve? `pip show opentelemetry-instrumentation-<library>` or `pip freeze | grep instrumentation`.
- What does the live PyPI/SDK README compatibility table say? Run `python3 scripts/fetch_sdk_docs.py` and check the `supported_instrumentors` list — the `version_constraint` there is the current upper bound.
- Is the AI library itself a recent major version that breaks the instrumentor (e.g., LangChain 0.3 with an instrumentor pinned to LangChain 0.1.x)?

### Fix

- Re-run `pip install` with the current constraint from PyPI (via `python3 scripts/fetch_sdk_docs.py`).
- If the instrumentor doesn't yet support the AI library version, propose pinning the AI library to a compatible version, OR consult the instrumentor's PyPI page for upcoming compatibility.

> **CRITICAL — never edit `requirements.txt` / `pyproject.toml` / `Pipfile` without explicit per-file approval.** If a version pin needs to change, propose the diff and wait. See `SKILL.md`.

### Symptom: `TypeError: wrap_function_wrapper() got an unexpected keyword argument 'module'` at `mc.setup()` import

This is a transitive-dep collision between the OpenLLMetry instrumentors (langchain, openai, anthropic, bedrock, crewai, sagemaker, vertexai at `<=0.53.4`) and `wrapt` 2.x. The instrumentors call `wrap_function_wrapper(module=...)`; `wrapt` 2.x renamed that argument to `target=`. PyPI doesn't expose this transitive constraint, so a fresh `pip install opentelemetry-instrumentation-langchain` can resolve `wrapt` to 2.x and crash on first import.

**Fix:** pin `wrapt<2` alongside the OpenLLMetry instrumentor(s) in the customer's dependency file, then reinstall. For example:

```diff
 opentelemetry-instrumentation-langchain<=0.53.4
+wrapt<2
```

Then `pip install -r requirements.txt` (or the pyproject/Pipfile equivalent). The skill must propose this as a diff and wait for per-file approval — never edit dependency files autonomously.

## 7. Failure mode #5 — Upstream pipeline not deployed

The customer's MC AO infrastructure (collector, ingestion endpoint, workspace) isn't online or hasn't been provisioned. The agent code is correct but there's nothing on the other end.

### Symptoms

- All four other failure modes ruled out.
- The OTLP endpoint URL appears correct, env vars are set, code runs.
- `get_agent_metadata` still returns the old list with no new entries after running the agent multiple times.

### Diagnostic

- Has the customer actually completed their MC AO setup? The customer should have:
  - An MC AO workspace provisioned.
  - An ingestion endpoint configured (either MC-hosted or self-hosted collector reachable from the customer's runtime).
  - Outbound network access from the agent's runtime to the OTLP endpoint.
- Try `curl -v <otlp-endpoint>` from the agent's runtime — does the collector accept the connection?
- Does the customer see the workspace in `https://getmontecarlo.com/dashboard`?

### Fix

Customer needs to coordinate with their MC AO setup team. This is **out of scope for the instrument-agent skill** — it's a setup/infra concern. Point them at AO-product onboarding docs and exit cleanly. Don't try to fix infra from the skill.

## 8. Putting it together — the diagnostic loop

When the verification step shows the new agent isn't appearing:

1. Ask the user: "Is the agent runtime serverless (Lambda, Cloud Functions, Vercel, etc.)?" If yes, check #1 first.
2. Confirm `mc.setup()` is actually executed (#2).
3. If MC-hosted, confirm the env vars (#3).
4. Run `pip show` / `fetch_sdk_docs.py` to compare versions (#4).
5. If all four are clean, escalate to upstream pipeline (#5) — that's a setup-infra concern outside this skill's scope.

Walk through them one at a time, not all at once. Each step has a cheap diagnostic that either confirms or rules out the cause.

## Common mistakes

- **Jumping to credential issues first when the symptom is missing traces on Lambda** — usually it's the `SimpleSpanProcessor` foot-gun. Check runtime classification before chasing env vars.
- **Echoing env var values to "confirm" they're set** — credential leak. Presence-only checks (`bool(os.environ.get(...))`) only.
- **Editing `requirements.txt` to bump versions without per-file approval** — violates `SKILL.md` guardrail. Propose the diff; wait.
- **Trying to fix upstream pipeline issues from the skill** — out of scope. Escalate to the customer's AO setup team.
- **Polling `get_agent_metadata` while waiting for traces** — wasteful. Let the customer drive the cadence; don't loop on the metadata endpoint.
- **Changing multiple things at once and re-testing** — you lose the signal about which fix actually mattered. One change, one re-test.
