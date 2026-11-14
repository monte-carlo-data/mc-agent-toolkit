---
name: tune-monitor
description: Tune noisy Monte Carlo monitors, or find which ones to tune. Starts from Monte Carlo's tuning agent (stored suggestions or a fresh preview), applies only what the user approves. Metric, SQL, validation, table and agent monitors.
when_to_use: |
  Invoke when the user wants to tune, reduce noise on, or adjust sensitivity for a Monte Carlo monitor, or asks which monitors to tune.
  Example triggers: "tune monitor <uuid>", "this monitor is too noisy", "reduce alerts on this monitor", "adjust sensitivity for <uuid>", "which monitors should I tune?", "my monitors are noisy".
bucket: Monitoring
version: 1.1.1
---

# Tune Monitor: Noise Reduction Analysis

Monte Carlo runs a monitor tuning agent. It analyzes noisy monitors in the background and stores
its recommendations, and it can analyze any supported monitor on request. Your job is to bring
that analysis to the user, explain it, and apply only the changes they approve. Do your own
analysis of the monitor's report only when the tuning agent cannot analyze the monitor
(Phases 1–4 below are that fallback).

> **Monte Carlo tool routing (required):** Always call Monte Carlo MCP tools through this plugin's
> bundled server, whose fully-qualified tool names are
> `mcp__plugin_mc-agent-toolkit_monte-carlo-mcp__<tool>` (e.g.
> `mcp__plugin_mc-agent-toolkit_monte-carlo-mcp__get_alerts`). Bare tool names used in this skill
> (`get_alerts`, `search`, `get_asset`, …) refer to that bundled server. If the session also has a
> separately-configured `monte-carlo-mcp` server, do **not** route to it — it may point at a
> different endpoint or credentials.

**Arguments:** $ARGUMENTS

Reference files live next to this skill file. **Use the Read tool** (not MCP resources) to access
them:

- Metric monitor tuning: `references/metric-monitor.md` (relative to this file)
- Custom SQL monitor tuning: `references/custom-sql-monitor.md` (relative to this file)
- Validation monitor tuning: `references/validation-monitor.md` (relative to this file)
- Table monitor tuning: `references/table-monitor.md` (relative to this file)
- Agent metric monitor tuning: `references/agent-metric-monitor.md` (relative to this file)
- Agent evaluation monitor tuning: `references/agent-evaluation-monitor.md` (relative to this file)
- Agent trajectory monitor tuning: `references/agent-trajectory-monitor.md` (relative to this file)
- Agent validation monitor tuning: `references/agent-validation-monitor.md` (relative to this file)

---

## Prerequisites

- **Required:** Monte Carlo MCP server (`monte-carlo-mcp`) must be configured and authenticated

---

## Available MCP tools

| Tool | Purpose |
|---|---|
| `get_monitor_tuning_suggestions` | Read the tuning agent's stored analysis: no arguments for the account-wide list of monitors with a pending suggestion, `monitor_uuid` for one monitor's full recommendations (Phase 0.5) |
| `tune_monitor` | Ask the tuning agent for a fresh analysis (`dry_run=true`, the default), or apply approved recommendations (`dry_run=false`, Phase 5) |
| `get_monitor_report` | Fetch a monitor's alert history, incident details, and troubleshooting summaries |
| `get_monitors` | Fetch monitor configuration (type, thresholds, schedule, segments) |
| `create_or_update_metric_monitor` | Update a metric monitor in place (pass `monitor_uuid`; used in Phase 5) |
| `create_or_update_sql_monitor` | Update a custom SQL monitor in place (pass `monitor_uuid`; used in Phase 5) |
| `create_or_update_validation_monitor` | Update a validation monitor in place (pass `monitor_uuid`; used in Phase 5) |
| `create_or_update_table_monitor_asset_rule` | Tune freshness / volume change / unchanged size for a single table; pick the per-metric variant via `rule_type` (`last_updated_on` / `total_row_count` / `total_row_count_last_changed_on`). One call per `(table, metric)` pair (used in Phase 5). |
| `create_or_update_agent_metric_monitor` | Update an agent metric monitor in place (pass `monitor_uuid`; used in Phase 5) |
| `create_or_update_agent_evaluation_monitor` | Update an agent evaluation monitor in place (pass `monitor_uuid`; used in Phase 5) |
| `create_or_update_agent_trajectory_monitor` | Update an agent trajectory monitor in place (pass `monitor_uuid`; used in Phase 5) |
| `create_or_update_agent_validation_monitor` | Update an agent validation monitor in place (pass `monitor_uuid`; used in Phase 5) |

All the `create_or_update_*` tools follow a **two-call preview-then-confirm pattern**: the first call (with the default `dry_run=True`) returns the rendered MaC YAML for review in `result.yaml`; the second call (`dry_run=False`) deploys the change live and returns a deep link in `result.instructions`. **Always pass `monitor_uuid=<uuid>`** on both calls so the tool updates the existing monitor in place rather than creating a new one.

---

## Phase 0: Find the monitor

Look for a monitor UUID in `$ARGUMENTS` or the conversation (format:
`xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`; an alert from `get_alerts` lists its monitors in
`monitor_uuids`).

**No monitor named** ("which monitors should I tune?", "my monitors are noisy"): call
`get_monitor_tuning_suggestions` with no arguments. It lists the monitors Monte Carlo has flagged
as noisy, each with a pending suggestion. Present them as markdown links (text = monitor name,
destination = `monitor_url`) with their alert counts and recommendation titles, and ask which one
to go through. The titles are Monte Carlo's, not yours: don't write them up as recommendations
and don't add your own. When the list is empty, say nothing is pending and offer to analyze a
specific monitor. Continue at Phase 0.5 once the user picks one.

**Monitor described but no UUID** (a table plus monitor type, or a monitor name): resolve the
table with `search`, list its monitors with `get_monitors(mcons=[<mcon>])`, and confirm with the
user if more than one matches. If it can't be resolved, ask for the UUID. Then go to Phase 0.5.

---

## Phase 0.5: Start from the tuning agent

Call `get_monitor_tuning_suggestions(monitor_uuid=<uuid>)`.

A stored analysis is **current** only when both hold:
- the no-argument `get_monitor_tuning_suggestions()` list has a row for this monitor with the same
  `run_uuid`. The list drops monitors edited since their analysis, including edits in the UI or
  through Monitors-as-Code;
- `changes_applied_since` is empty. It only covers changes made by tuning runs, so it is not
  enough on its own.

- **Recommendations returned and current:** present them (Phase 0.6). Always open with where the
  analysis came from (`source`: a background analysis by Monte Carlo, or `MANUAL`, an on-demand
  analysis requested by a user or started by Monte Carlo while planning a remediation) and when
  (`triggered_at`). Keep its `run_uuid`: Phase 5 checks it again before applying.
- **Recommendations returned but not current:** don't present them as advice. Say why in one line
  (retuned since, per `changes_applied_since`, or no longer the pending analysis on the list),
  then call `tune_monitor(monitor_uuid=<uuid>)` for a fresh preview.
- **No recommendations on record:** call `tune_monitor(monitor_uuid=<uuid>)`. It defaults to
  `dry_run=true`, so it only previews. It can take a minute or two.
- **`tune_monitor` returns recommendations:** present them (Phase 0.6).
- **`tune_monitor` returns no recommendations and no `skip_reason`:** the tuning agent analyzed the
  monitor and found nothing to change. Say so; run Phases 1–4 only if the user asks.
- **`skip_reason` names a deleted monitor or a collection failure:** relay it with its fix and
  stop. Do not fall back to your own analysis. If the alerts are run failures, point to
  remediation.
- **Any other `skip_reason` (the agent's changes were dropped), or `tune_monitor` fails:** relay
  `skip_reason` as given, then fall back to your own analysis (Phases 1–4). Do not call
  `tune_monitor` again until its cause is fixed.

Either way, skip Phases 1–4 when the tuning agent produced recommendations.

### Phase 0.6: Present the tuning agent's recommendations

For each recommendation, show its title, reasoning and change summary, and the affected asset
for table monitors. Flag every `would_reset: true`: applying it resets the monitor's learned
thresholds, and it relearns from scratch. A recommendation whose `recommendation_type` is
`advisory` is a note to relay, not a change to apply. If the monitor is `is_template_managed`
(Phase 5 says where to read it), it is deployed with Monitors-as-Code: show the recommendations
but do not offer to apply them.

**Next step:** "Which of these do you want me to apply?" Nothing is applied until the user names
the changes.

---

## Phase 1: Fetch Monitor Report (fallback)

Phases 1–4 run only when Phase 0.5 sends you here: `skip_reason` set (other than a deleted monitor
or collection failure), or the tuning agent failed.

Call `get_monitor_report` with:
- `monitor_uuid`: the UUID resolved in Phase 0
- `max_incidents`: 50

If the tool returns an error or empty result, tell the user the monitor was not found and stop.

Also fetch the monitor's full config via `get_monitors` with:
- `monitor_ids`: [`{monitor_uuid}`]
- `include_fields`: [`config`]

Run both calls in parallel.

---

## Phase 1.5: Determine Monitor Type and Load Reference

From the `get_monitors` config response, determine the monitor type:

| Config indicator | Type | Reference file |
|---|---|---|
| Monitor type is a metric monitor variant (e.g., metric, field health) | Metric | `references/metric-monitor.md` |
| Monitor type is a custom SQL rule / custom monitor | Custom SQL | `references/custom-sql-monitor.md` |
| Monitor type is a validation rule / validation monitor | Validation | `references/validation-monitor.md` |
| Monitor type is a table monitor (freshness, volume, schema across tables) | Table | `references/table-monitor.md` |
| Monitor type is an agent metric monitor (metric over an AI agent's trace table) | Agent metric | `references/agent-metric-monitor.md` |
| Monitor type is an agent evaluation monitor (LLM-judge / SQL transforms over sampled agent traffic) | Agent evaluation | `references/agent-evaluation-monitor.md` |
| Monitor type is an agent trajectory monitor (span-pattern rule over an agent's traces) | Agent trajectory | `references/agent-trajectory-monitor.md` |
| Monitor type is an agent validation monitor (predicate rule flagging invalid span rows) | Agent validation | `references/agent-validation-monitor.md` |

**Read** the appropriate reference file using the Read tool with the path relative to this skill
file. The reference contains type-specific config fields to extract, recommendation guidance, and
apply-changes instructions.

If the monitor type is not metric, custom SQL, validation, table, or one of the agent monitor
types (metric, evaluation, trajectory, validation), stop and tell the user:

> This skill supports tuning metric, custom SQL, validation, table, and agent (metric,
> evaluation, trajectory, validation) monitors. This monitor is a {type} monitor, which is not
> supported.

---

## Phase 2: Analyze the Report

Analyze the monitor report and config together. Focus on:

### 2a. Alert volume & frequency
- How many incidents in the last 30 days? Last 7 days?
- What is the firing cadence — multiple times per day? Daily? Sporadic?
- Are incidents clustered in time (bursts) or spread evenly?

### 2b. Anomaly patterns
- Which segments (field values) are firing most? Are they the same segments repeatedly?
- Are anomalies consistently marginal (just above threshold) or severe?
- Are any anomalies from sparse/bursty event types that naturally spike?
- Are anomalies caused by known operational events (deployments, batch jobs, bulk user actions)?
- For validation monitors: how many invalid rows per incident? Is the count stable or growing?
- For table monitors: which (table, metric) pairs are firing most? Are they the same repeatedly?

### 2c. Current configuration
Extract the current configuration. The specific fields to look for are documented in the per-type
reference loaded in Phase 1.5. At minimum, extract:
- Monitor type and what it measures
- Schedule interval
- Audiences / notification channels
- Whether the monitor uses ML thresholds or explicit thresholds
- The value of every setting you might propose changing — sensitivity, thresholds, the time bucket
  it aggregates on, its filter, and the segments it already excludes

That last item is what Phase 3 checks each recommendation against, so extract it even where nothing
about the report suggests the setting is the problem. Write the values down in your analysis; a
setting you never read is one you cannot tell you are about to re-propose.

### 2d. Troubleshooting analysis (if available)
Look at any troubleshooting TL;DRs in the report. Note:
- Are most anomalies assessed as "likely normal data variation"?
- Are there recurring root causes?
- Is there a blind spot (e.g., no upstream metadata)?

---

## Phase 3: Generate Recommendations

Based on the analysis, produce a prioritized list of recommendations. For each recommendation:
- State the **problem** it solves
- Give the **specific config change** (use exact field names from the MC config schema)
- Explain the **trade-off** (what signal might be lost)

**Check every change against the value you read in 2c.** Reading the configuration is the floor,
not the point — a lever the monitor is already set to is not a recommendation, it is a report that
the user's change did not take, and it costs them a second attempt at something already done.
Before naming a lever, find it in what you extracted and confirm the monitor is not already there.
If it is, say so under **What NOT to change** and spend the slot on a lever that would actually
move. This binds the heading as tightly as the body: a recommendation titled *"switch to weekly
buckets"* on a monitor already bucketing weekly reads as advice to re-apply it, whatever the
paragraph underneath goes on to say.

The same applies to a change someone made recently. The report covers a window; the configuration
is only as of now. If `last_update_time` is more recent than the alerts you are reasoning from,
those alerts fired under an older configuration — say so, and check each lever against the current
values rather than against what the alert pattern implies the monitor used to be set to.

A per-type reference can limit which levers exist for a monitor, or say that the right outcome is
no change. When it does, follow it: it overrides the instruction above to spend the slot on
another lever, and any general recommendation below that conflicts with it. Other general
recommendations still apply. Report a no-change outcome with the no-change form of the Phase 4
template.

### General recommendations (all monitor types)

#### Sensitivity tuning (ML thresholds only)
This applies to any monitor that uses ML thresholds — both metric monitors and custom SQL monitors.
Skip this section for validation monitors (they don't use ML thresholds), for table monitors
(they have their own per-metric sensitivity — see the table monitor reference), for agent
trajectory and agent validation monitors (no thresholds or sensitivity at all — see their
references), and for monitors with explicit thresholds (for custom SQL monitors, see threshold
adjustment in the per-type reference instead).

- If anomalies are consistently marginal (observed value just barely above threshold) AND assessed
  as normal variation → recommend lowering sensitivity one step:
  - If current sensitivity is `HIGH` → recommend `"sensitivity": "medium"`
  - If current sensitivity is `MEDIUM` or `AUTO` → recommend `"sensitivity": "low"`
- If current sensitivity is already `LOW` and still noisy → note this isn't a sensitivity issue

#### Schedule / interval
- If the monitor fires multiple times per day but anomalies always resolve within hours → recommend
  increasing schedule interval (e.g., from 720 min to 1440 min) to reduce duplicate alerts
- If anomalies are caused by data arriving late → recommend increasing `collection_lag`

#### Snooze / training period
- If the monitor was recently created (<30 days) and is still learning patterns → recommend
  waiting for the model to stabilize before tuning

#### Audience / notification routing
- If the monitor has no audiences configured and is generating noise → recommend adding audiences
  only for high-severity anomalies, or removing notifications entirely for known-noisy monitors

### Type-specific recommendations

For type-specific recommendations (WHERE conditions, segment exclusion, aggregation changes,
threshold adjustment, SQL modifications, alert condition modifications, per-table-metric
sensitivity tuning), follow the guidance in the per-type reference loaded in Phase 1.5.

---

## Phase 4: Present the Report

Output a structured analysis. **This is the primary output — include it in full.**

```markdown
## Monitor Tune Report: {monitor_uuid}

**Monitor:** {display_name or mac_name}
**Type:** {monitor type — metric, custom SQL, validation, table, or an agent monitor type}
**Table:** {table}
**What it monitors:** {metric and segments, SQL query summary, validation conditions, or table/metric coverage}
**Current sensitivity:** {sensitivity or "AUTO (default)" or "N/A (explicit thresholds)"}
**Schedule:** every {interval_minutes / 60}h

### Alert Summary (last 30 days)
- Total alerts: {count}
- Firing frequency: {e.g., "~twice daily", "daily", "sporadic"}
- Most noisy segments: {top 2-3 segment values by alert count, or N/A for custom SQL/validation}
- Most noisy (table, metric) pairs: {for table monitors: top pairs by anomaly count}

### Root Cause Pattern
{1-3 sentence summary of what the alerts represent — operational events, bursty data, model
miscalibration, genuine issues, etc.}

### Recommendations

#### 1. {Highest-impact change} [RECOMMENDED]
**Problem:** ...
**Change:**
```yaml
{specific config field}: {new value}
```
**Trade-off:** ...

#### 2. {Second change} [OPTIONAL]
...

#### 3. {Third change} [OPTIONAL]
...

{If the per-type reference says the monitor should stay as it is, replace the numbered list with
**No change recommended** and one or two sentences of evidence, and list the settings left alone
under What NOT to change. Omit **If these changes are made** when no change is recommended.}

### What NOT to change
{Any configurations that look correct and should be left alone — avoid over-tuning.}

### If these changes are made
{Predict the expected outcome: estimated alert reduction, what genuine anomalies would still fire.}
```

**Next step:** "Want me to apply any of these changes to the monitor config, or explore the alert
history further?" When nothing is recommended, offer only the alert-history exploration.

---

## Phase 5: Apply Changes (if user requests)

**Tuning agent recommendations:** check freshness first. Which check depends on where the
approved recommendations came from:
- **A stored analysis** (from `get_monitor_tuning_suggestions`, or handed off by remediation with
  its `run_uuid` and `analyzed_at`): call `get_monitor_tuning_suggestions()` with no arguments.
  Apply only if the monitor's row is there with the same `run_uuid` as the analysis the user
  approved; read `is_template_managed` from that row. If the row is missing or carries a different
  `run_uuid` (the monitor was edited, the suggestion was dismissed or aged out, or a newer
  analysis replaced it), do not apply. Preview with `tune_monitor(monitor_uuid=<uuid>)`, present
  the result (Phase 0.6), say what differs from what the user approved, and wait for a new
  approval.
- **A preview you ran with `tune_monitor` in this conversation:** it is current. Read
  `is_template_managed` and `recommendation_type` from the preview response.

For a monitor with `is_template_managed: true`,
do not call `tune_monitor`: hand off to the manage-mac skill so the user edits their
Monitors-as-Code YAML. Otherwise leave out `advisory` items (relay them only) and call
`tune_monitor(monitor_uuid=<uuid>, dry_run=false, recommendations=[<the approved subset>])`.
Pass the approved recommendations back exactly as returned. Leaving `recommendations` out
re-analyzes the monitor and applies whatever that finds, which is not what the user approved.
Report `apply_result` and any `skip_reason`.

**Your own recommendations (from the Phases 1–4 fallback):** follow the apply-changes
instructions in the per-type reference loaded in Phase 1.5. Each reference specifies the correct
tool and constraints for that monitor type.

General rules. Rule 2 applies to both paths above; rules 1, 3 and 4 apply only to your own
recommendations (the `create_or_update_*` path). On the tuning agent path, the user's approval of
the shown recommendations is the preview, and `is_template_managed` is the Monitors-as-Code check.
1. **Always preview first** — show the user what will change before applying.
2. **Get explicit confirmation** before applying any change.
3. **Validate the preview YAML against the schema** — before presenting the preview YAML to the user, fetch the published MaC JSON Schema from `https://clidocs.getmontecarlo.com/mac/schema.json` (WebFetch) and check the preview YAML against it. If any field in the YAML does not appear in the schema for the given monitor type, flag it and correct it. Note: the schema validates field names, types, and enum values only — cross-field semantic constraints are enforced by the backend at apply time, not by the schema.
4. **MaC-managed monitors** — if `get_monitors` returns a `mac_name` or the user mentions the monitor is managed via a MaC YAML file, note this before applying: changes made via the API will be overwritten the next time `montecarlo monitors apply` runs. Offer to hand off to `/manage-mac` (edit workflow) instead so the YAML file stays the source of truth.

---

## Guidelines

- **Be specific.** Generic advice like "reduce sensitivity" is less useful than exact config changes.
- **Prefer surgical changes.** A targeted WHERE condition beats a blunt sensitivity reduction.
- **Preserve signal.** Always explain what genuine anomalies would still be caught after tuning.
- **Cite evidence.** Reference specific incident dates, segment values, and counts from the report.
- **Degrade gracefully.** If troubleshooting runs are missing, note the limited context and
  reason from alert patterns alone.
- **Add `$schema` when saving YAML to a file.** If the user asks to save the MaC YAML to a file, add `# yaml-language-server: $schema=https://clidocs.getmontecarlo.com/mac/schema.json` as the first line of that file.
