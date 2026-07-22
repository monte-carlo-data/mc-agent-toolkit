# Backend: Snowflake Cortex / Snowflake Intelligence (`platform_agent`)

## What this backend is

A **declarative platform agent** running inside the customer's Snowflake account —
Cortex Agents / Snowflake Intelligence. There is no agent source code: the agent is
defined by its configuration (instructions, tools, semantic models/views), and Snowflake
runs it. Monte Carlo reads its AI-observability events, normalized to the standard span
vocabulary.

**CRITICAL: there is no code repo and no PRs here — the fix surface is the agent's
configuration. A "which PR broke it" question has no answer on this backend; a "which
config change broke it" question usually does.**

## Signal available here

- **Real span structure with token counts** — token, duration, and status questions all
  have answers; latency and error trends are readable through `get_agent_traces`.
- **A config surface with change timestamps** — the agent's instructions, tools, and
  semantic views carry created/modified times. This is the platform analog of code
  history and the primary change-correlation signal.
- **Conversations** — `get_agent_conversations` (rank by tokens/duration/errors to find
  the expensive or failing ones) and `get_agent_conversation` for a full thread.
  Transcript content is consent-gated (see Gotchas).
- **Data lineage bridge** — the agent's generated SQL queries real source tables; a
  freshness/volume/schema incident on a source table (check `get_alerts`) is a data
  root cause only Monte Carlo can surface.
- **Segments** — `get_agent_segments` for the workflow/task values in play.

## Absent by design — do not chase

- **No source code, no GitHub, no PRs.** Do not look for repositories or recommend code
  changes.
- **No OTel exception attributes** — error semantics come from span status and the
  tool-span structure, not from exception type/message fields.
- **Latency and infrastructure are Snowflake-managed** and not user-fixable — focus on
  answer quality and cost via the config surface, not on infra tuning.
- **Raw content is consent-gated** — prompts, completions, generated SQL, and
  transcripts require the account's data-sampling consent. Structure, status, tokens,
  and config are always available.

## Investigation approach

1. **Confirm the backend** — `get_alert_agent_classification` / `get_agent_metadata`.
2. **Config-space investigation FIRST.** Compare the agent's configuration modification
   times (instructions, semantic views, tools) against the regression window. An
   instruction edit, a semantic-model change, or a tool change landing right before the
   anomaly is a top root cause on this backend.
3. **Compare BEFORE vs AFTER.** The incident window vs the immediately-prior baseline —
   traces, tokens, duration, errors — plus the longer daily trend via `get_agent_traces`
   aggregation. Did the breached metric *step* on a specific day (points at a config
   change that day) or drift? Never describe only the bad window.
4. **Look at WHAT breached — and rule out a false positive.** Pull the flagged
   conversations (`get_agent_conversations`, sampled from the breaching side of the score
   per the metric + breach direction — see `agent-alert-evaluation.md` step 3) and read
   them (`get_agent_conversation`). Decide: genuine problem (runaway tool loop,
   bloated answer, error spike) vs false positive (a legitimately long-but-correct
   conversation, an expected seasonal spike, a too-tight threshold). A breach the sample
   shows to be benign **is a finding** — say so and recommend adjusting the monitor.
5. **Bridge to the data.** Identify the source tables the agent queried and check
   `get_alerts` for incidents on them — a data incident upstream explains a quality drop
   better than anything in the agent itself.
6. For a full automated root-cause run, hand off to `run_troubleshooting_agent` and
   collect results with `get_troubleshooting_agent_results`.

## Gotchas

- **Consent gating is a fact to report, not a failure.** If conversation content comes
  back blocked or empty because of the account's data-sampling settings, say that content
  is unavailable on this account and continue from structure, tokens, and config — do
  not retry or treat it as an error.
- **Prefer summaries and rollups over raw span pulls.** Wide raw reads get truncated on
  this backend; aggregate views (`get_agent_traces` grouping, `get_agent_segments`,
  conversation lists ordered by impact) are the reliable way to see the picture.
- **Eval scores are computed in-warehouse.** A quality-score movement correlates with a
  config-surface change or a source-data shift — never with a Monte Carlo–side scoring
  change.
- **Schema questions are answered from the normalized vocabulary.** Do not run
  exploratory queries against the trace store to discover fields — the field list is in
  the span-field reference below.
- **Fix language is config-surface only:** edit instructions, adjust semantic views,
  add/remove tools, fix the upstream data incident. Never recommend code changes or
  infrastructure tuning.

## Cross-links

- Span-field vocabulary: `../../monitoring-advisor/references/agent-span-fields.md`
- Alert-type playbooks: `agent-alert-*.md`
