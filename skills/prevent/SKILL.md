---
name: monte-carlo-prevent
description: Shift-left safety net for dbt/SQL model edits. Surfaces health context (via asset-health), runs change impact assessment before edits, generates SQL validation queries after, and offers monitor generation (via monitoring-advisor) post-edit.
when_to_use: |
  Invoke when the user expresses intent to change a dbt or SQL model — adding, dropping, renaming, refactoring a column or filter, fixing a bug in model logic, tweaking a parameter, or referencing a model file paired with an edit verb.
  Example triggers: "add an is_active column to client_hub", "refactor the join logic in stg_payments", "drop the legacy_id column from dim_users", "@models/orders.sql add a filter".

  Do NOT invoke for:
  - Plain health questions about a table ("how is X doing?", "is X healthy?") — those go to monte-carlo-asset-health.
  - Alert investigation or incident triage ("freshness alert on X", "why did X fail?") — those go to monte-carlo-automated-triage or monte-carlo-incident-response.
  - Standalone monitor creation requests without an edit context ("create a monitor for X", "what should I monitor?", "show coverage gaps") — those go to monte-carlo-monitoring-advisor.
  - Performance or pipeline diagnosis ("why is X slow?", "investigate the query plan") — those go to monte-carlo-performance-diagnosis.
  - Edits to non-model files: seed CSVs (seeds/), analysis files (analyses/), dbt config (dbt_project.yml, profiles.yml, packages.yml).
  - Bare file opens or reads without an edit verb ("open stg_orders.sql so I can see what it does") — that's navigation, not change intent.
version: 1.0.0
---

# Monte Carlo Prevent Skill

This skill brings Monte Carlo's data observability context directly into your editor. When you're modifying a dbt model or SQL pipeline, use it to surface table health, lineage, active alerts, and to generate monitors-as-code without leaving Claude Code.

Reference files live next to this skill file. **Use the Read tool** (not MCP resources) to access them:

- Full workflow step-by-step instructions: `references/workflows.md` (relative to this file)
- MCP parameter details: `references/parameters.md` (relative to this file)
- Troubleshooting: `references/TROUBLESHOOTING.md` (relative to this file)

## When to activate this skill

**Prevent is the edit-lifecycle skill.** Activate only when the user expresses
intent to change a dbt model. Bare file mentions, table-name mentions in
passing, or general health questions are **not** prevent's territory — those
belong to `monte-carlo-asset-health` and will activate that skill on their own.

**Do not wait to be asked.** Run the appropriate workflow automatically whenever the user:

- Describes a planned change to a model (new column, join update, filter change, refactor) → **STOP — run Workflow 1 first if it has not run for this table this session, then Workflow 2, before writing any code**
- Adds a new column, metric, or output expression to an existing model → same rule: Workflow 1 first (if not yet run for this table), then Workflow 2; the post-edit hook will offer Workflow 6 (monitor generation) afterward
- References a model file with an edit verb in the same prompt (e.g. `@models/clients/client_hub.sql add an is_active column`) → same rule: Workflow 1 first, then Workflow 2

Present the W2 impact assessment as context the engineer needs before proceeding — not as a response to a question.

### Workflow 1 runs silently when chained to Workflow 2

When the user expresses change intent, Workflow 1 invokes `monte-carlo-asset-health`
purely as a data-gathering step. Read asset-health's report from your context, but
**do not relay the full report to the engineer** — the user-facing artifact is
Workflow 2's impact assessment, which already cites the relevant alerts / lineage /
monitors. Showing both creates duplicate reading.

Two exceptions where you **must** surface output from W1 to the engineer:

1. **Disambiguation prompt.** If asset-health returns multiple matches and asks
   the engineer to pick one, surface that question — the user must choose.
2. **Stop-the-world signals.** If the table is already on fire (active critical
   alerts firing, freshness severely stale), say so in one short line before W2.

If Workflow 1 already ran for this table earlier in the session, skip directly
to Workflow 2 — re-running asset-health is redundant.

## When NOT to activate this skill

Do not invoke Monte Carlo tools for:

- Seed files (files in seeds/ directory)
- Analysis files (files in analyses/ directory)
- One-off or ad-hoc SQL scripts not part of a dbt project
- Configuration files (dbt_project.yml, profiles.yml, packages.yml)
- Test files unless the user is specifically asking about data quality

If uncertain whether a file is a dbt model, check for {{ ref() }} or {{ source() }}
Jinja references — if absent, do not activate.

### Macros and snapshots — gate edits, skip auto-context

Macro files (`macros/`) and snapshot files (`snapshots/`) are **not** models, so
do not auto-fetch Monte Carlo context (Workflow 1) when they are opened. However,
macros are inlined into every model that calls them at compile time — a one-line
macro change can silently alter dozens of models. Snapshots control historical
tracking and are similarly sensitive.

**The pre-edit hook gates these files.** If the hook fires for a macro or snapshot,
identify which models are affected and run the change impact assessment (Workflow 2)
for those models before proceeding with the edit.

### Peer-skill redirects

These requests have their own skills — do not run prevent for them:

- "How is table X doing?" / "is X healthy?" / "check status of X" → `monte-carlo-asset-health`
- "Create a monitor for X" / "what should I monitor?" / "set up freshness on X" (without an active edit context) → `monte-carlo-monitoring-advisor`

Prevent invokes asset-health and monitoring-advisor itself when its workflows
need them (W1, W6); it does not duplicate their entry points.

---

## REQUIRED: Change impact assessment before any SQL edit

**Before editing or writing any SQL for a dbt model or pipeline, you MUST run Workflow 2.**

This applies whenever the user expresses intent to modify a model — including phrases like:

- "I want to add a column…"
- "Let me add / I'm adding…"
- "I'd like to change / update / rename…"
- "Can you add / modify / refactor…"
- "Let's add…" / "Add a `<column>` column"
- Any other description of a planned schema or logic change
- "Exclude / filter out / remove [records/customers/rows]…"
- "Adjust / increase / decrease [threshold/parameter/value]…"
- "Fix / bugfix / patch [issue/bug]…"
- "Revert / restore / undo [change/previous behavior]…"
- "Disable / enable [feature/logic/flag]…"
- "Clean up / remove [references/columns/code]…"
- "Implement [backend/feature] for…"
- "Create [models/dbt models] for…" (when modifying existing referenced tables)
- "Increase / decrease / change [max_tokens/threshold/date constant/numeric parameter]…"
- Any change to a hardcoded value, constant, or configuration parameter within SQL
- "Drop / remove / delete [column/field/table]"
- "Rename [column/field] to [new name]"
- "Add [column]" (short imperative form, e.g. "add a created_at column")
- Any single-verb imperative command targeting a column, table, or model
  (e.g. "drop X", "rename Y", "add Z", "remove W")

Parameter changes (threshold values, date constants, numeric limits) appear
safe but silently change model output. Treat them the same as logic changes
for impact assessment purposes.

**Do not write or edit any SQL until the change impact assessment (Workflow 2) has been presented to the user.** The assessment must come first — not after the edit, not in parallel.

---

## Pre-edit gate — check before modifying any file

**Before calling Edit, Write, or MultiEdit on any `.sql` or dbt model
file, you MUST check:**

1. Has the synthesis step been run for THIS SPECIFIC CHANGE in the
   current prompt?
2. **If YES** → proceed with the edit
3. **If NO** → stop immediately, run Workflow 2, present the full
   report with synthesis connected to this specific change.
   **If risk is High or Medium:** ask "Do you want me to proceed
   with the edit?" and wait for explicit confirmation.
   **If risk is Low:** use judgment — proceed if straightforward
   and no concerns found, otherwise ask before editing.

**Important: "Workflow 2 already ran this session" is NOT sufficient
to proceed.** Each distinct change prompt requires its own synthesis
step connecting the MC findings to that specific change.

The synthesis must reference the specific columns, filters, or logic
being changed in the current prompt — not just general table health.

Example:

- ✅ "Given 34 downstream models depend on is_paying_workspace,
  adding 'MC Internal' to the exclusion list will exclude these
  workspaces from all downstream health scores and exports.
  Confirm?"
- ❌ "Workflow 2 already ran. Making the edit now."

The only exception: if the user explicitly acknowledges the risk
and confirms they want to skip (e.g. "I know the risks, just make
the change") — proceed but note the skipped assessment.

## Available MCP tools

All tools are available via the `monte-carlo` MCP server.

| Tool                         | Purpose                                                              |
| ---------------------------- | -------------------------------------------------------------------- |
| `testConnection`             | Verify auth and connectivity                                         |
| `search`                     | Find tables/assets by name                                           |
| `getTable`                   | Schema, stats, metadata for a table                                  |
| `getAssetLineage`            | Upstream/downstream dependencies (call with mcons array + direction) |
| `getAlerts`                  | Active incidents and alerts                                          |
| `getMonitors`                | Monitor configs — filter by table using mcons array                  |
| `getQueriesForTable`         | Recent query history                                                 |
| `getQueryData`               | Full SQL for a specific query                                        |
| `createValidationMonitorMac` | Generate validation monitors-as-code YAML                            |
| `createMetricMonitorMac`     | Generate metric monitors-as-code YAML                                |
| `createComparisonMonitorMac` | Generate comparison monitors-as-code YAML                            |
| `createCustomSqlMonitorMac`  | Generate custom SQL monitors-as-code YAML                            |
| `getValidationPredicates`    | List available validation rule types                                 |
| `getAudiences`               | List notification audiences                                          |
| `getDomains`                 | List MC domains                                                      |
| `getUser`                    | Current user info                                                    |
| `getCurrentTime`             | ISO timestamp for API calls                                          |

## Core workflows

Each workflow has detailed step-by-step instructions in `references/workflows.md` (Read tool).

### 1. Asset health pre-fetch (silent delegation to asset-health)

**When:** User expresses change intent for a table that hasn't been seen in this session.
**What:** Invokes `monte-carlo-asset-health` via the Skill tool to gather table state (health, lineage, alerts, monitors). The report is **used as data for Workflow 2**, not shown to the engineer. Two exceptions surface to the user: any disambiguation prompt, and stop-the-world signals (active critical alerts, severe staleness).

### 2. Change impact assessment — REQUIRED before modifying a model

**When:** Any intent to modify a dbt model's logic, columns, joins, or filters.
**What:** Surfaces blast radius, downstream dependencies, active incidents, monitor coverage, and query exposure. Reuses asset-health's data when Workflow 1 ran earlier this session; otherwise calls `get_table` / `get_alerts` / `get_asset_lineage` / `get_monitors` directly. Produces a risk-tiered report with synthesis connecting findings to specific code recommendations.

### 3. Change validation queries

**When:** Explicit engineer request only (e.g. "validate this change", "ready to commit"), or via `/mc-validate run`.
**What:** Generates 3–5 targeted SQL queries to verify the change behaved as intended. Uses Workflow 2 context — requires both impact assessment and file edit in session.

### 4. *(reserved)* Sandbox build — invoked by `/mc-validate run`

Lands when `achen/mc-validate-run` merges. See that branch's design.

### 5. *(reserved)* Execute validation queries — invoked by `/mc-validate run`

Lands when `achen/mc-validate-run` merges. See that branch's design.

### 6. Add monitor (delegated to monitoring-advisor, post-edit)

**When:** Post-edit hook injects the coverage prompt (driven by `MC_MONITOR_GAP` from Workflow 2), or the engineer explicitly asks to add a monitor.
**What:** Asks "Generate monitor definitions? (yes/no)". On yes, invokes `monte-carlo-monitoring-advisor` via the Skill tool with the model name and changed columns/logic. Prevent's responsibility ends at delegation — it does not wait for monitoring-advisor or emit a completion marker.

---

## Post-synthesis confirmation rules

Always end the synthesis with one clear, specific recommendation in plain English:
"Given the above, I recommend: [specific action]"

**If the risk is High or Medium:** STOP and wait for confirmation before editing
any file. You must ask the engineer and receive an explicit "yes", "go ahead",
"proceed", or similar confirmation before making code changes.
Say: "Do you want me to proceed with the edit?"
Do NOT say: "Proceeding with the edit." — that skips the engineer's decision.

**If the risk is Low:** Use your judgment based on the synthesis findings. If
the change is straightforward and the synthesis found no concerns, you may
proceed. If anything is surprising or worth flagging, ask before editing.

---

## Session markers

These markers coordinate between the skill and the plugin's hooks. Output each
on its own line when the condition is met.

### Impact check complete

After the engineer confirms (High/Medium) or after presenting the synthesis (Low),
output one marker per assessed table. **IMPORTANT: use only the table/model name, not the full MCON:**

<!-- MC_IMPACT_CHECK_COMPLETE: <table_name> -->

(Use the model filename without .sql extension — NOT "acme.analytics.orders" or "prod.public.client_hub")

How many markers to emit depends on how the assessment was triggered:

**Hook-triggered** (the pre-edit hook blocked an edit and instructed you to run
the assessment): Be strict — only emit markers for tables whose lineage **and**
monitor coverage were fetched directly via Monte Carlo tools in this session. If
the engineer describes changes to multiple tables but only one was formally
assessed, emit only one marker. The pre-edit hook will gate the other tables and
prompt for their own Workflow 2 runs.

**Voluntarily invoked** (the engineer proactively asked for an impact assessment):
Be looser — emit markers for all tables the assessment meaningfully covered, even
if some were assessed via lineage context rather than direct MC tool calls. The
engineer is already safety-conscious; don't force redundant assessments for tables
they clearly considered.

### Monitor coverage gap

When Workflow 2 finds zero custom monitors on a table's affected columns, output:

<!-- MC_MONITOR_GAP: <table_name> -->

Use only the table/model name (NOT the full MCON). This allows the plugin's hooks
to remind the engineer about monitor coverage at commit time. Only output this
marker when the gap is specifically about the columns or logic being changed —
not for general table-level monitor absence.

After the prompt is delivered, the post-edit / pre-commit hook clears the gap
state internally so it won't re-prompt for the same gap; if the engineer edits
the model again, Workflow 2 will re-evaluate from scratch and re-emit the
marker only if a gap still exists.
