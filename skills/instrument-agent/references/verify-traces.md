# Verify Traces

How to confirm that an instrumented agent is actually emitting traces to Monte Carlo. This is the verification step at the end of the instrument-agent workflow.

The skill calls `get_agent_metadata` exactly **twice** per instrumentation flow — once to snapshot existing agents before any code changes, and once after the customer runs the instrumented agent. New traces are confirmed by diffing the two snapshots on `(agentName, traceTableMcon)`.

---

## 1. Pre-flight: `test_connection`

`test_connection` is the Step 0 pre-flight check — it runs once at the very start of the workflow, before any intake questions. By the time the BEFORE snapshot (Step 4) runs, MCP connectivity is already confirmed.

This section documents what that pre-flight check does and what to do if MCP is unavailable at snapshot time (e.g. the session expired mid-workflow):

> **CRITICAL — bail early if `test_connection` fails.** Do not propose any code changes. The verification step at the end of the workflow won't work, and instrumenting without verification means the customer ships traces with no way to confirm they arrived. Point at https://docs.getmontecarlo.com/docs/mcp-server for setup and exit cleanly.

If MCP was confirmed in Step 0 but appears unavailable at Step 4 or Step 10, re-run `test_connection` to confirm and exit cleanly if it fails — do not continue the workflow without MCP.

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

> **NEVER poll `get_agent_metadata` in a loop.** The skill calls it twice — once before edits, once after the user reports running the agent. Polling burns API quota and adds nothing. Monte Carlo's ingestion pipeline takes seconds to a few minutes for new agents to appear, and the trigger is the customer running the agent, not the passage of time.

If the customer says "I ran it but I don't see it yet," wait a minute and ask them to retry the check. If it's still missing after ~5 minutes, branch to `troubleshooting.md`.

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

- A new `agentName` should appear in `get_agent_metadata` within seconds to a few minutes.
- If after ~5 minutes the new agent isn't visible, something is wrong (SDK init not running, wrong endpoint, missing credentials, batch processor suspended on Lambda, etc.). Branch to `troubleshooting.md`.

---

## Common mistakes

- **Calling `get_agent_metadata` only once** (after the edits). Without the BEFORE snapshot, you can't tell new from existing. Wrong.
- **Comparing only `agentName`, not MCON.** Misses the dev/prod twin case where the same name already exists. Wrong.
- **Polling `get_agent_metadata` in a loop while waiting.** Wasteful and unnecessary — the customer running the agent is the trigger.
- **Skipping the `test_connection` pre-flight.** Verification fails silently if MCP is misconfigured, and the customer ships uninstrumented or unverified code.
- **Concluding "instrumentation works" without running the agent and re-checking.** Premature — code changes alone prove nothing.
- **Assuming a Lambda customer's missing trace is a credential issue.** Usually it's the `SimpleSpanProcessor` foot-gun. Check serverless first.
