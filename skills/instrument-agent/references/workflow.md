# Workflow

End-to-end procedure for instrumenting a customer's Python AI agent with Monte Carlo Agent Observability. Read top-to-bottom — each step gates the next. The output of this workflow is traces that the `monitoring-advisor` skill later consumes.

> **CRITICAL — never modify any file without explicit user approval.** This skill proposes diffs; the user accepts them. That includes dependency files (`requirements.txt`, `pyproject.toml`, `Pipfile`), application source (where `mc.setup()` and decorators land), and anything else on disk. If the user says "go ahead and apply it," that's approval for that specific diff and nothing more. Ask again for the next file.

The workflow has a pre-flight check followed by eleven steps, in order:

0. Pre-flight — confirm MCP connectivity via `test_connection`
1. Detect libraries, runtime, and existing setup
2. Ask about the OTel collector (MC-hosted vs. self-hosted)
3. Ask whether stricter privacy requirements warrant redaction (default is full capture)
4. Snapshot existing agents via `get_agent_metadata` (BEFORE changes)
5. Resolve and confirm the final OTLP endpoint
6. Propose dependency-file edits
7. Propose `mc.setup()` insertion
8. Propose `@trace_with_workflow` / `@trace_with_task` decorator diffs
9. Confirm env vars (presence-only)
10. Verify via `get_agent_metadata` (AFTER user runs the agent)
11. On failure, branch to `troubleshooting.md`

---

## Step 0 — Pre-flight: confirm MCP connectivity

Before beginning the workflow, confirm the Monte Carlo MCP server is configured and authenticated by calling `test_connection`.

- **If `test_connection` succeeds** — proceed to Step 1. Record that MCP is available; Steps 4 and 10 will call `get_agent_metadata` without re-checking.
- **If `test_connection` fails** — **degrade gracefully**, don't exit. Tell the user that the Monte Carlo MCP server isn't available, point them at https://docs.getmontecarlo.com/docs/mcp-server as informational, and continue the workflow. Explain that they'll need to verify the new agent appears in the Monte Carlo UI manually after running the instrumented agent (Step 4 will skip the BEFORE snapshot and Step 10 will give them manual-UI verification instructions). Record `mcp_available = false` so Steps 4 and 10 know which path to take.

Do this check once, up front, so the user discovers a MCP problem immediately — not after three turns of intake questions.

---

## Step 1 — Detect libraries, runtime, and existing setup

Run the detection helper against the customer's agent code:

```bash
python3 scripts/detect_libraries.py <target_path>
```

It prints a JSON object with the following fields:

- `dependencies` — sorted list of normalized pip package names parsed from `requirements.txt` / `pyproject.toml` / `Pipfile`. Raw surface; the script does not single out AI libraries. The LLM matches these against `fetch_sdk_docs.py`'s `supported_instrumentors` list (see below).
- `runtime` — `serverless`, `long_running`, or `unknown`. `serverless` if any serverless signal is found; `long_running` if a dep manifest was found but no serverless signals; `unknown` when no dep manifest exists at all.
- `serverless_signals` — what triggered a serverless classification (e.g. `lambda_handler`, `serverless.yml`, `mangum`)
- `existing_setup` — `{ found: bool, files: list[str] }` for any pre-existing `mc.setup()` call. The `files` array contains repo-relative paths where `montecarlo_opentelemetry` was detected.

Match `dependencies` against the live PyPI supported-instrumentor list to figure out which instrumentors to install. See `library-detection.md` for the matching rules — including the ambiguous-multipurpose-SDK case (`boto3`, `google-cloud-aiplatform`, etc.) where the LLM must ask the customer before installing.

Parse this output and branch:

- **`existing_setup.found` is `true`** — do not propose a fresh `mc.setup()`. Inspect the paths listed in `existing_setup.files` to understand what already exists. Point the reader at the existing-setup decision matrix in `setup-template.md` to decide whether to keep, reconfigure, or replace the call. Then continue with the rest of the workflow (the user may still need decorator and dependency changes).

### Known limitations

`existing_setup` detection parses Python imports and setup calls. It recognizes `import montecarlo_opentelemetry`, aliases such as `import montecarlo_opentelemetry as mco`, and direct imports such as `from montecarlo_opentelemetry import setup as setup_mc`, but only when the imported module/name is actually called. Malformed Python files fall back to a narrower text check, so if the customer reports an existing setup that was missed, inspect those files manually before proposing a new `mc.setup()`.

### Match in real code, not docs or comments

The same principle that governs `existing_setup` detection applies to every match-scanning step in this workflow — library-import detection, decorator-candidate identification, and existing-`mc.setup()` lookup. Before treating a match as actionable, confirm it lives in executable Python code, not in a docstring, an inline comment, an example block in a Markdown file, or test fixture data. A match inside a `"""..."""` doc block or a `README.md` example is not a real usage.

- **`runtime: "unknown"` and `dependencies: []`** — exit cleanly. No dependency manifest was found in the target tree, so there's nothing to scan. Tell the user: "I didn't find a `requirements.txt`, `pyproject.toml`, or `Pipfile` in the target. Confirm the agent code is actually in this path, then re-run." Do not scaffold anything.
- **`dependencies` non-empty but no PyPI-supported AI library matches** — exit cleanly per `library-detection.md` section 7. Don't scaffold an `mc.setup()` against an empty instrumentor list unless the customer is manually reporting every LLM call with `mc.create_llm_span`.
- **Anything else** — continue to step 2 with the detection output in hand.

Always run `python3 scripts/fetch_sdk_docs.py` alongside `detect_libraries.py`. It pulls the live `supported_instrumentors` list from PyPI — that's the canonical source for which AI libraries the SDK currently supports. The script fails closed if PyPI is unreachable; if it errors, point the user at `https://pypi.org/project/montecarlo-opentelemetry/` directly and ask them to share the current supported list manually. Match the customer's `dependencies` against `supported_instrumentors` to decide which instrumentors to install.

**Next:** with detection settled, ask about the collector.

---

## Step 2 — Ask about the OTel collector

Ask the user verbatim:

> "Are you using your own OTel collector or the MC-hosted one?"

Capture the answer — it gates step 5 (endpoint normalization) and step 9 (env-var checks).

- **MC-hosted** — base URL is `https://integrations.getmontecarlo.com/otel`. Step 9 will require either `MCD_DEFAULT_API_ID` / `MCD_DEFAULT_API_TOKEN` or `OTEL_EXPORTER_OTLP_HEADERS`, depending on the setup template.
- **Self-hosted** — ask: "What's the base URL for your collector?" Capture it as the customer's collector base URL. Step 9 will skip MC credential checks because auth happens at the customer's collector.

Don't try to infer the collector from anything in the codebase — just ask.

**Next:** ask whether the customer has stricter privacy requirements that warrant redaction, so step 3 picks the right `mc.setup()` template.

---

## Step 3 — Ask whether redaction is required

The Monte Carlo OpenTelemetry SDK's value proposition is auto-instrumentation that captures prompts and completions by default. Trace content lives in the customer's environment; the MC-hosted collector is a write-back pass-through with no MC-side persistence of trace content. Full capture is therefore the canonical path, and redaction is opt-in for customers with stricter requirements.

Ask the user verbatim:

> "Do you have stricter requirements (compliance, contractual, or company policy) that would require redacting prompts or completions in traces?"

This is a non-optional gating decision that runs **before** any `mc.setup()` is generated.

- **Yes** — route the user to `redaction.md`. Under redaction, `TRACELOOP_TRACE_CONTENT=false` is **mandatory** when an auto-instrumentor is in use (else the instrumentor emits duplicate-content spans alongside any manual redacted spans). The prompts-disabled `mc.setup()` template in step 7 sets this in code. Customers who want partial capture with placeholder substitution can layer manual `mc.create_llm_span` calls on top — that's an optional additional layer, not a replacement.
- **No** — use the default `mc.setup()` template in step 7. The default leaves auto-instrumentor capture on; prompts and completions flow into the customer's environment with no extra wiring.

**Next:** snapshot existing agents before any code changes land.

---

## Step 4 — Snapshot existing agents via `get_agent_metadata` (BEFORE changes)

This must run **before** step 6, 7, or 8 propose any diffs. The snapshot is what step 10 compares against to prove the new instrumentation actually produced traces.

Branch on the MCP availability flag recorded in Step 0:

- **MCP available** — call `get_agent_metadata`. Save the list of `(agent_name, mcon)` pairs and hold onto the snapshot; step 10 diffs against it.
- **MCP unavailable** — skip the BEFORE snapshot. Tell the customer that without MCP this skill can't capture a baseline, so step 10 will hand them off to verify the new agent in the Monte Carlo UI manually. Continue the workflow.

If MCP was reported available in Step 0 but the `get_agent_metadata` call now fails (e.g. the session expired), re-run `test_connection`. If it still fails, flip `mcp_available = false` and proceed under the manual-UI verification path described above.

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
| `https://collector.example.com:4318`               | `https://collector.example.com:4318/v1/traces`                 |

Render the resolved final URL to the user and ask for confirmation before generating any code. See `setup-template.md` for the full normalization rules.

**Next:** propose dependency edits using the install set from step 1.

---

## Step 6 — Propose dependency-file edits

Determine the install set by matching `detect_libraries.py`'s `dependencies` against `fetch_sdk_docs.py`'s `supported_instrumentors` per `library-detection.md`. Always include the MC SDK package itself.

**Pinning is required, not optional.** Each `supported_instrumentors` entry from `fetch_sdk_docs.py` may include a `version_constraint` (e.g. `<=0.53.4`) parsed from the PyPI README's `pip install` line. Apply that constraint directly in the proposed diff — never strip it. If `fetch_sdk_docs.py` failed (PyPI unreachable) it exits with an error rather than substituting stale data; point the user at `https://pypi.org/project/montecarlo-opentelemetry/` to resolve pins manually.

Some instrumentors have transitive constraints PyPI doesn't expose. The most common today is `wrapt<2`, required alongside the OpenLLMetry instrumentors. The skill **does not** preemptively bake that pin into every install diff — it's surfaced as a symptom-driven fix in `troubleshooting.md` (the customer hits a `TypeError: wrap_function_wrapper() got an unexpected keyword argument 'module'` and the troubleshooting reference names the pin). If the customer reports that error after installing, route them to that section.

Propose the additions as a unified diff against the customer's actual dependency file — `requirements.txt`, `pyproject.toml`, or `Pipfile`. Wait for **explicit per-file approval** before any edit lands.

> **CRITICAL — never edit dependency files autonomously.** Even if the change looks trivial. The user reviews and accepts each diff. See `library-detection.md` for the install rules.

If any of the customer's `dependencies` is ambiguous (e.g. `boto3` could mean Bedrock, SageMaker, or generic AWS; `google-cloud-aiplatform` could be Vertex inference or Vertex Search), surface the candidates and ask the user before deciding what to install. Don't guess. See `library-detection.md` section 4.

**Next:** propose the `mc.setup()` insertion.

---

## Step 7 — Propose `mc.setup()` insertion as a diff

Use the runtime classification from step 1 to pick the template:

- **`runtime: "serverless"`** — use the serverless template, which uses `SimpleSpanProcessor` so spans flush before the Lambda freeze. See `setup-template.md` for the canonical template. The serverless `BatchSpanProcessor` foot-gun is covered in `troubleshooting.md`.
- **`runtime: "long_running"`** — use the default template in `setup-template.md`. `BatchSpanProcessor` is appropriate here.
- **`runtime: "unknown"`** — by step 7 you should never be here; step 1 would have exited cleanly. If you somehow are, ask the user to classify before proposing a template.

If the customer opted into redaction in step 3, use the prompts-disabled variant of the chosen template — it sets `TRACELOOP_TRACE_CONTENT=false` in code, which is mandatory under redaction to prevent auto-instrumentors from emitting duplicate-content spans. If the customer did not opt into redaction, use the default template, which leaves auto-instrumentor capture on.

If step 1 reported `existing_setup.found: true`, don't propose a fresh insertion — apply the decision from `setup-template.md`'s existing-setup matrix instead.

Propose the change as a diff. Wait for explicit approval before writing the file.

**Next:** propose decorator placement.

---

## Step 8 — Propose `@trace_with_workflow` and `@trace_with_task` decorator diffs

Identify two kinds of functions in the agent code:

- **Orchestration entry points** — the function the customer calls to run the agent end-to-end. Decorate with `@trace_with_workflow`.
- **LLM-calling task functions** — the discrete units of work the workflow calls (a single LLM call, a tool invocation, a retrieval step). Decorate each with `@trace_with_task`.

> **CRITICAL — `@trace_with_workflow` and `@trace_with_task` are the only two decorators in scope for V1.** `monitoring-advisor` is built around the workflow/task model; other tracing primitives the SDK exposes are not part of the v1 surface.

Propose each decorator addition as a separate diff. Wait for **explicit per-diff approval**. See `decorator-placement.md` for placement guidance and the canonical example.

**Next:** confirm env vars are set (or skip, depending on step 2).

---

## Step 9 — Confirm env vars

Branches on the answer from step 2:

- **MC-hosted collector** — confirm the auth env vars for the chosen setup template are present in the customer's runtime environment. Use **presence-only checks**, e.g.:

  ```python
  bool(os.environ.get("MCD_DEFAULT_API_ID")) and bool(os.environ.get("MCD_DEFAULT_API_TOKEN"))
  # or, for the standard OTel header path:
  bool(os.environ.get("OTEL_EXPORTER_OTLP_HEADERS"))
  ```

  > **CRITICAL — never read or echo the credential value.** Presence (`bool(...)`) only. If a check needs to land in a logging or diagnostic file, mask everything but `True`/`False`. See `setup-template.md` on credential safety.

- **Self-hosted collector** — skip this step entirely. Auth is handled at the customer's collector; the MC SDK doesn't need `MCD_*` env vars in this branch. Don't ask the user to set them, and don't propose a check.

**Next:** hand back to the user to run their agent, then verify.

---

## Step 10 — Verify via `get_agent_metadata` (AFTER user runs the instrumented agent)

Ask the user to run the instrumented agent against their environment so it produces at least one workflow trace. Then branch on the MCP availability flag recorded in Step 0:

- **MCP available** — call `get_agent_metadata` again and diff against the snapshot from step 4. Expected outcomes:
  - A new entry exists with `agent_name` matching whatever the customer passed to `mc.setup(agent_name=...)`, and a new MCON.
  - If the same `agent_name` already existed in the snapshot (e.g. a dev/prod twin), the new MCON should still be different — confirm that.
  - If nothing new appears after a reasonable wait (see `verify-traces.md` for timing), go to step 11.
- **MCP unavailable** — hand off to manual UI verification. Tell the customer: "Sign in to Monte Carlo, go to Agent Observability, and confirm a new agent with the name you passed to `mc.setup(agent_name=...)` appears. First-time visibility for low-traffic dev agents can take 10–15 minutes; if it still isn't visible after that, go to step 11." Don't claim verification on the customer's behalf — they confirm.

See `verify-traces.md` for the full diffing logic, timing expectations, and edge cases.

**Next:** if verification passed, the workflow is done. If not, troubleshoot.

---

## Step 11 — On failure, branch to `troubleshooting.md`

The four common failure modes, in roughly the order to check:

1. **SDK init not running** — `mc.setup()` is in the file but the import path or entry point isn't actually loading it at runtime.
2. **Wrong instrumentor versions** — the installed OTel instrumentors are incompatible with the SDK or with each other.
3. **Missing credentials** — the selected MC-hosted auth env vars are not present in the runtime (`MCD_DEFAULT_API_ID` / `MCD_DEFAULT_API_TOKEN` or `OTEL_EXPORTER_OTLP_HEADERS`).
4. **Upstream pipeline not actually deployed** — the agent code with `mc.setup()` exists in the repo but the deployed runtime is still the old build.

`troubleshooting.md` also covers the **serverless `SimpleSpanProcessor` foot-gun** — Lambda freezing the process before `BatchSpanProcessor` flushes, producing partial or missing traces. If the runtime is serverless and traces look incomplete (rather than absent), that's the first thing to check.

Walk the customer through whichever branch matches their symptoms. Once a fix is in place, re-run step 10.
