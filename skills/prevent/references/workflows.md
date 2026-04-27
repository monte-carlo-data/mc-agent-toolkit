# Workflow Details

Detailed step-by-step instructions for each Monte Carlo Prevent workflow.
These are referenced from the main SKILL.md — consult the relevant section when
executing a workflow.

---

## Workflow 1: Table health check (delegated)

**Trigger:** A `.sql` file or dbt model is opened, referenced, or a table name
is mentioned in the context of an upcoming edit.

**Goal:** Surface Monte Carlo context (health, lineage, alerts, monitors) for
the table before the engineer makes any change.

### Sequence

1. Invoke the `monte-carlo-asset-health` skill via the Skill tool. Pass the
   table name. Wait for it to produce its full health report.

2. Do **not** duplicate any of the MCP calls asset-health makes
   (`get_table`, `get_alerts`, `get_asset_lineage`, `get_monitors`). Asset-health
   is the source of truth for health data.

3. Once the report returns, present it to the engineer as-is, then resume in
   prevent:

   - If the user's prompt or session context indicates **change intent** (any
     verb in Workflow 2's trigger list — see SKILL.md), proceed to Workflow 2
     (change impact assessment). Workflow 2 will reuse the data asset-health
     just gathered.
   - If there is **no change intent**, stop. The asset-health report is the
     answer.

### What this workflow does NOT do

- Does not call any MCP tools directly. All data comes from asset-health.
- Does not auto-escalate to Workflow 2 if there's no change intent. The skill
  trigger list in SKILL.md is the gate.

---

## Workflow 2: Change impact assessment — REQUIRED before modifying a model

**Trigger:** Any expressed intent to add, rename, drop, or change a column, join, filter, or model logic. Run this immediately — before writing any code — even if the user hasn't asked for it.

### Bugfixes and reverts require impact assessment too

When the user says "fix", "revert", "restore", or "undo", run this workflow
before writing any code — even if the change seems small or safe.

A revert that undoes a column addition or changes join logic has the same
blast radius as the original change. Downstream models may have already
adapted to the "incorrect" behavior, meaning the fix itself could break them.

Pay special attention to:
- Whether the revert removes a column other models now depend on
- Whether downstream models reference the specific logic being reverted
- Whether active alerts may be related to the change being reverted

When the user is about to rename or drop a column, change a join condition, alter a filter, or refactor a model's logic, run this sequence to surface the blast radius before any changes are committed:

**Data sources:**

If asset-health (Workflow 1) ran for this table earlier in the session, reuse
its lineage / alerts / monitors / table metadata. Do not re-fetch via MCP —
the data is the same. If the asset-health report is stale (older than this
turn's edit context) or covered a different table, re-invoke asset-health
rather than running impact assessment on partial data.

If asset-health did not run (the engineer invoked impact assessment directly,
without a prior file-open trigger), call MCP tools yourself in this order:

```
1. search(query="<table_name>") + getTable(mcon="<mcon>")
   → importance score, query volume (reads/writes per day), key asset flag

2. getAssetLineage(mcon="<mcon>")
   → full list of downstream dependents; for each, note whether it is a key asset

3. getTable(mcon="<downstream_mcon>") for each key downstream asset
   → importance score, last updated, monitoring status

4. getAlerts(
     created_after="<7 days ago>",
     created_before="<now>",
     table_mcons=["<mcon>", "<downstream_mcon_1>", ...],
     statuses=["NOT_ACKNOWLEDGED"]
   )
   → any active incidents already affecting this table or its dependents

5. getQueriesForTable(mcon="<mcon>")
   → recent queries; scan for references to the specific columns being changed
   → use getQueryData(query_id="<id>") to fetch full SQL for ambiguous cases

5b. Supplementary local search for downstream dbt refs:
   - Search the local models/ directory for ref('<table_name>') (single-hop only)
   - Compare results against getAssetLineage output from step 2
   - If any local models reference this table but are NOT in MC's lineage results:
     "⚠️ Found N local model(s) referencing this table not yet in MC's lineage: [list]"
   - If no models/ directory exists in the current project, skip silently
   - MC lineage remains the authoritative source — local grep is supplementary only

6. getMonitors(mcon="<mcon>")
   → which monitors are watching columns or metrics affected by the change
```

### Risk tier assessment

| Tier | Conditions |
|---|---|
| 🔴 High | Key asset downstream, OR active alerts already firing, OR >50 reads/day |
| 🟡 Medium | Non-key assets downstream, OR monitors on affected columns, OR moderate query volume |
| 🟢 Low | No downstream dependents, no active alerts, low query volume |

### Multi-model changes

When the user is changing multiple models in the same session or same domain
(e.g., 3 timeseries models, 4 criticality_score models):

- Run a single consolidated impact assessment across all changed tables
- Deduplicate downstream dependents — if two changed tables share a downstream
  dependent, count it once and note that it's affected by multiple upstream changes
- Present a unified blast radius report rather than N separate reports
- Escalate risk tier if the combined blast radius is larger than any individual table

Example consolidated report header:
"## Change Impact: 3 models in timeseries domain
Combined downstream blast radius: 28 tables (deduplicated)
Highest risk table: timeseries_detector_routing (22 downstream refs)"

### Report format

```
## Change Impact: <table_name>

Risk: 🔴 High / 🟡 Medium / 🟢 Low

Downstream blast radius:
  - <N> tables depend on this model
  - Key assets affected: <list or "none">

Active incidents:
  - <alert title, status> or "none"

Column exposure (for columns being changed):
  - Found in <N> recent queries (e.g. <query snippet>)

Monitor coverage:
  - <monitor name> watches <metric> — will be affected by this change
  - If zero custom monitors exist → append:
    "⚠️ No custom monitors on this table. After making your changes,
    I'll suggest a monitor for the new logic — or say 'add a monitor'
    to do it now."

Recommendation:
  - <specific callout, e.g. "Notify owners of downstream_table before deploying",
     "Coordinate with the freshness alert owner", "Add a monitor for the new column">
```

If risk is 🔴 High:
1. Call `getAudiences()` to retrieve configured notification audiences
2. Include in the recommendation: "Notify: <audience names / channels>"
3. Proactively suggest:
   - Notifying owners of downstream key assets manually via the audience channels listed above (alert mutation is handled by `monte-carlo-incident-response`)
   - Adding a monitor for the new logic before deploying (Workflow 6)
   - Running `montecarlo monitors apply --dry-run` after changes to verify nothing breaks

### Synthesis: translate findings into code recommendations

After presenting the impact report, use the findings to shape your code suggestion.
Do not present MC data and then write code as if the data wasn't there.
Explicitly connect each key finding to a specific recommendation:

- Active alerts firing on the table:
  → Recommend deferring or minimally scoping the change until alerts are resolved
  → Explain: "There are N active alerts on this table — making this change now
     risks compounding an existing data quality issue"

- Key assets downstream:
  → Recommend defensive coding patterns: null guards, backward-compatible changes,
     additive-only schema changes where possible
  → Explain: "X downstream key assets depend on this table — I'd recommend
     writing this as [specific pattern] to avoid breaking [specific dependent]"

- Monitors on affected columns:
  → Call out that the change will affect monitor coverage
  → Recommend updating monitors alongside the code change (offer Workflow 6)
  → Explain: "The existing monitor on [column] will need to be updated to
     account for this change"

- New output column or logic being added:
  → Always offer Workflow 6 after the impact assessment, regardless
    of existing monitor coverage
  → Do not skip this step even if risk tier is 🟢 Low
  → Say explicitly: "This adds new output logic — would you like me
    to generate a monitor for it? I can add a null check, range
    validation, or custom SQL rule."
  → Wait for the user's response before proceeding with the edit

- High read volume (>50 reads/day):
  → Recommend extra caution around column renames or removals
  → Suggest backward-compatible transition (add new column, deprecate old one)
  → Explain: "This table has [N] reads/day — a column rename without a
     transition period would break downstream consumers immediately"

- Column renames, even inside CTEs:
  → Never assume a CTE-internal rename is safe. Always check:
    1. Does this column appear in the final SELECT, directly or
       via a CTE that feeds into the final SELECT?
    2. If yes — treat as a breaking change. Recommend a
       backward-compatible transition: add the correctly-named
       column, keep the old one temporarily, remove in a
       follow-up PR.
    3. If truly internal and never surfaces in output — confirm
       this explicitly before proceeding.
  → Explain: "Even though this column is defined in a CTE, if it
    surfaces in the final SELECT it is a public output column —
    renaming it breaks any downstream model selecting it by name."

---

## Workflow 3: Change validation queries — after a code change is made

**Trigger:** Explicit engineer intent only. Activate when the engineer says something like:
- "generate validation queries", "validate this change", "I'm done with this change"
- "let me test this", "write queries to check this", "ready to commit"

**Required session context — do not activate without both:**
1. Workflow 2 (change impact assessment) has run for this table in this session
2. A file edit was made to a `.sql` or dbt model file for that same table

**Do NOT activate automatically after file edits. Do NOT proactively offer after Workflow 2 or file edits. The engineer asks when they are ready.**

---

### What this workflow does

Using the context already in the session — the Workflow 2 findings, the file diff, and the `getTable` result — generate 3–5 targeted SQL validation queries that directly test whether this specific change behaved as intended.

These are not generic templates. Use the semantic meaning of the change from Workflow 2 context: which columns changed and why, what business logic was affected, what downstream models depend on this table, and what monitors exist. A null check on a new `days_since_contract_start` column should verify it is never negative and never null for rows with a `contract_start_date` — not just check for nulls generically.

---

### Step 1 — Identify the change type from session context

From Workflow 2 findings and the file diff, classify the primary change. A change may span multiple types — classify the dominant one and note secondaries:

- **New column** — a new output column was added to the SELECT
- **Filter change** — a WHERE clause, IN-list, or CASE condition was modified
- **Join change** — a JOIN condition or join target was modified
- **Column rename or drop** — an existing output column was renamed or removed
- **Parameter change** — a hardcoded threshold, constant, or numeric value was changed
- **New model** — the file was newly created, no production baseline exists

---

### Step 2 — Determine warehouse context from Workflow 2

From the `getTable` result already in session context, extract:
- **Fully qualified table name** — e.g. `analytics.prod_internal_bi.client_hub_master`
- **Warehouse type** — Snowflake, BigQuery, Redshift, Databricks
- **Schema** — already resolved, do not re-derive

Use the correct SQL dialect for the warehouse type. Key differences:

| Warehouse | Date diff | Current timestamp | Notes |
|---|---|---|---|
| Snowflake | `DATEDIFF('day', a, b)` | `CURRENT_TIMESTAMP()` | `QUALIFY` supported |
| BigQuery | `DATE_DIFF(a, b, DAY)` | `CURRENT_TIMESTAMP()` | Use subquery instead of `QUALIFY` |
| Redshift | `DATEDIFF('day', a, b)` | `GETDATE()` | |
| Databricks | `DATEDIFF(a, b)` | `CURRENT_TIMESTAMP()` | |

For the dev database, use the placeholder `<YOUR_DEV_DATABASE>` with a comment instructing the engineer to replace it. Do not guess the dev database name.

---

### Step 3 — Apply database targeting rules (mandatory)

These rules are not negotiable — violating them produces queries that will fail at runtime:

- **Columns or logic that only exist post-change** → dev database only. Never query production for a column that doesn't exist there yet.
- **Comparison queries (before vs after)** → both production and dev databases
- **New model (no production baseline)** → dev database only for all queries
- **Row count comparison** → always include, always query both databases

---

### Step 4 — Generate targeted validation queries

Always include a row count comparison regardless of change type — it's the baseline signal that something unexpected happened.

Then generate change-specific queries based on what needs to be validated for this change type. Use the exact conditions, column names, and business logic from the diff and Workflow 2 findings — not generic placeholders. The goal for each change type:

**New column:** Verify the column is non-null where it should be non-null (based on its business meaning), that its value range is plausible, and that its distribution makes sense given the underlying data. Query dev only.

**Filter change:** Verify that only the intended rows were reclassified — generate a before/after count showing how many rows were added or removed by the new condition using the exact filter logic from the diff, and a sample of the rows that changed classification. The sample helps the engineer confirm the right records moved.

**Join change:** Verify that the join didn't introduce duplicates — a uniqueness check on the join key is essential. Also verify row count didn't change unexpectedly. Query dev for uniqueness, both databases for row count.

**Column rename or drop:** Verify the old column name is absent and the new column (if renamed) is present in the dev schema. Also verify that downstream models referencing the old column name are identified — use the local ref() grep results from Workflow 2 if available.

**Parameter or threshold change:** Verify the distribution of values affected by the change — how many rows moved above or below the new threshold, and whether the count matches the engineer's expectation. Query both databases to compare before and after.

**New model:** No production comparison possible. Verify row count is non-zero and plausible, sample rows look correct, and key columns are non-null. Query dev only.

---

### Step 5 — Add change-specific context to each query

For every query, include a SQL comment block that explains:
- What the query is checking
- What a healthy result looks like **for this specific change**
- What would indicate a problem

Derive this context from Workflow 2 findings. Use the business meaning of the change, not generic descriptions. For example, for adding `days_since_contract_start`:

```sql
/*
Null rate check: days_since_contract_start (new column, dev only)
What to look for:
  - Null count should equal workspaces with no contract_start_date
  - All rows with contract_start_date should have a non-null, non-negative value
  - Values above 3650 (~10 years) are suspicious and may indicate a data issue
*/
```

This is what differentiates these queries from generic validation — the comment tells the engineer exactly what pass and fail look like for their specific change.

---

### Step 6 — Save to local file

Save all generated queries to:
```
validation/<table_name>_<YYYYMMDD_HHMM>.sql
```

Include a header at the top of the file:
```sql
/*
Validation queries for: <fully_qualified_table>
Change type: <change type from Step 1>
Generated: <timestamp>
Workflow 2 risk tier: <tier from this session>

Instructions:
1. Replace <YOUR_DEV_DATABASE> with your personal or branch database
2. Run the row count comparison first
3. Run change-specific queries to validate intended behavior
4. Unexpected results should be investigated before merging
*/
```

Then tell the engineer:
> "Validation queries saved to `validation/<table_name>_<timestamp>.sql`.
> Replace `<YOUR_DEV_DATABASE>` with your dev database and run in Snowflake
> or your preferred SQL client to verify the change behaved as expected."

---

### What this workflow does NOT do
- Does not execute queries (Phase 2)
- Does not require warehouse MCP connection
- Does not generate Monte Carlo notebook YAML
- Does not trigger automatically — only on explicit engineer request
- Does not activate if Workflow 2 has not run for this table in this session

---

> **Note:** Workflow numbers 4 and 5 are reserved for the sandbox-build and
> execute-validation steps that land when the `achen/mc-validate-run` branch
> merges. The numbering jump from 3 to 6 is intentional, not a typo.

---

## Workflow 6: Add monitor (delegated, post-edit)

**Trigger:** *Never auto-invoked from a file-open or table-mention trigger.*
W6 fires only when:

1. The post-edit / turn-end hook injects the monitor-coverage prompt — driven
   by the `MC_MONITOR_GAP` marker emitted during Workflow 2 — **or**
2. The engineer explicitly asks to add a monitor for the just-edited model
   (e.g. "add a monitor", "create a monitor for X").

**Required session context:** Workflow 2 has run for the model and identified
a coverage gap, *or* the engineer is explicitly requesting monitor generation.

### Sequence

1. Ask the engineer:

   > "Generate monitor definitions for the new logic? (yes/no)"

2. On **no** → stop. The post-edit hook has already cleared the gap state;
   no further action.

3. On **yes** → invoke the `monte-carlo-monitoring-advisor` skill via the
   Skill tool. Pass:
   - The model name.
   - The specific columns / logic that changed (from the Workflow 2
     synthesis output).

4. **Prevent's responsibility ends at the moment delegation fires.** Do not
   wait for monitoring-advisor to finish, do not emit any completion marker,
   do not insert any post-step. Monitor generation can take a while; prevent
   should not block on it.

### Re-edit behavior

If the engineer edits the same model again, the pre-edit gate forces Workflow 2
to re-run, which re-evaluates monitor coverage via `get_monitors`. If the
generated monitors now cover the changed columns, Workflow 2 will not re-emit
`MC_MONITOR_GAP` — the gap is genuinely closed. If a fresh gap exists, Workflow 2
re-emits the marker and the post-edit hook prompts again. Self-healing — no
explicit "already generated" tracking needed.

### What this workflow does NOT do

- Does not generate monitor YAML itself. All generation is done by
  monitoring-advisor.
- Does not modify the `monte-carlo-monitoring-advisor` skill in any way.
- Does not emit `MC_MONITOR_GENERATED` or any other completion marker.
