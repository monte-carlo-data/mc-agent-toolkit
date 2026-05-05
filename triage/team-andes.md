# Triage Workflow — team_andes

Automated hourly triage for the Andes team's Monte Carlo alerts.

- **Audience:** team_andes (`2d300526-306c-4aba-b0aa-44c13ac710cf`)
- **Cadence:** every 1 hour
- **Status filter:** `NOT_ACKNOWLEDGED` only (skips already-triaged alerts)
- **Slack channel:** #agentic-do-testing-outputs (`C0ASSV042SJ`)
- **Mode:** recommendation (no writes to MC; switch to action mode once validated)

---

## Procedure

### Step 1: Fetch alerts

Call `get_alerts` for the last 1 hour, filtered to the team_andes audience and `NOT_ACKNOWLEDGED` status only.

```
audience_ids: ["2d300526-306c-4aba-b0aa-44c13ac710cf"]
statuses: ["NOT_ACKNOWLEDGED"]
created_after: <1 hour ago>
first: 100
```

If no alerts are returned, stop — nothing to triage.

Check for `truncation_note` in the response — if present, paginate using `cursor` to retrieve remaining alerts.

### Step 2: Score each alert

Call `alert_assessment` in parallel for every alert, in batches of up to 10 at a time.

Each result includes `alert_confidence`, `alert_impact` (HIGH/MEDIUM/LOW), and a natural-language summary used for comments on untroubleshot alerts.

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

Call `create_or_update_alert_comment` for every alert:
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

#### Slack notifications

For each **verified ongoing incident** only, post one message to **#agentic-do-testing-outputs** (`C0ASSV042SJ`) containing:
- Alert title and affected table
- Root cause summary (2–3 sentences from the troubleshooting output)
- Link to the alert: use the `url` field from `get_alerts`

Do not post for any other classification.

---

## Output

After all steps, produce a summary table:

| Alert | Audience | Confidence | Impact | Classification | Action taken |
|-------|----------|------------|--------|----------------|--------------|

Include every alert. For untroubleshot alerts, leave Classification blank and set Action Taken to "Comment only".

---

## Moving to action mode

When recommendation mode output matches how the team would respond manually:

1. Remove the "do not call write tools" restriction in Step 4
2. Replace the Slack `output` step with a real `slack_send_message` call per verified incident
3. Update **Mode** at the top to `action`
4. Post to the team_andes Slack channel (`C05BXN2U89W`) once tested in #agentic-do-testing-outputs

## Adapting this workflow

- **Widen troubleshooting threshold:** also run troubleshooting when either score is HIGH (useful once noisy monitors are tuned)
- **Tune scoring:** add `user_instructions` to `alert_assessment` to down-weight known noisy monitors
- **Use `/schedule`** to automate on a fixed cadence

## Notes

- `prod.table_events` has a chronically noisy monitor (24 alerts in 60 days, none actioned — LOW confidence). Consider recalibrating or muting it. It will reliably produce comment-only output until addressed.
