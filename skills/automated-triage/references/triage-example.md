# Triage Example: 6-Step Workflow

This is a complete, ready-to-run triage workflow. It covers all five stages from `triage-stages.md` in a single pass and is a good starting point for most Monte Carlo environments.

Run it as-is to see how triage works end-to-end, then adapt it to match your team's needs.

---

## What this workflow does

1. Fetches all alerts from the last 3 hours
2. Scores every alert by confidence and impact (in parallel)
3. Runs deep troubleshooting on alerts where BOTH confidence AND impact are MEDIUM or HIGH
4. Posts a triage comment on every alert
5. Updates the status of troubleshot alerts based on their classification

---

## Procedure

Work through all 6 steps in order. Do not skip steps or reorder them.

### Step 1: Fetch alerts

Call `get_alerts` for the last 3 hours.

If no alerts are returned, report: "No alerts in the last 3 hours." and stop.

### Step 2: Score each alert

Call `alert_assessment` in parallel for every alert from step 1, in batches of up to 10 at a time. Each result includes `alert_confidence`, `alert_impact` (HIGH/MEDIUM/LOW each), and a natural-language summary — the summary is used for the triage comment in step 5 for alerts that don't go through troubleshooting.

### Step 3: Troubleshoot and classify high-signal alerts

For each alert where BOTH `alert_confidence` AND `alert_impact` are MEDIUM or HIGH, call `run_tsa` with at most 2 running in parallel — each TSA call can spawn dozens of sub-agents, so more than 2 concurrent calls can cause degraded performance. 
Skip any alert where either value is LOW — `run_tsa` is expensive and not warranted for low-signal alerts.

After each call, classify that alert before moving on to the next.


**Classifications:**

| Classification              | When to use                                                                                                          |
| --------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| **Intentional change**      | Planned migrations, feature releases, or bug fixes                                                                   |
| **Natural data variation**  | Seasonal patterns or expected volatility                                                                             |
| **Possible data incident**  | Anything that requires further investigation                                                                         |
| **Resolved incident**       | A real incident that has already been resolved                                                                       |
| **Verified ongoing incident** | A clear incident that has not resolved, where troubleshooting identified the root cause (e.g. query change or infrastructure failure) |
| **Other**                   | Does not fit the above                                                                                               |

Alerts that did not go through `run_tsa` are left unclassified.

### Step 4: Post a triage comment on every alert

Call `create_or_update_alert_comment` for each alert:

- **Untroubleshot alerts**: one sentence describing the anomaly and the confidence/impact scores. Do not explain why it wasn't troubleshot. No recommendations.
- **Troubleshot alerts**: 2–4 sentences covering classification, reasoning from the `run_tsa` output, any action taken, and a recommendation.

### Step 5: Update status for troubleshot alerts

For each classified alert from step 3, call `update_alert`:

| Classification              | Status               |
| --------------------------- | -------------------- |
| Natural data variation      | `NO_ACTION_NEEDED`   |
| Intentional change          | `EXPECTED`           |
| Resolved incident           | `FIXED`              |
| Verified ongoing incident   | `ACKNOWLEDGED`       |
| Possible data incident      | *(no change)*        |
| Other                       | *(no change)*        |

Do not update status for untroubleshot alerts.

---

## Output

After completing all 6 steps, produce a summary table:

| Alert ID | Type | Confidence | Impact | Classification | Action Taken |
|----------|------|------------|--------|----------------|--------------|

Include every alert from step 1. For untroubleshot alerts, leave Classification blank and set Action Taken to "Comment only".

---

## Adapting this example

Common adjustments:

- **Change the time window** in step 1 (e.g. last 1 hour for a continuous loop, last 24 hours for a daily run)
- **Adjust the troubleshooting filter** in step 3
- **Skip status updates** in step 6 while building confidence — comments alone are a good first step
- **Add Slack or ticket creation** in step 5/6 for confirmed incidents
- **Customise `alert_assessment` scoring** via `user_instructions` to tune emphasis for your environment (see `triage-stages.md`)
