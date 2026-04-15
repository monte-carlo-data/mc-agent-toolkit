# Workflow Details

Detailed step-by-step instructions for the Monte Carlo Asset Health skill.
Referenced from the main SKILL.md — consult when executing the workflow.

---

## Asset Health Check

When the user asks about the health or status of a data asset, run this sequence.

### Phase 1 — Resolve the asset

Run both calls in parallel:

```
search(query="<table_name>")
→ Returns MCON, full_table_id, and properties (tags)

get_mc_webapp_url()
→ Returns the base Monte Carlo webapp URL (MC_WEBAPP_URL)
```

Save the webapp URL for constructing alert links later.

Save the MCON for subsequent calls. Save properties for the Tags line in the
report. If multiple results are returned, present them in a table with these
exact columns and ask which one they want to check. Do not pick one automatically
or make assumptions.

```
| # | Table (full_table_id) | Warehouse | Importance | Key Asset |
|---|----------------------|-----------|------------|-----------|
| 1 | db:schema.table      | my-wh     | 0.99       | Yes       |
```

Every row must include the Warehouse column.

### Phase 2 — Gather health metrics (ALL in parallel)

Run all 4 calls in a single turn:

```
getTable(mcon="<mcon>")
→ last updated, row count, importance score, is_important (key asset flag)

getAlerts(created_after="<7 days ago>", created_before="<now>", table_mcons=["<mcon>"], statuses=["ACKNOWLEDGED", "WORK_IN_PROGRESS", null])
→ active alerts on this asset

getMonitors(mcons=["<mcon>"])
→ monitor configs — check status field for paused vs active

getAssetLineage(mcon="<mcon>", direction="upstream")
→ 1-hop upstream parent assets
```

Use `getCurrentTime()` in Phase 1 or Phase 2 if you need the current timestamp
for `getAlerts`. Or compute it from system time if available.

### Phase 3 — Check upstream health (ALL parents in parallel)

Check at most **10** upstream parents. If there are more than 10, check the first
10 and note: "N more upstream parents not checked — ask to see more."

For each upstream parent, run both calls in parallel:

```
getTable(mcon="<parent_mcon>")
→ freshness, importance

getAlerts(created_after="<7 days ago>", created_before="<now>", table_mcons=["<parent_mcon>"], statuses=["ACKNOWLEDGED", "WORK_IN_PROGRESS", null])
→ active alerts on this parent
```

All parents are checked in parallel with each other. Each parent's `getTable` and
`getAlerts` are also parallel (no dependency between them).

### Phase 4 — Synthesize the health report

Assemble findings into the report format defined in SKILL.md:

1. **Tags** — from `search` properties. Omit line if none.
2. **Status** — determine from alerts and monitoring:
   - 🔴 if any alerts returned (the statuses filter already limits to non-resolved)
   - 🟡 if no alerts but 0 active monitors on a high-importance asset
   - 🟢 otherwise
4. **Metrics table** — freshness, volume, alerts, monitoring, importance, upstream
5. **Active Alerts** — list each with type and status
6. **Upstream Issues** — list each parent with health status
   - If any parent is unhealthy, ask: "Want me to check further upstream for **\<parent\>**?"
7. **Recommendations** — only facts derivable from data:
   - Upstream issues that may explain this asset's problems
   - Alerts needing attention

### Monitoring assessment

When evaluating monitors from `getMonitors`:

- Count only **active** (non-paused) monitors
- A paused monitor does NOT count as active coverage
- Report: "N active monitors" or "N monitors (M paused)"
- Signal: ≥1 active = 🟢, 0 active = 🔴

---

## Upstream Drill-Down

When the user requests deeper upstream investigation for a specific parent:

### Phase 1 — Get upstream of the specified parent

```
getAssetLineage(mcon="<parent_mcon>", direction="upstream")
→ 1-hop upstream of the parent (grandparents of the original asset)
```

### Phase 2 — Check grandparent health (ALL in parallel)

For each grandparent:

```
getTable(mcon="<grandparent_mcon>")
getAlerts(created_after="<7 days ago>", created_before="<now>", table_mcons=["<grandparent_mcon>"], statuses=["ACKNOWLEDGED", "WORK_IN_PROGRESS", null])
```

### Phase 3 — Report

Present findings for this hop. If any grandparent has issues, again ask:
"Want me to check further upstream for **\<grandparent\>**?"

Each drill-down is exactly 1 hop. Never auto-cascade. Always wait for user request.
