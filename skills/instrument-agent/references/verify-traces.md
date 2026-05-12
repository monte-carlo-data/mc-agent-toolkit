# Verify Traces

How to confirm that an instrumented agent is actually emitting traces to Monte Carlo. This is the verification step at the end of the instrument-agent workflow.

The skill calls `get_agent_metadata` exactly **twice** per instrumentation flow — once to snapshot existing agents before any code changes, and once after the customer runs the instrumented agent. New traces are confirmed by diffing the two snapshots on `(agentName, traceTableMcon)`.

---

## 1. Pre-flight: `test_connection`

`test_connection` is the Step 0 pre-flight check — it runs once at the very start of the workflow, before any intake questions. Its job is to record whether MCP is available so Steps 4 and 10 know which verification path to take.

- **MCP available** — Step 4 captures a BEFORE snapshot via `get_agent_metadata` and Step 10 diffs against it. This is the canonical path.
- **MCP unavailable** — **degrade gracefully, don't exit.** Tell the user the Monte Carlo MCP server isn't reachable, link them to https://docs.getmontecarlo.com/docs/mcp-server for setup, and continue. Step 4 skips the BEFORE snapshot. Step 10 hands the customer off to verify the new agent appears in the Monte Carlo UI manually after they run the instrumented agent. Instrumentation can still proceed; only the in-skill verification step changes.

If MCP was reported available in Step 0 but a subsequent `get_agent_metadata` call fails (e.g. the session expired mid-workflow), re-run `test_connection`; if it still fails, flip `mcp_available = false` and proceed under the manual-UI verification path.

---

## 2. The before/after pattern

### BEFORE snapshot (workflow step #4)

Before any edits to the customer's code, call `get_agent_metadata` and save the full list of `(agentName, traceTableMcon)` pairs. This is the baseline.

The response shape:

```json
[
  {"agentName": "customer-support", "traceTableMcon": "MCON://...", "sourceType": "TRACE_TABLE"},
  {"agentName": "monitoring-agent", "traceTableMcon": "MCON://...", "sourceType": "PLATFORM_AGENT"}
]
```

Each MCON is unique per ingestion source — it is the true identity of the trace stream. `agentName` is **not** unique on its own.

### AFTER snapshot (workflow step #10)

After the customer has approved the `mc.setup()` and decorator diffs **and** has run the instrumented agent end-to-end at least once, call `get_agent_metadata` again and diff against the BEFORE snapshot.

---

## 3. Why MCON, not name, is the identity

> **IMPORTANT — when the same `agent_name` reappears in the AFTER snapshot, compare MCONs.**

Common gotcha: a customer instruments the agent in dev, then later instruments the *same* agent in prod. Both report `agent_name="customer-support"` to MC. Comparing only on `agentName`, the AFTER snapshot looks identical to the BEFORE snapshot ("customer-support is still there"), and the skill would falsely conclude the prod instrumentation worked when it actually didn't.

A genuinely new agent has a **new MCON** not in the BEFORE list. If the MCON is unchanged from the BEFORE snapshot, no new traces have arrived — branch to `troubleshooting.md`.

---

## 4. Prompting the customer between snapshots

Verification is gated on the customer running the instrumented agent at least once. After the BEFORE snapshot and after they've approved the diffs, prompt them:

> "I've snapshotted your existing agents in Monte Carlo. Run your instrumented agent end-to-end against your environment (your dev or staging stack) at least once, then tell me when it's done. I'll re-check `get_agent_metadata` and confirm the new agent appears."

Then **wait for the customer to confirm** they ran it. Don't loop. Let them work and ping the skill when ready.

---

## 5. Don't poll

> **NEVER poll `get_agent_metadata` in a loop.** The skill calls it twice — once before edits, once after the user reports running the agent. Polling burns API quota and adds nothing. The trigger is the customer running the agent, not the passage of time. First-time visibility for low-traffic or dev agents can take 10 minutes or more.

If the customer says "I ran it but I don't see it yet," wait a couple of minutes and ask them to retry the check. If after ~10–15 minutes the new agent still isn't visible, branch to `troubleshooting.md`.

---

## 6. The AFTER call — what to check

When the user reports they've run the instrumented agent:

1. Call `get_agent_metadata`.
2. Filter for **new entries** — any `(agentName, traceTableMcon)` not in the BEFORE snapshot.
3. Look for an `agentName` matching what the customer put in `mc.setup(agent_name=...)`.
4. Confirm the MCON is genuinely new (not present in BEFORE).

### Success path

- New entry with the customer's chosen `agent_name` **and** a new MCON → traces are flowing. Tell the customer the instrumentation is verified, and recommend the `monte-carlo-monitoring-advisor` skill for setting up monitors.

### Failure paths

- **No new entries at all** → the instrumented agent hasn't sent any spans. Branch to `troubleshooting.md`.
- **New entry exists but with a different `agent_name` than expected** → likely a typo in `mc.setup()` or two `mc.setup()` calls in the codebase. Walk the customer through the decision matrix in `setup-template.md`.
- **New entry's MCON matches a BEFORE entry** → not actually new. Branch to `troubleshooting.md`.
- **Customer is on a serverless runtime (Lambda, Cloud Run, etc.) and traces aren't appearing** → highly likely the `SimpleSpanProcessor` is missing. Branch to `troubleshooting.md` with that hypothesis first.

---

## 7. Timing expectations

After the customer's agent runs and emits OTLP spans:

- A new `agentName` typically appears in `get_agent_metadata` within a few minutes. First-time visibility for low-traffic dev agents, or for agents emitting a small number of spans, can take 10 minutes or more — be patient, especially on a customer's first instrumentation pass.
- If after ~10–15 minutes the new agent still isn't visible, something is wrong (SDK init not running, wrong endpoint, missing credentials, batch processor suspended on Lambda, etc.). Branch to `troubleshooting.md`.

### Optional: local verification with a desktop OTLP receiver

When the customer wants to confirm the instrumentation produces valid OTLP spans *before* pointing at MC's collector — for example, while iterating in dev — they can run a local OTLP receiver and temporarily set `OTEL_ENDPOINT` to it. [`otel-desktop-viewer`](https://github.com/CtrlSpice/otel-desktop-viewer) is a single-binary receiver with a browser UI that makes the trace tree easy to inspect (the Docker image listens on `4317` for gRPC, `4318` for HTTP, and serves the UI on `8000`).

This is **not** a substitute for the MC-side `get_agent_metadata` check — only the latter proves the trace reached Monte Carlo. But it is useful for:

- Confirming the wiring (`@trace_with_workflow` produces a root, `@trace_with_task` nests under it, the auto-instrumentor's LLM spans land where expected).
- Distinguishing "traces never emitted" from "traces emitted but dropped in transit" when troubleshooting Step 10 failures.

Note: the published Docker image's JSON-RPC API may lag the repo's `main` branch — its method names tend to be stable across releases, but new methods may not be available yet on `latest-arm64` / `latest-amd64`.

---

## Common mistakes

- **Calling `get_agent_metadata` only once** (after the edits). Without the BEFORE snapshot, you can't tell new from existing. Wrong.
- **Comparing only `agentName`, not MCON.** Misses the dev/prod twin case where the same name already exists. Wrong.
- **Polling `get_agent_metadata` in a loop while waiting.** Wasteful and unnecessary — the customer running the agent is the trigger.
- **Skipping the `test_connection` pre-flight.** Verification fails silently if MCP is misconfigured, and the customer ships uninstrumented or unverified code.
- **Concluding "instrumentation works" without running the agent and re-checking.** Premature — code changes alone prove nothing.
- **Assuming a Lambda customer's missing trace is a credential issue.** Usually it's the `SimpleSpanProcessor` foot-gun. Check serverless first.
