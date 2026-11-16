# Backend: Monte Carlo OTel Store (`ao_clickhouse_otel`)

## What this backend is

The Monte Carlo–managed trace store for OpenTelemetry-instrumented **code agents**. The
customer instruments their own agent code with OTel and Monte Carlo ingests the spans.
This is the richest backend: everything the platform can know about an agent run exists
here, so the investigation is limited by your discipline, not by the data.

**CRITICAL: there is no built-in previous-period baseline on this backend — every trend
you read describes only the window you asked for. Always construct your own comparison
window (e.g. the 7 days before the onset vs the window after it) before calling anything
a regression.**

## Signal available here

- **Full, real span tree** — parent/child structure, per-span timing, and error flags via
  `get_agent_trace`.
- **Model per span and token counts** (prompt / completion / total) — model-swap, cost,
  and context-overflow questions all have answers here.
- **Error detail** — status per span plus error type and error message text.
- **Workflow / task / model segmentation** — enumerate real segment values with
  `get_agent_segments`; group and sort traces with `get_agent_traces`.
- **Conversations** — `get_agent_conversations` / `get_agent_conversation`, with
  transcripts when the account's data-sampling settings allow content.
  **Conversation-grain evaluation monitors** run here (and on the Snowflake Cortex and
  Databricks Genie platform backends), so a breached eval alert may name whole
  conversations rather than traces.
- **Conversation clustering** — when the account has clustering enabled for this agent,
  Monte Carlo groups its conversations into an intent-cluster taxonomy, shown alongside
  the agent's conversations in the Monte Carlo UI. No toolkit tool reads clusters
  directly: point the user at the cluster view to see which *kind* of conversations a
  regression concentrates in, or hand off to `run_troubleshooting_agent`, which uses
  cluster-share shifts as evidence.
- **Change correlation** — this is a code agent: when the customer has GitHub connected,
  correlate the onset with merged PRs and deploys.

## Absent by design — do not chase

- **No previous-period deltas** — trend reads are single-window; the baseline is yours to
  build.
- **No platform config surface** — behavior changes land through code deploys, not a
  declarative agent configuration. "What config changed?" is answered by PR/deploy
  history here, not by an agent settings diff.

## Investigation approach

1. **Confirm the backend first** — `get_alert_agent_classification` for an alert, or
   `get_agent_metadata` for the agent. The backend decides what signal exists and what
   the fix language is.
2. **Establish trends and find the onset.** Over a window of roughly 7 days before the
   earliest anomalous trace to 1 day after the latest, reproduce the trend dimensions
   with `get_agent_traces` aggregation (sort/group by the relevant field). The
   dimensions worth reproducing:
   - latency percentiles per node/task (typical vs tail)
   - error rate per node/task
   - throughput (trace and span volume over time)
   - token usage (prompt / completion / total)
   - prompt stability (did prompt sizes change, or prompts disappear, on a date?)
   - error-type breakdown over time
   - prompt/completion length growth
   - per-trace context accumulation (message counts growing span-over-span inside a
     trace — `get_agent_trace` on representative traces)
   Decide whether the movement is a **step** (look for a discrete change on that date)
   or a **drift**.
3. **Classify errors before hypothesizing.** Distinguish: provider rejection (LLM span
   errored with no tokens and no completion), timeout (far above the node's typical
   latency), fast-fail (errored in seconds), structured-output/parse failure, code
   exception, and slow-but-healthy (a risk, not an error).
4. **On a known-bad trace, list its failed spans in order** with `get_agent_trace`.
   Cascade failures show as multiple failed spans — the root cause is usually the
   earliest or innermost one. Read the actual error text before forming a hypothesis.
5. **Compare content across cohorts** (when content is available): read breaching
   conversations/traces and pre-onset ones, and compare — prompt changes, empty outputs,
   and shared failure patterns show up here.
6. **Correlate with changes.** PRs merged **before** the onset (a PR merged after the
   issue started cannot be the root cause; merges can precede deploys, so use wide
   margins), provider status pages for time-bounded spikes, and model changelogs for
   context-window or behavior changes.
7. Named plays worth knowing: **model switch** (non-overlapping model date ranges on the
   same node → before/after error pivot → check the new model's context window and
   whether prompts stayed identical); **provider rejection** (token/prompt growth
   upstream? new model at onset? time-bounded across traces ⇒ provider outage);
   **context overflow** (tokens usually present but now missing on failures ⇒ provider
   failure or overflow; overflow in a late node ⇒ the accumulation began in an earlier
   stage).
8. For a full automated root-cause run, hand off to `run_troubleshooting_agent` and
   collect the evidence timeline with `get_troubleshooting_agent_results`.

## Gotchas

- **Error status is effectively binary** — a span is either an error or it is healthy;
  do not invent intermediate severities from message text.
- **Interrupts are not errors.** LangGraph-style "interrupt" messages are control flow —
  exclude them from any error-rate reasoning.
- **Exception text quoted inside a span's input context is not a real error.** Healthy
  spans often *mention* more exceptions than failing ones (they carry prior errors as
  context). Trust the span's error status, never text matching on content.
- **Generic node names repeat.** A name like `RunnableSequence` can appear at several
  places in the graph — disambiguate by the span's position in the tree
  (`get_agent_trace` parent path), not by name alone.
- **Compare prompts by identity, not by prose.** Whether prompts are identical or
  changed across cohorts matters more than what they say — length and sameness are the
  first-class signals.
- **Units differ across tools.** `get_agent_traces` reports `duration_seconds`;
  `get_agent_trace` reports duration in milliseconds; monitors use `duration_sec`. See
  the span-field reference before quoting numbers.

## Cross-links

- Span-field vocabulary: `../../monitoring-advisor/references/agent-span-fields.md`
- Alert-type playbooks: `agent-alert-*.md`
