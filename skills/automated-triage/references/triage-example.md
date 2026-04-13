# Triage Example Workflow

This is a complete triage workflow that supports two modes:

- **Recommendation mode** — runs the full investigation and tells you what it would do, without writing anything to your environment. Use this while tuning your triage prompt.
- **Action mode** — runs the full workflow and applies actions (comments, status updates) for real.

Run in recommendation mode first. Once the classifications and recommendations match how your team would respond manually, switch to action mode.

---

## What this workflow does

1. Asks whether to run in recommendation or action mode
2. Fetches all alerts from the last 3 hours
3. Scores every alert by confidence and impact (in parallel)
4. Fires deep troubleshooting on all high-signal alerts simultaneously, classifying each as results arrive
5. In **action mode**: posts a triage comment on every alert and updates statuses
   In **recommendation mode**: outputs what it would comment and what status it would set — no writes

---

## Procedure

### Step 1: Choose mode

Ask: "Run in **recommendation mode** (no writes — I'll show you what actions would be taken) or **action mode** (comments and status updates applied for real)?"

Wait for the answer before proceeding.

### Step 2: Fetch alerts

Call `get_alerts` for the last 3 hours.

If no alerts are returned, report: "No alerts in the last 3 hours." and stop.

### Step 3: Score each alert

Call `alert_assessment` in parallel for every alert from step 2, in batches of up to 10 at a time. Each result includes `alert_confidence`, `alert_impact` (HIGH/MEDIUM/LOW each), and a natural-language summary — the summary is used for the triage comment in step 4 for alerts that don't go through troubleshooting.

### Step 4: Troubleshoot and classify high-signal alerts

For each alert where BOTH `alert_confidence` AND `alert_impact` are MEDIUM or HIGH, call `run_troubleshooting_agent` (default `async_mode=True`). Fire all eligible alerts simultaneously — each call returns immediately with one of: `success` (previous results available immediately), `queued` (accepted, not started yet), or `running` (in progress).

Skip any alert where either value is LOW — troubleshooting is expensive and not warranted for low-signal alerts.

For each job that returned `queued` or `running`, poll with `get_troubleshooting_agent_results(incident_id=...)` — start at ~30 seconds, then increase to 60s intervals. Classify each alert as its result arrives (`success`), before moving on. If a job returns `failed`, note it and continue.

**Classifications:**

| Classification                | When to use                                                                                                           |
| ----------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| **Intentional change**        | Planned migrations, feature releases, or bug fixes                                                                    |
| **Natural data variation**    | Seasonal patterns or expected volatility                                                                              |
| **Possible data incident**    | Anything that requires further investigation                                                                          |
| **Resolved incident**         | A real incident that has already been resolved                                                                        |
| **Verified ongoing incident** | A clear incident that has not resolved, where troubleshooting identified the root cause (e.g. query change or infrastructure failure) |
| **Other**                     | Does not fit the above                                                                                                |

Alerts that did not go through troubleshooting are left unclassified.

### Step 5: Comments and status updates

**Action mode:**

Call `create_or_update_alert_comment` for each alert:
- **Untroubleshot alerts**: one sentence describing the anomaly and the confidence/impact scores. Do not explain why it wasn't troubleshot. No recommendations.
- **Troubleshot alerts**: 2–4 sentences covering classification, reasoning from the troubleshooting output, any action taken, and a recommendation.

Then call `update_alert` for each classified alert:

| Classification              | Status               |
| --------------------------- | -------------------- |
| Natural data variation      | `NO_ACTION_NEEDED`   |
| Intentional change          | `EXPECTED`           |
| Resolved incident           | `FIXED`              |
| Verified ongoing incident   | `ACKNOWLEDGED`       |
| Possible data incident      | *(no change)*        |
| Other                       | *(no change)*        |

Do not update status for untroubleshot alerts.

**Recommendation mode:**

Do not call any write tools. Instead, for each alert output:
- The comment you would post
- The status you would set (or "no change")

---

## Output

After completing all steps, produce a summary table:

| Alert ID | Type | Confidence | Impact | Classification | Action Taken |
|----------|------|------------|--------|----------------|--------------|

Include every alert from step 1. For untroubleshot alerts, leave Classification blank and set Action Taken to "Comment only".

---

## Adapting this example

Common adjustments:

- **Change the time window** in step 2 (e.g. last 1 hour for a continuous loop, last 24 hours for a daily run)
- **Adjust the troubleshooting filter** in step 4
- **Add Slack or ticket creation** in step 5 for confirmed incidents
- **Customise `alert_assessment` scoring** via `user_instructions` to tune emphasis for your environment (see `triage-stages.md`)
