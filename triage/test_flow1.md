# Triage Workflow — test_flow1

General-purpose triage across all Monte Carlo alerts, built and validated on 2026-04-16.

- **Audience:** all (no audience filter)
- **Time window:** last 12 hours (widen from 3 hours to get a useful working set; tighten to 3–6 hours for scheduled runs)
- **Status filter:** `NOT_ACKNOWLEDGED` only (skips already-triaged alerts)
- **Mode:** recommendation (no writes to MC; switch to action mode once validated)

---

## Procedure

### Step 1: Fetch alerts

Call `get_alerts` for the last 12 hours, filtered to `NOT_ACKNOWLEDGED` status only.

```
statuses: ["NOT_ACKNOWLEDGED"]
created_after: <12 hours ago>
first: 100
```

If no alerts are returned, stop — nothing to triage.

Check for `truncation_note` in the response — if present, paginate using `cursor` to retrieve remaining alerts.

### Step 2: Score each alert

Call `alert_assessment` in parallel for every alert, in batches of up to 10 at a time.

Each result includes `alert_confidence`, `alert_impact` (HIGH/MEDIUM/LOW), and a natural-language summary used for comments on untroubleshot alerts.

If `alert_assessment` times out for an alert, retry once. If it fails again, skip the alert — leave it unchanged and unactioned, and note it in the output summary.

### Step 3: Troubleshoot high-signal alerts

Run `run_troubleshooting_agent` (async_mode=True) on alerts where BOTH `alert_confidence` AND `alert_impact` are MEDIUM or HIGH. Skip any alert where either score is LOW — troubleshooting is expensive and not warranted for low-signal alerts.

Fire all eligible alerts simultaneously. For each job that returned `queued` or `running`, poll with `get_troubleshooting_agent_results` — wait ~30 seconds before first poll, then increase to 60s intervals. Classify each alert as its result arrives.

**Classifications:**

| Classification | When to use |
|---|---|
| Intentional change | Planned migrations, feature releases, or bug fixes |
| Natural data variation | Seasonal patterns or expected volatility |
| Possible data incident | Requires further investigation — no clear root cause |
| Resolved incident | A real incident that has already resolved |
| Verified ongoing incident | Clear incident, root cause identified, not yet resolved |
| Other | Does not fit the above |

### Step 4: Take actions

**In recommendation mode (current):** do not call any write tools. For each alert, output what would happen.

**In action mode:** apply the following for real.

#### Comments

Call `create_or_update_alert_comment` for every scored alert:
- **Untroubleshot alerts:** one sentence describing the anomaly and its confidence/impact scores. No recommendations.
- **Troubleshot alerts:** 2–4 sentences covering classification, reasoning from the troubleshooting output, and action taken or recommended.

#### Status updates

Call `update_alert` for each classified alert:

| Classification | Status |
|---|---|
| Natural data variation | `NO_ACTION_NEEDED` |
| Intentional change | `EXPECTED` |
| Resolved incident | `FIXED` |
| Verified ongoing incident | `ACKNOWLEDGED` |
| Possible data incident | *(no change)* |
| Other | *(no change)* |

Do not update status for untroubleshot alerts.

---

## Output

After all steps, produce a summary table:

| Alert | Type | Confidence | Impact | Classification | Action taken |
|-------|------|------------|--------|----------------|--------------|

Include every alert. For untroubleshot alerts, leave Classification blank and set Action Taken to "Comment only". For skipped alerts (scoring timeout), note "Skipped (timeout)".

---

## Moving to action mode

When recommendation mode output matches how the team would respond manually:

1. Remove the "do not call write tools" restriction in Step 4
2. Update **Mode** at the top to `action`

## Adapting this workflow

- **Narrow to a team:** add an `audience_ids` filter to scope alerts to a specific team
- **Tighten for scheduled runs:** reduce time window to 3–6 hours to avoid processing the same alerts twice
- **Widen troubleshooting threshold:** also run troubleshooting when either score is HIGH (useful once noisy monitors are tuned)
- **Tune scoring:** add `user_instructions` to `alert_assessment` to down-weight monitors with >20 alerts/60 days and zero actioned history — most LOW-confidence alerts in this environment are chronically miscalibrated monitors
- **Use `/schedule`** to automate on a fixed cadence

## Notes from initial run (2026-04-16)

- **Dominant pattern: noisy monitors.** 6 of 7 scored alerts had LOW confidence because their monitors had fired 14–74 times in 60 days with zero actioned alerts. This environment has significant monitor calibration debt. Consider recalibrating or suppressing these monitors before running in action mode.
- **One verified incident found:** `analytics.prod_internal_bi.exlooker_billable_tables__snapshot_expanded` lost ~30M rows due to `analytics.prod.calendar_gen` expiring on April 16, 2026. The calendar table had no Monte Carlo metadata ingested, preventing early detection. Fix: regenerate `calendar_gen` with a 1–2 year date horizon; add a MAX(date) monitor to catch this proactively.
- **Assessment timeout:** `prod_lineage_v2.edges_fixed/stats` (Dolomites Freshness) timed out twice on `alert_assessment`. The retry-once logic in Step 2 covers this — flag in summary if it persists.
