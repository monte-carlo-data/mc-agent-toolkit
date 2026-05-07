# Workflow

End-to-end procedure for instrumenting a customer's Python AI agent with Monte Carlo Agent Observability. Read top-to-bottom — each step gates the next. The output of this workflow is traces that the `monitoring-advisor` skill later consumes.

> **CRITICAL — never modify any file without explicit user approval.** This skill proposes diffs; the user accepts them. That includes dependency files (`requirements.txt`, `pyproject.toml`, `Pipfile`), application source (where `mc.setup()` and decorators land), and anything else on disk. If the user says "go ahead and apply it," that's approval for that specific diff and nothing more. Ask again for the next file.

The workflow has eleven steps, in order:

1. Detect libraries, runtime, and existing setup
2. Ask about the OTel collector (MC-hosted vs. self-hosted)
3. Ask about sensitive data (gates redaction + `mc.setup()` template)
4. Snapshot existing agents via `get_agent_metadata` (BEFORE changes)
5. Resolve and confirm the final OTLP endpoint
6. Propose dependency-file edits
7. Propose `mc.setup()` insertion
8. Propose `@trace_with_workflow` / `@trace_with_task` decorator diffs
9. Confirm env vars (presence-only)
10. Verify via `get_agent_metadata` (AFTER user runs the agent)
11. On failure, branch to `troubleshooting.md`

---

## Step 1 — Detect libraries, runtime, and existing setup

Run the detection helper against the customer's agent code:

```bash
python3 scripts/detect_libraries.py <target_path>
```

It prints a JSON object with the following fields:

- `detected` — list of PRD core libraries found in the target tree
- `suggested_instrumentors` — the OTel instrumentor packages to install for those libraries
- `unsupported` — ambiguous matches that need user disambiguation (e.g. `boto3` could be Bedrock or SageMaker, or just generic AWS)
- `runtime` — `serverless`, `long_running`, or `unknown`
- `serverless_signals` — what triggered a serverless classification (e.g. `lambda_handler`, `serverless.yml`, `Mangum`)
- `existing_setup` — `{ found: bool, path: str | null, snippet: str | null }` for any pre-existing `mc.setup()` call

Parse this output and branch:

- **`existing_setup.found` is `true`** — do not propose a fresh `mc.setup()`. Point the reader at the existing-setup decision matrix in `setup-template.md` to decide whether to keep, reconfigure, or replace the call. Then continue with the rest of the workflow (the user may still need decorator and dependency changes).
- **`runtime: "unknown"` and `detected: []`** — exit cleanly. No PRD core libraries are present, so there's nothing to instrument. Tell the user: "I didn't find any of the supported AI libraries (`openai`, `anthropic`, `langchain`, `llama_index`, `bedrock`, `vertexai`, `crewai`, `dspy`) in the target. Confirm the agent code is actually in this path, then re-run." Do not scaffold anything.
- **Anything else** — continue to step 2 with the detection output in hand.

If the user wants to consider libraries beyond what `detect_libraries.py` knows about, run `python3 scripts/fetch_sdk_docs.py` to pull the live `supported_instrumentors` list from PyPI (it falls back to a local snapshot if PyPI is unreachable). This is informational only — proposed installs still wait until step 6.

**Next:** with detection settled, ask about the collector.

---

## Step 2 — Ask about the OTel collector

Ask the user verbatim:

> "Are you using your own OTel collector or the MC-hosted one?"

Capture the answer — it gates step 5 (endpoint normalization) and step 9 (env-var checks).

- **MC-hosted** — base URL is `https://integrations.getmontecarlo.com/otel`. Step 9 will require `MCD_DEFAULT_API_ID` and `MCD_DEFAULT_API_TOKEN` to be present in the runtime environment.
- **Self-hosted** — ask: "What's the base URL for your collector?" Capture it as the customer's collector base URL. Step 9 will skip MC credential checks because auth happens at the customer's collector.

Don't try to infer the collector from anything in the codebase — just ask.

**Next:** ask about sensitive data so step 3 picks the right `mc.setup()` template.

---

## Step 3 — Ask about sensitive data

Ask the user verbatim:

> "Will any prompts or completions in this agent contain sensitive data (PII, PHI, credentials, customer content)?"

This is a non-optional gating decision that runs **before** any `mc.setup()` is generated.

- **Yes** — route the user to `redaction.md` and walk through the three V1 redaction pathways. Use the prompts-disabled `mc.setup()` template in step 7. Do not generate the default template in this branch.
- **No** — use the default `mc.setup()` template in step 7. The default still leans prompts-disabled with an opt-in comment per `setup-template.md`; the customer can flip it on later if they decide content capture is safe.

**Next:** snapshot existing agents before any code changes land.

---

## Step 4 — Snapshot existing agents via `get_agent_metadata` (BEFORE changes)

This must run **before** step 6, 7, or 8 propose any diffs. The snapshot is what step 10 compares against to prove the new instrumentation actually produced traces.

1. Call MC MCP `testConnection` first.
   - If it fails, point the user at https://docs.getmontecarlo.com/docs/mcp-server and **exit cleanly without proposing any edits.** Without MCP, step 10's verification can't run, and shipping instrumentation that can't be verified is worse than not shipping it.
2. With MCP confirmed, call `get_agent_metadata`. Save the list of `(agent_name, mcon)` pairs.
3. Hold onto the snapshot — step 10 diffs against it.

See `verify-traces.md` for the full before/after flow and what the response looks like.

**Next:** resolve the OTLP endpoint URL and get user confirmation before generating any code.

---

## Step 5 — Resolve and display the final OTLP endpoint

The endpoint is whatever base URL came out of step 2, normalized to end in `/v1/traces`.

- If the user's URL already ends in `/v1/traces`, use it as-is.
- Otherwise, append `/v1/traces`.
- **Never double-append.** A URL that already ends in `/v1/traces` must not become `…/v1/traces/v1/traces`.

Examples:

| Input                                              | Resolved                                                       |
| -------------------------------------------------- | -------------------------------------------------------------- |
| `https://integrations.getmontecarlo.com/otel`      | `https://integrations.getmontecarlo.com/otel/v1/traces`        |
| `https://integrations.getmontecarlo.com/otel/v1/traces` | `https://integrations.getmontecarlo.com/otel/v1/traces`    |
| `https://collector.acme.internal:4318`             | `https://collector.acme.internal:4318/v1/traces`               |

Render the resolved final URL to the user and ask for confirmation before generating any code. See `setup-template.md` for the full normalization rules.

**Next:** propose dependency edits using the install set from step 1.

---

## Step 6 — Propose dependency-file edits

Determine the install set from `detect_libraries.py`'s `suggested_instrumentors` (or live-fetch via `fetch_sdk_docs.py` if the user wants libraries beyond the default set). Always include the MC SDK package itself.

Propose the additions as a unified diff against the customer's actual dependency file — `requirements.txt`, `pyproject.toml`, or `Pipfile`. Wait for **explicit per-file approval** before any edit lands.

> **CRITICAL — never edit dependency files autonomously.** Even if the change looks trivial. The user reviews and accepts each diff. See `library-detection.md` for the install rules.

If `unsupported` from step 1 is non-empty (e.g. `boto3` matched but the agent could be using Bedrock, SageMaker, or just S3), surface the candidates and ask the user before deciding what to install. Don't guess.

**Next:** propose the `mc.setup()` insertion.

---

## Step 7 — Propose `mc.setup()` insertion as a diff

Use the runtime classification from step 1 to pick the template:

- **`runtime: "serverless"`** — use the serverless template, which uses `SimpleSpanProcessor` so spans flush before the Lambda freeze. See `setup-template.md` and the linked `saas-serverless` example. The serverless `BatchSpanProcessor` foot-gun is covered in `troubleshooting.md`.
- **`runtime: "long_running"`** — use the default template (the linked `ai-agent` example). `BatchSpanProcessor` is appropriate here.
- **`runtime: "unknown"`** — by step 7 you should never be here; step 1 would have exited cleanly. If you somehow are, ask the user to classify before proposing a template.

If step 3 was "yes" (sensitive data), use the prompts-disabled variant of the chosen template. If step 3 was "no", use the default (still prompts-disabled with an opt-in comment).

If step 1 reported `existing_setup.found: true`, don't propose a fresh insertion — apply the decision from `setup-template.md`'s existing-setup matrix instead.

Propose the change as a diff. Wait for explicit approval before writing the file.

**Next:** propose decorator placement.

---

## Step 8 — Propose `@trace_with_workflow` and `@trace_with_task` decorator diffs

Identify two kinds of functions in the agent code:

- **Orchestration entry points** — the function the customer calls to run the agent end-to-end. Decorate with `@trace_with_workflow`.
- **LLM-calling task functions** — the discrete units of work the workflow calls (a single LLM call, a tool invocation, a retrieval step). Decorate each with `@trace_with_task`.

> **CRITICAL — never propose `@trace_with_tags`.** Only `@trace_with_workflow` and `@trace_with_task` are part of V1. `@trace_with_tags` exists in the SDK but is not in scope; using it produces traces that `monitoring-advisor` cannot consume.

Propose each decorator addition as a separate diff. Wait for **explicit per-diff approval**. See `decorator-placement.md` for placement guidance and the canonical example.

**Next:** confirm env vars are set (or skip, depending on step 2).

---

## Step 9 — Confirm env vars

Branches on the answer from step 2:

- **MC-hosted collector** — confirm `MCD_DEFAULT_API_ID` and `MCD_DEFAULT_API_TOKEN` are set in the customer's runtime environment. Use **presence-only checks**, e.g.:

  ```python
  bool(os.environ.get("MCD_DEFAULT_API_TOKEN"))
  ```

  > **CRITICAL — never read or echo the credential value.** Presence (`bool(...)`) only. If a check needs to land in a logging or diagnostic file, mask everything but `True`/`False`. See `setup-template.md` on credential safety.

- **Self-hosted collector** — skip this step entirely. Auth is handled at the customer's collector; the MC SDK doesn't need `MCD_*` env vars in this branch. Don't ask the user to set them, and don't propose a check.

**Next:** hand back to the user to run their agent, then verify.

---

## Step 10 — Verify via `get_agent_metadata` (AFTER user runs the instrumented agent)

Ask the user to run the instrumented agent against their environment so it produces at least one workflow trace. Then call `get_agent_metadata` again and diff against the snapshot from step 4.

Expected outcomes:

- A new entry exists with `agent_name` matching whatever the customer passed to `mc.setup(agent_name=...)`, and a new MCON.
- If the same `agent_name` already existed in the snapshot (e.g. a dev/prod twin), the new MCON should still be different — confirm that.
- If nothing new appears, go to step 11.

See `verify-traces.md` for the full diffing logic and edge cases.

**Next:** if verification passed, the workflow is done. If not, troubleshoot.

---

## Step 11 — On failure, branch to `troubleshooting.md`

The four PRD failure modes, in roughly the order to check:

1. **SDK init not running** — `mc.setup()` is in the file but the import path or entry point isn't actually loading it at runtime.
2. **Wrong instrumentor versions** — the installed OTel instrumentors are incompatible with the SDK or with each other.
3. **Missing credentials** — `MCD_DEFAULT_API_ID` / `MCD_DEFAULT_API_TOKEN` not present in the runtime (MC-hosted branch only).
4. **Upstream pipeline not actually deployed** — the agent code with `mc.setup()` exists in the repo but the deployed runtime is still the old build.

`troubleshooting.md` also covers the **serverless `SimpleSpanProcessor` foot-gun** — Lambda freezing the process before `BatchSpanProcessor` flushes, producing partial or missing traces. If the runtime is serverless and traces look incomplete (rather than absent), that's the first thing to check.

Walk the customer through whichever branch matches their symptoms. Once a fix is in place, re-run step 10.
