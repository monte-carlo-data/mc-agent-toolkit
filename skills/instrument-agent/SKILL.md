---
name: monte-carlo-instrument-agent
description: Instrument a new AI agent in a Python codebase for Monte Carlo Agent Observability. Detects AI libraries, installs the Monte Carlo OpenTelemetry SDK, and proposes tracing setup and decorator placements as diffs. Asks before editing any file.
when_to_use: |
  Activates when the user wants to instrument a new AI agent in their Python codebase for Monte Carlo Agent Observability. Triggers include: "instrument my agent", "instrument my LangChain/LangGraph/CrewAI/Bedrock/OpenAI/Anthropic agent", "set up Monte Carlo tracing on a new agent", "add MC tracing to this agent", "wire up the Monte Carlo OpenTelemetry SDK", "set up agent observability for a new agent", "setting up an agent".

  Do NOT activate for: monitoring or alerting on an existing agent (use monitoring-advisor); investigating agent issues, alerts, or traces (use incident-response or analyze-root-cause); pushing agent metadata (use push-ingestion); creating monitors on agent traces ("monitor my agent latency", "alert on agent errors" — those go to monitoring-advisor). Boundary: this skill PRODUCES traces; monitoring-advisor consumes them.
bucket: Setup
version: 1.0.0
---

# Monte Carlo Instrument-Agent Skill

This skill walks an MC Agent Observability customer through instrumenting a new AI agent in their Python codebase: detect AI libraries → install the Monte Carlo OpenTelemetry SDK + matching instrumentors → generate `mc.setup()` (with `SimpleSpanProcessor` when serverless) → propose `@trace_with_workflow` / `@trace_with_task` decorator diffs → confirm env vars (only when needed) → verify traces flow via `get_agent_metadata`.

The skill produces traces. It is **not** for monitoring or alerting on existing traces — that's `monte-carlo-monitoring-advisor`. The two skills are sequential: instrument-agent first, monitoring-advisor afterward.

Reference files live next to this file. **Use the Read tool** (not MCP resources) to access them.

## CRITICAL — Never modify any file without explicit user approval

This skill **must not** modify *any* file in the customer's codebase without explicit per-file user approval. This rule covers:

- **Dependency files** — `requirements.txt`, `pyproject.toml`, `Pipfile`, lockfiles. Always propose the diff and wait for confirmation before editing.
- **Source code** — `mc.setup()` insertion, decorator placement (`@trace_with_workflow`, `@trace_with_task`), import additions. Always propose the diff and wait for confirmation per file.
- **Env files** — `.env`, `.envrc`, shell rc files. Always propose the change and wait for confirmation before editing.

The skill walks the user through *what* needs to change and *why*, then proposes diffs. It does not apply edits, run `pip install`, or write env files autonomously. The only exception: the user may explicitly waive approval for a specific file ("I know the risks, just edit the file") — proceed for that file only and surface that the approval was waived.

This guardrail mirrors PRD requirement #8 ("Never modifies code without explicit user approval") and is reinforced in the Tier-3 references (`references/decorator-placement.md`, `references/setup-template.md`, `references/library-detection.md`).

## When to activate this skill

Activate when the user expresses intent to instrument a new AI agent:

- Asks to instrument an agent for Monte Carlo, set up MC tracing, or wire up the Monte Carlo OpenTelemetry SDK
- Asks how to add tracing to a LangChain / LangGraph / OpenAI / Anthropic / CrewAI / Bedrock / SageMaker / Vertex AI agent
- Says things like "instrument my agent", "set up tracing", "set up Monte Carlo on my new agent", "setting up an agent"
- References the SDK install or `mc.setup()` (when generating; not when diagnosing)

## When NOT to activate this skill

Do not activate when the user is:

- Asking to **monitor** an existing agent (latency, token usage, evaluation, trajectory, validation) → `monte-carlo-monitoring-advisor`
- Investigating an active agent **incident** or alert → `monte-carlo-incident-response` / `monte-carlo-analyze-root-cause`
- Asking about **pushing metadata or query logs** to Monte Carlo (data ingestion, not agent tracing) → `push-ingestion`
- Building a **Connection Auth Rules** config → `connection-auth-rules`
- Asking why traces are missing for an *already-instrumented* agent → that's troubleshooting; this skill covers it via `references/troubleshooting.md`, but the *first* invocation should be deliberate (not a coverage question)

If the user is ambiguous ("set up agent observability"), surface both options and ask whether they're instrumenting a *new* agent (this skill) or configuring monitors on an *existing* one (monitoring-advisor).

## Pre-flight check

Before walking the workflow, confirm two things:

1. **Monte Carlo MCP server is configured + authenticated.** Run `testConnection`. If unavailable, point the user at the MC MCP setup docs (`https://docs.getmontecarlo.com/docs/mcp-server`) and exit cleanly. The verification step (`get_agent_metadata`) requires the MCP server.
2. **Python codebase is present.** Look for `requirements.txt`, `pyproject.toml`, or `Pipfile` in the working directory. If none exist, ask the user where the agent codebase is.

## Reference files — when to load

The skill is structured as a Tier 1 router (this file) → Tier 2 workflow → Tier 3 per-step references. Load each reference when its step is reached in the workflow.

| Reference file | Load when… |
|---|---|
| `references/workflow.md` | At the start of every invocation. Tier 2 — the end-to-end flow. Read first. |
| `references/library-detection.md` | Walking step 1 of the workflow — detecting AI libraries, the runtime style (serverless vs long-running), and any existing `mc.setup()`. Documents the PRD core library list as a stable contract. |
| `references/setup-template.md` | Walking step 5–7 of the workflow — resolving the OTLP endpoint, generating `mc.setup()`, handling the existing-`mc.setup()` decision matrix. Includes both serverless and long-running templates. |
| `references/decorator-placement.md` | Walking step 8 of the workflow — proposing `@trace_with_workflow` and `@trace_with_task` diffs. Tier 3: those are the only two decorators in scope for v1. |
| `references/verify-traces.md` | Walking step 4 (BEFORE snapshot) and step 10 (AFTER verification) of the workflow — both `get_agent_metadata` calls. Documents dev/prod twin disambiguation via MCON. |
| `references/redaction.md` | When the user answers "yes" to step 3 of the workflow ("Will any prompts/completions contain sensitive data?"). Documents the three V1 redaction pathways. |
| `references/troubleshooting.md` | When step 10's verification doesn't show the new agent, or the user reports incomplete traces. Covers the four PRD failure modes plus the serverless `SimpleSpanProcessor` foot-gun. |

## High-level workflow (Tier 1 summary)

The full step-by-step flow lives in `references/workflow.md`. At a glance:

1. **Detect** AI libraries, runtime style, and any existing `mc.setup()` via `scripts/detect_libraries.py`.
2. **Ask** whether the customer hosts their own OTel collector or uses the MC-hosted one — gates the env-var step.
3. **Ask** whether prompts/completions will contain sensitive data — gates the redaction routing.
4. **Snapshot existing agents** via `get_agent_metadata` (BEFORE any code changes).
5. **Resolve and display the final OTLP endpoint** to the user — normalize idempotently (never double-append `/v1/traces`).
6. **Propose dependency-file edits** and wait for approval — install SDK + instrumentors at compatible versions (live-fetched from PyPI; fall back to the snapshotted `instrumentor_map.json` with a STALE warning).
7. **Propose `mc.setup()` insertion** as a diff and wait for approval — serverless variant uses `SimpleSpanProcessor`.
8. **Propose `@trace_with_workflow` / `@trace_with_task` decorator diffs** — wait for approval per file. Those are the only two decorators in scope for v1.
9. **Confirm env vars** (only on the MC-hosted collector path) — `MCD_DEFAULT_API_ID` / `MCD_DEFAULT_API_TOKEN`. Presence-only check; never read or echo the values.
10. **Verify** via `get_agent_metadata` (AFTER user runs the instrumented agent) — confirm new `agent_name` + new MCON appears.
11. **On failure**, branch to `references/troubleshooting.md`.

Each step's full Tier 3 details live in the reference files above.

## Helper scripts

The skill ships three Python helpers under `scripts/` that the workflow invokes:

| Script | Purpose |
|---|---|
| `scripts/detect_libraries.py` | Parse `requirements.txt` / `pyproject.toml` / `Pipfile`; classify runtime as serverless / long-running / unknown; detect existing `mc.setup()`. Returns JSON. |
| `scripts/fetch_sdk_docs.py` | Live-fetch the SDK supported-instrumentor list from GitHub README + PyPI metadata. Falls back to `scripts/instrumentor_map.json` (with a STALE warning) when live fetch fails. |
| `scripts/instrumentor_map.json` | Snapshotted last-known-compatible instrumentor list with `snapshot_date`. Source-of-truth fallback when PyPI is unreachable; canonical schema shared with `detect_libraries.py` and `fetch_sdk_docs.py`. |

The instrumentor list and version constraints come from PyPI live; the local snapshot is only consulted when the live fetch fails. Live success requires all PRD core libraries (`langchain`, `langgraph`, `openai`, `anthropic`, `crewai`, `bedrock`, `sagemaker`, `vertexai`) to be present — partial parses fall back to the snapshot for completeness.

## Out of scope (v1)

- Auto-scaffolded `create_llm_span` boilerplate for libraries without a dedicated instrumentor.
- Auto-instrumented redaction (proactive sensitive-data detection and wrapping). The skill is *conversant* in redaction — when the user asks, it walks them through the three V1 pathways in `references/redaction.md`.
- Full first-time AO setup (infra deployment, datastore registration, warehouse ingestion).
- API-key generation.
- Non-Python SDKs.
- Decorators other than `@trace_with_workflow` and `@trace_with_task`. Other tracing primitives the SDK exposes are not part of the v1 surface.

## Available slash commands

| Command | Purpose |
|---|---|
| `/instrument-agent` | Kicks off the workflow against the current Python codebase. |
