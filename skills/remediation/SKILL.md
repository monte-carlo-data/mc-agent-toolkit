---
name: monte-carlo-remediation
description: |
  Activates when a user asks to remediate, fix, or respond to a data quality alert
  or incident. Investigates the alert using Monte Carlo MCP tools (alerts, TSA root
  cause analysis, lineage, table metadata), discovers what remediation tools are
  available via connected MCP servers, reasons about the appropriate fix, and
  executes it — or escalates to a human with full context when uncertain. Do not
  wait to be asked for details: once activated, run the full investigation workflow
  before proposing any action.
version: 1.0.0
---

# Monte Carlo Remediation Skill

This skill teaches you to investigate and remediate data quality issues detected by Monte Carlo. You use MC MCP tools to understand the alert context, run root cause analysis, assess blast radius, and then execute the appropriate remediation action using whatever external tools the user has connected.

Reference files live next to this skill file. **Use the Read tool** (not MCP resources) to access them:

- Common remediation patterns and examples: `references/patterns.md` (relative to this file)
- How to discover available tools at runtime: `references/tool-discovery.md` (relative to this file)
- Safety rails and escalation criteria: `references/safety.md` (relative to this file)

## When to activate this skill

Activate when the user:

- Asks to remediate, fix, or respond to a data quality alert or incident
- Mentions a specific alert ID, incident, or data quality issue they want resolved
- Says something like "fix the freshness issue on X", "remediate this alert", "handle this incident"
- Asks to triage AND fix an alert (triage alone without remediation intent → use the prevent skill's Workflow 3 instead)
- Wants to automate a response to a recurring data quality pattern
- Asks "what should I do about this alert?" or "how do I fix this?"

## When NOT to activate this skill

Do not activate when the user is:

- Just triaging or investigating an alert without remediation intent (use prevent skill's Workflow 3)
- Creating or configuring monitors (use the monitor-creation skill)
- Running a change impact assessment before code changes (use the prevent skill's Workflow 4)
- Asking about general data quality best practices without a specific incident
- Exploring table health or lineage without an active issue to fix

---

## Available MCP tools

### Monte Carlo tools (investigation + post-remediation)

All tools are available via the `monte-carlo` MCP server.

| Tool | Purpose |
| ---- | ------- |
| `getAlerts` | Fetch alert details — type, severity, affected tables, timestamps |
| `alertAssessment` | Triage confidence + impact score — use as a gate before running TSA |
| `runTroubleshootingAgent` | Launch TSA root cause analysis (async — returns immediately) |
| `getTroubleshootingAgentResults` | Poll for TSA results — contains root cause `tldr` and detailed findings |
| `getAssetLineage` | Upstream producers and downstream consumers — blast radius assessment |
| `getTable` | Table schema, stats, freshness, volume, capabilities, monitoring status |
| `getMonitors` | Existing monitoring coverage on affected tables |
| `getQueriesForTable` | Recent query patterns — helps distinguish pipeline issues from ad-hoc problems |
| `search` | Find assets by name when you don't have the MCON |
| `updateAlert` | Update alert status (ACKNOWLEDGED, FIXED, EXPECTED, etc.) and severity |
| `setAlertOwner` | Assign alert ownership to a specific user |
| `createOrUpdateAlertComment` | Document findings and remediation actions on the alert |
| `getCurrentTime` | ISO timestamp for API calls that need date ranges |

### External tools (remediation execution)

These are **not** Monte Carlo tools. They come from external MCP servers the user may have configured. Their availability varies — see Workflow 2 (Capability Discovery) for how to detect them at runtime.

| Capability | Example MCP Servers | Example Tools |
| ---------- | ------------------- | ------------- |
| Pipeline orchestration | Airflow, Dagster, Prefect | `trigger_dag_run`, `get_task_status`, `retry_task` |
| dbt operations | dbt Cloud | `trigger_run`, `get_run`, `list_jobs` |
| Code changes | GitHub, GitLab | `create_pull_request`, `create_issue`, `create_branch` |
| Notifications | Slack, PagerDuty, Teams | `send_message`, `create_incident`, `post_message` |
| Data warehouse | Snowflake, BigQuery, Databricks | `execute_query`, `get_table_info` |

---

## Core workflow

Follow these workflows in order. Each workflow builds on the context gathered by the previous one.

### Workflow 1: Investigation

**Goal:** Understand what happened, why it happened, and what's affected.

Before proposing ANY remediation action, you MUST complete this investigation. Do not skip steps — incomplete context leads to wrong fixes.

#### Step 1: Get alert context

```
getAlerts(
  alert_ids=["<alert_id>"],
)
```

If the user provided a table name instead of an alert ID:
```
search(query="<table_name>")
→ extract MCON
getAlerts(
  table_mcons=["<mcon>"],
  created_after="<7 days ago>",
  created_before="<now>",
  order_by="-createdTime",
  statuses=["NOT_ACKNOWLEDGED", "WORK_IN_PROGRESS"]
)
```

Extract from the alert: `alert_type` (Freshness, Volume, Schema Changes, etc.), `severity`, affected table MCONs, `created_time`.

#### Step 2: Assess triage priority

```
alertAssessment(
  incident_id="<alert_uuid>"
)
```

This returns `triage_confidence` (HIGH/MEDIUM/LOW), `alert_impact` (HIGH/MEDIUM/LOW), and a summary. Use this to decide urgency:

- **HIGH impact + HIGH confidence** → proceed immediately to TSA
- **LOW impact or LOW confidence** → still run TSA, but note to the user that this may not warrant immediate remediation

#### Step 3: Root cause analysis (TSA)

```
runTroubleshootingAgent(
  incident_id="<alert_uuid>",
  async_mode=true
)
```

Then poll for results (wait 30s initially, then 60s intervals):
```
getTroubleshootingAgentResults(
  incident_id="<alert_uuid>"
)
```

Status values:
- `not_found` → TSA hasn't been triggered yet
- `running` → still analyzing (keep polling)
- `success` → read the `tldr` for the root cause summary, `full_response` for details
- `failed` → check `full_response` for error; proceed with manual investigation

**The TSA `tldr` is your primary input for choosing a remediation action.** Read it carefully.

#### Step 4: Assess blast radius

```
getAssetLineage(
  mcons=["<affected_table_mcon>"],
  direction="DOWNSTREAM"
)
```

Then for upstream investigation:
```
getAssetLineage(
  mcons=["<affected_table_mcon>"],
  direction="UPSTREAM"
)
```

Note: `has_relationships=false` means no dependencies tracked — do not assume missing relationships.

#### Step 5: Gather table context

```
getTable(
  mcon="<affected_table_mcon>",
  include_fields=true,
  include_table_capabilities=true
)
```

Extract: last activity timestamps, row counts, schema, monitoring status, importance score.

For key downstream tables identified in Step 4, also fetch their details:
```
getTable(mcon="<downstream_mcon>")
```

#### Step 6: Check monitoring coverage and recent queries

```
getMonitors(mcons=["<affected_table_mcon>"])
```

```
getQueriesForTable(
  mcon="<affected_table_mcon>",
  query_type="destination",
  limit=10
)
```

Use `query_type="destination"` to find queries that write to this table (pipeline queries). This helps identify which pipeline or job is responsible for the data.

#### Investigation summary

After completing Steps 1–6, synthesize your findings into a clear summary:

1. **What happened:** alert type, when it fired, severity
2. **Root cause:** TSA findings (or your best assessment if TSA failed)
3. **Blast radius:** N downstream consumers, any key assets affected
4. **Pipeline context:** which queries/jobs write to this table, when they last ran
5. **Monitoring:** what monitors exist, any gaps

Present this summary to the user before proceeding to remediation.

---

### Workflow 2: Capability discovery

**Goal:** Determine what remediation actions are possible given the tools you have available.

Before attempting any remediation action, you must know what tools you can use. You cannot assume any external MCP server is connected.

#### How tool discovery works

Your available tools are listed in your system prompt or tool inventory. External MCP tools follow the naming convention `mcp__<server_name>__<tool_name>`.

Scan your available tools and look for these patterns:

| Pattern | Capability | What you can do |
| ------- | ---------- | --------------- |
| `mcp__*airflow*__*` | Pipeline orchestration (Airflow) | Trigger DAG runs, retry failed tasks, check task status |
| `mcp__*dagster*__*` | Pipeline orchestration (Dagster) | Trigger pipeline runs, check run status |
| `mcp__*prefect*__*` | Pipeline orchestration (Prefect) | Trigger flow runs, check run status |
| `mcp__*dbt*__*` | dbt operations | Trigger dbt job runs, check run status, list jobs |
| `mcp__*github*__*` | Code changes | Create PRs, open issues, create branches |
| `mcp__*gitlab*__*` | Code changes | Create merge requests, open issues |
| `mcp__*slack*__*` | Notifications | Send messages, post to channels |
| `mcp__*pagerduty*__*` | Incident management | Create/escalate incidents, notify on-call |
| `mcp__*snowflake*__*`, `mcp__*bigquery*__*`, `mcp__*databricks*__*` | Data warehouse | Run queries, inspect tables directly |

**If a capability is not found:** That's fine. Not every remediation requires every tool. The skill degrades gracefully — see "Graceful degradation" below.

#### Capability assessment

After scanning, summarize what's available:

> "Based on your connected MCP servers, I can:
> - ✅ Investigate via Monte Carlo (always available)
> - ✅/❌ Restart pipelines (Airflow/Dagster/Prefect)
> - ✅/❌ Rerun dbt jobs (dbt Cloud)
> - ✅/❌ Create code changes (GitHub/GitLab)
> - ✅/❌ Send notifications (Slack/PagerDuty)
> - ✅/❌ Query the warehouse directly"

For detailed guidance on tool discovery, read `references/tool-discovery.md`.

#### Graceful degradation

When the needed execution tool is NOT available:

1. **Always produce the remediation plan** — describe exactly what needs to happen, step by step
2. **Provide runnable commands** — if the fix is "restart this Airflow DAG", give the user the `airflow dags trigger <dag_id>` command they can run manually
3. **Escalate via available channels** — if Slack is connected but Airflow isn't, post the remediation plan to the appropriate channel
4. **Document on the alert** — use `createOrUpdateAlertComment` to record the diagnosis and recommended fix, even if you can't execute it

---

### Workflow 3: Remediation execution

**Goal:** Take the appropriate action to fix the root cause, with safety rails.

Read `references/patterns.md` for detailed examples of common remediation patterns.

#### Step 1: Select remediation action

Based on the TSA root cause and available tools, determine the action:

| Root Cause Signal (from TSA) | Typical Remediation | Required Capability |
| ---------------------------- | ------------------- | ------------------- |
| Pipeline/DAG failure or delay | Restart the failed pipeline or task | Pipeline orchestration |
| dbt model failure | Rerun the failed dbt job | dbt operations |
| Schema change (upstream) | Assess impact, update downstream models or revert | Code changes |
| Volume anomaly (missing data) | Check upstream pipeline, trigger backfill | Pipeline orchestration + warehouse |
| Volume anomaly (duplicate data) | Identify and remove duplicates, fix pipeline | Warehouse + code changes |
| Permission/access error | Escalate to data platform team | Notifications |
| Infrastructure issue | Escalate to platform/ops team | Notifications |
| Unknown or complex root cause | Escalate with full context | Notifications |

**If the root cause maps to multiple possible actions**, present the options to the user with tradeoffs and let them choose.

**If the root cause doesn't clearly map to any pattern**, read `references/patterns.md` for the "Unknown / complex" pattern, which focuses on packaging context for escalation.

#### Step 2: Present the remediation plan

**BEFORE executing anything**, present the plan to the user:

> "Based on the investigation:
>
> **Root cause:** [TSA summary]
> **Proposed action:** [what you want to do]
> **Reasoning:** [why this action addresses the root cause]
> **Risk:** [what could go wrong, blast radius]
> **Rollback:** [how to undo if the fix causes new problems]"

Read `references/safety.md` for detailed safety protocols.

#### Step 3: Execute (with safety rails)

**Safety rules — these are non-negotiable:**

1. **Always explain before executing.** Never run a remediation action without first telling the user what you're about to do and why.

2. **Confirm destructive operations.** Any action that modifies data, restarts a pipeline, triggers a job, or changes configuration requires explicit user confirmation. Ask and wait for "yes", "go ahead", "proceed", or similar.

3. **Escalate when uncertain.** If you're not confident the action will fix the issue without side effects, say so. Present what you know, what you're unsure about, and recommend the user verify before proceeding.

4. **One action at a time.** Don't chain multiple remediation actions. Execute one, verify the result, then decide on the next step.

5. **Log everything.** After each action, document what you did on the alert using `createOrUpdateAlertComment`.

#### Step 4: Verify the fix

After executing the remediation action, verify it worked:

1. **Wait for the action to take effect** — pipeline runs take time, dbt jobs need to complete
2. **Re-check the table:**
   ```
   getTable(mcon="<affected_table_mcon>")
   ```
   Check: has `last_activity` updated? Have row counts changed as expected?

3. **Re-check the alert:**
   ```
   getAlerts(alert_ids=["<alert_id>"])
   ```
   Has the alert auto-resolved? Is the condition still firing?

4. **Report to the user:**
   > "Remediation result:
   > - Action taken: [what was done]
   > - Table status: [current freshness/volume/schema state]
   > - Alert status: [resolved/still firing]
   > - Next steps: [if any]"

---

### Workflow 4: Post-remediation

**Goal:** Close out the incident properly — update status, document, and prevent recurrence.

#### Step 1: Update the alert

```
updateAlert(
  alert_id="<alert_uuid>",
  status="FIXED"
)
```

Use the appropriate status:
- `FIXED` — the root cause was identified and remediated
- `EXPECTED` — the alert fired on expected behavior (e.g., planned maintenance)
- `NO_ACTION_NEEDED` — the issue resolved itself or is not actionable

#### Step 2: Document the remediation

```
createOrUpdateAlertComment(
  alert_id="<alert_uuid>",
  comment="## Remediation Summary\n\n**Root cause:** [TSA findings]\n**Action taken:** [what was done]\n**Result:** [outcome]\n**Remediated by:** AI agent via remediation skill\n**Timestamp:** [ISO timestamp]"
)
```

#### Step 3: Assign ownership (if escalated)

If the issue was escalated or needs follow-up:
```
setAlertOwner(
  alert_id="<alert_uuid>",
  owner="<owner_email>"
)
```

#### Step 4: Consider prevention

After remediating, briefly assess whether this issue is likely to recur:

- **If the root cause is systemic** (e.g., a flaky pipeline, a missing monitor): suggest adding a monitor or creating a ticket to address the underlying issue
- **If it was a one-off** (e.g., infrastructure blip, manual error): document and move on

Do not automatically create monitors or tickets — suggest them and let the user decide.

---

## Common mistakes to avoid

- **NEVER execute a remediation action without presenting the plan first.** The user must understand what you're about to do.
- **NEVER skip the investigation phase.** A wrong diagnosis leads to a wrong fix — or worse, a fix that causes new problems.
- **NEVER assume external MCP tools are available.** Always check first. A missing tool is not an error — it just means you escalate instead of execute.
- **NEVER chain multiple remediation actions without verifying each one.** One action at a time.
- **NEVER modify data directly** (DELETE, UPDATE, DROP) without explicit user confirmation AND a clearly stated rollback plan.
- **NEVER mark an alert as FIXED before verifying the fix.** Check that the underlying condition has actually improved.
- **NEVER remediate silently.** Always document what was done via `createOrUpdateAlertComment`.
