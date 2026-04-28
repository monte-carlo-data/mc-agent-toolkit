# Workflow Details

Detailed step-by-step instructions for each Monte Carlo Prevent workflow.
These are referenced from the main SKILL.md — consult the relevant section when
executing a workflow.

---

## Workflow 1: Asset health pre-fetch (silent delegation)

**Trigger:** The user expresses change intent. Workflow 1 only ever runs as a
precursor to Workflow 2 — it does not run on bare file mentions or general
"how is X doing" questions. Those go directly to `monte-carlo-asset-health`
via its own activation rules.

**Goal:** Gather Monte Carlo context (health, lineage, alerts, monitors) for
the table being changed so Workflow 2 can incorporate it into the change-focused
impact assessment. The report itself is data for W2 — not a separate user-facing
artifact.

### Sequence

1. Invoke the `monte-carlo-asset-health` skill via the Skill tool. Pass the
   table name. Wait for the full health report.

2. Do **not** duplicate any of the MCP calls asset-health makes
   (`get_table`, `get_alerts`, `get_asset_lineage` upstream-only, `get_monitors`).
   Asset-health is the source of truth for those.

3. Asset-health only fetches **upstream** lineage. To complete the picture for
   Workflow 2's blast-radius synthesis, make one additional direct call:

   ```
   get_asset_lineage(mcon="<mcon resolved by asset-health>", direction="DOWNSTREAM")
   ```

   Use the MCON asset-health already resolved — do **not** re-call `search()`.
   If asset-health surfaced a disambiguation prompt and the engineer hasn't
   chosen yet, wait — do not run the downstream call until the MCON is fixed.

4. **Do NOT print, summarize, paraphrase, or relay asset-health's report.**
   Asset-health returns a long Markdown report (Health Check tables, monitor
   lists, recommendations) — that report is **internal data for prevent**,
   not user-facing output. Treat it the same way you would treat a raw MCP
   tool result: read it into context, then move on without echoing it.

5. Two exceptions where you **must** surface W1 output to the engineer:
   - **Disambiguation prompt.** If asset-health returns multiple matches,
     surface that question and wait for the answer before continuing.
   - **Stop-the-world signals.** If the table is already on fire (active
     critical alerts firing, freshness severely stale), say so in one short
     line before W2 begins. One line — not the full asset-health report.

6. **Immediately proceed to Workflow 2.** Do not pause, do not ask the
   engineer if they want to continue, do not summarize what W1 found. The
   user-facing artifact is W2's impact-assessment report, not asset-health's
   report. W1 is incomplete until W2 has been presented.

### What Workflow 1 does NOT do

- Does not call MCP tools other than the single `get_asset_lineage(direction="DOWNSTREAM")`
  call in step 3. Everything else comes via asset-health.
- Does not run standalone. W1 only fires as part of the W1 → W2 chain. **W1
  finishing without W2 running is a workflow failure** — always continue to W2.
- Does not produce a user-facing report. Asset-health's "Health Check"
  Markdown is data, not output. The user-facing artifact is W2's report.
- Does not stop and wait for the engineer to confirm before W2. The transition
  W1 → W2 is automatic.
- Does not handle new-model creation. Prevent's mission is preventing
  dangerous changes to existing models. If the engineer is authoring a
  brand-new model and wants to verify upstream health, that is a
  `monte-carlo-asset-health` question on each upstream — not a prevent
  workflow.

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
1. search(query="<table_name>")
   → list of candidate MCONs across MC connections.
   If multiple results are returned, present them in a table (full_table_id,
   warehouse, importance, key-asset flag) and ask the engineer which one to
   assess. Do not pick one automatically. Once they choose, call
   getTable(mcon="<mcon>") for that single MCON.
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
> or your preferred SQL client — or let me run them against your sandbox
> now by saying `/mc-validate run`."

**Always end Workflow 3 with the `/mc-validate run` offer**, regardless of how
Workflow 3 was triggered (auto-activated or explicitly invoked). For YAML/docs-only
diffs where no SQL validation is useful, skip query generation entirely and tell
the engineer: "YAML-only diff; no SQL validation needed. `dbt test --select
<model>` can still exercise newly-added schema tests."

---

### What this workflow does NOT do
- Does not execute queries (Phase 2)
- Does not require warehouse MCP connection
- Does not generate Monte Carlo notebook YAML
- Does not trigger automatically — only on explicit engineer request
- Does not activate if Workflow 2 has not run for this table in this session

---

## Workflow 4: Sandbox build — invoked by `/mc-validate run`

**Trigger:** `/mc-validate run` (never automatic).

**Required session context:** Workflow 3 has produced a `validation/<table>_<ts>.sql`
for at least one changed model.

### Goal

Materialize the changed model(s) into the engineer's dev database with
`dbt build --select <model>` so validation queries have something real to read
from. Skip automatically for YAML/docs-only diffs.

### Sequence

0. **Pre-flight check (prerequisites).** Before any other step, verify:
   - `dbt` is installed and a `dbt_project.yml` is discoverable from the
     changed model.
   - The Snowflake MCP server is available in this session — look for any
     tool whose name starts with `mcp__snowflake__`. If absent, abort with:
     "Snowflake MCP is not registered in this session. `/mc-validate run`
     requires the Snowflake MCP server — see the prevent skill README's
     prerequisites. Aborting before the build so no work is lost."
   - `profiles.yml` exists where step 1 expects it.

   These are listed in `skills/prevent/README.md` under
   "`/mc-validate run` prerequisites". Failing fast here is much friendlier
   than failing deep inside `dbt build` or partway through query execution.

1. **Find `profiles.yml`.** Check `~/.dbt/profiles.yml` first, then the dbt
   project root (which is typically `analytics/` in MC's `dbt` repo — detect
   the same way `generate-validation-notebook` does, by walking up from the
   changed model file until a `dbt_project.yml` is found).


2. **Resolve the active target** using the sandbox script:

   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/skills/prevent/scripts/sandbox/parse_profiles.py <profiles.yml>
   ```

   On error (missing file, unparseable YAML, unresolvable target), skip this
   step and ask the engineer for their dev database directly.

3. **Classify the resolved database:**

   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/skills/prevent/scripts/sandbox/classify_sandbox.py <database>
   ```

   Categories: `personal`, `dev`, `shared-dev`, `prod`, `unknown`.

4. **Detect hard-coded `database:` in the model config:**

   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/skills/prevent/scripts/sandbox/detect_hardcoded_db.py <model.sql>
   ```

   If a value is returned, surface it to the engineer and use it in place of
   the profile's database for this model. Warn that the build will land in the
   hard-coded location regardless of their profile.

5. **Decide whether to build** (diff-aware):
   - If the session diff is **YAML / markdown / docs only** → skip the build,
     note "no rebuild needed for YAML-only change," continue to Workflow 5.
   - Otherwise → prompt:

     ```
     Run `dbt build --select <model>` to rebuild into <database> before validating? [Y/n]
     ```

6. **Hard-stop for prod classification.** If the classifier returned `prod`
   (or the hard-coded `database:` value classifies as `prod`) and the engineer
   approves the build, **refuse**: "Target resolves to shared prod. Aborting
   the build. Please fix your profiles.yml and re-run." Do not proceed.

7. **Execute the build.** Run from the dbt project root:

   ```bash
   dbt build --select <model>
   ```

   For multiple models, pass them in one invocation: `--select m1 m2 m3`. Do
   not add `--full-refresh` or `+<model>` unless the engineer explicitly asked.
   Stream stdout to the user.

8. **Handle test failures.** `dbt build` may succeed the run phase but fail
   tests. Treat this as a soft block and prompt:

   ```
   ✓ run succeeded
   ✗ N of M tests failed: <failing test names>

   Tests failed. Run validation queries anyway? [y/N]
   ```

9. **Emit a session marker** on success (or on skip, with reason):

   ```
   <!-- MC_BUILD_RAN: <table_name> -->
   ```

### What this workflow does NOT do

- Does not run `dbt run-operation`. If the engineer asks, refuse and instruct
  them to run it manually.
- Does not auto-add `--full-refresh` or `+<model>` cascades.
- Does not attempt to recover from `dbt debug` / connection failures; surface
  the error and stop.

---

## Workflow 5: Execute validation queries — invoked by `/mc-validate run`

**Trigger:** `/mc-validate run` (never automatic).

**Required session context:** Workflow 3 has produced a `validation/<table>_<ts>.sql`,
and Workflow 4 has either completed (or been explicitly skipped with
`--skip-build`, or been no-op'd for a YAML-only diff).

### Goal

Substitute the `<YOUR_DEV_DATABASE>` placeholder in the generated queries with
a user-confirmed value, verify each query is read-only, execute them via the
Snowflake MCP, and present per-query verdicts plus a consolidated summary.

### Sequence

1. **Propose a dev-database value.** If Workflow 4 resolved a database from
   `profiles.yml` (step 2–4 there), reuse that value. Otherwise, the engineer
   either passed `--dev-db <NAME>` or has not provided one — in which case
   prompt for it.

2. **Show the execution plan and require confirmation.** Scan the generated
   SQL for fully-qualified references and list every database that will be
   touched, so the engineer can see exactly where queries will run:

   ```
   Execution plan:

     Dev database (from profiles.yml target 'prod'):
       → PERSONAL_ACHEN   (classified: personal sandbox ✓)

     Other databases referenced literally in queries:
       → analytics        (used in N query)

   Proceed? [Y / type new dev database / cancel]
   ```

   Advisory text varies by classification:
   - `personal` / `dev` / `shared-dev` → `(classified: personal sandbox ✓)` etc.
   - `prod` → `⚠ classified as prod — this doesn't look like a dev database`
   - `unknown` → `(unrecognized — is this your dev database?)`

   If the engineer types a new value, re-classify it and re-confirm before
   continuing.

3. **Substitute placeholders:**

   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/skills/prevent/scripts/sandbox/substitute_placeholders.py \
     validation/<table>_<ts>.sql --dev-db <CONFIRMED_DEV_DB>
   ```

   This writes `validation/run/<table>_<ts>.run.sql` (the script creates the
   `run/` subdirectory if it doesn't exist) and reports the count of
   substitutions + the list of literal databases found. **All execution-time
   scratch output lives under `validation/run/`** so the main `validation/`
   directory stays clean with just the human-facing `.sql` generated by
   Workflow 3.

4. **Read-only pre-check** (mandatory):

   ```bash
   python3 ${CLAUDE_PLUGIN_ROOT}/skills/prevent/scripts/sandbox/readonly_check.py \
     validation/run/<table>_<ts>.run.sql
   ```

   If the script exits non-zero, **abort execution**. Report the rejected
   keyword and the query it came from. Do not send anything to Snowflake MCP.

   **If the script exits zero, tell the engineer explicitly** — the point of
   this check is confidence, and a silent pass doesn't build it. Output one
   short line before step 5:

   > ✓ Read-only pre-check passed — N queries verified SELECT-only, no writes can reach Snowflake.

5. **Show the final SQL** (per query, as a fenced SQL block) to the engineer
   before sending to Snowflake MCP. This is the last point at which they can
   cancel. Having seen the ✓ from step 4 plus the exact SQL here, the
   engineer has everything they need to press proceed with confidence.

6. **Execute each query via Snowflake MCP** (e.g. the `mcp__snowflake__query`
   tool — confirm the exact tool name available in the session). Apply a 60s
   per-query timeout by default. On error (including timeout), continue with
   remaining queries but mark the failed one.

   **Prefer splitting queries in memory.** Read `validation/run/<table>_<ts>.run.sql`
   once, split the queries in memory (they're separated by blank lines between
   top-level statements; each query is preceded by a `/* ... */` comment block
   containing its name and "What to look for" guidance), and pass each query
   string directly to the Snowflake MCP tool. The comment is metadata for the
   verdict in step 7, not a file to write.

   **If you must write per-query scratch files** (e.g. because your MCP client
   only accepts file paths), put them under `validation/run/` alongside the
   `.run.sql` — never at the top level of `validation/`. The `validation/run/`
   directory is understood to be transient and safe to gitignore; top-level
   `validation/` is the durable human-facing artifact directory.

7. **Report per-query verdicts** using the "What to look for" comment block
   attached to each query in the generated `.sql`:

   - Print a short human heading per query (e.g. "Row count comparison: prod vs dev").
   - Show the result as a compact table (cap 20 rows; truncate with a note
     above 20).
   - **Wide tables:** if the result has more than 12 columns, project to
     just the columns named in the query's `/* What to look for */` comment
     block (plus any obvious key columns like the join key or primary id).
     Mention the omission in the verdict line — e.g. "showing 6 of 84
     columns; full result available by re-running the query directly."
     This keeps `SELECT *` against a 100-column table from burying the
     signal under width.
   - Emit one of `✅` / `⚠️` / `🔴` with a one-line reason grounded in the
     "What to look for" comment — do not invent "healthy" from nothing.
   - For `⚠️` and `🔴`, add a follow-up hint.

8. **Consolidated summary** at the end, e.g.:

   ```
   ## Validation summary: <model>

   ✅ Row count comparison
   ✅ Sample data preview
   ⚠️ Null rate on days_since_contract_start (4.2% null in dev — expected ~0%)
   ✅ Core segmentation counts
   ✅ Uniqueness check on account_id

   Overall: 4 of 5 checks clean. 1 warning worth investigating before merging.
   ```

9. **Emit a session marker** per model after execution:

   ```
   <!-- MC_VALIDATE_RAN: <table_name> -->
   ```

10. **Feed 🔴 verdicts back to the change context.** If any query verdict was
    🔴 (and only then), add a closing line to the consolidated summary that
    invites the engineer to revisit the change before merging:

    > "One or more checks failed. If these results suggest the change isn't
    > behaving as intended, consider re-running Workflow 2 (change impact
    > assessment) with the failing-query summary as additional input — that
    > can surface whether the failure is downstream-relevant — before
    > revising the code."

    Do not auto-invoke Workflow 2. Surface the option and let the engineer
    decide. This closes the loop between W5 (what the data says) and W2
    (what to do about the change). For `⚠️`-only results, note them but
    don't suggest re-running W2 — yellow signals usually warrant
    investigation, not a re-assessment.

### Multi-model behavior

If Workflow 3 generated files for multiple models, run steps 3–8 per model
with its own substituted file and its own verdicts section. Finish with a
top-level summary listing one status line per model.

### What this workflow does NOT do

- Does not execute any statement that isn't read-only (rejected by step 4).
- Does not guess a dev database when `profiles.yml` / `--dev-db` don't provide
  one — it asks.
- Does not fall back to any execution path other than Snowflake MCP unless
  the MCP is unavailable, in which case it leaves the substituted `.run.sql`
  on disk and tells the engineer to run it manually.
- Does not re-run queries — each invocation is a fresh execution of all
  queries in the current file.

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
