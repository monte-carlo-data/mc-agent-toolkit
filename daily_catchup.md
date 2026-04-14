# Daily Alert Catchup

Fetches all unacknowledged alerts from the last 24 hours, scores every alert, organises them into priority tiers, and posts a summary to Slack.

---

## What this workflow does

1. Fetches all `NOT_ACKNOWLEDGED` alerts from the last 24 hours
2. Scores every alert with `alert_assessment` in parallel (confidence, impact, summary)
3. Assigns each alert to a priority tier based on native priority + scores
4. Posts a structured summary to #team-sinai (no individual alert comments)

---

## Tier logic

| Tier | Criteria |
|------|----------|
| **High** | P1/P2 alert, OR HIGH confidence (regardless of impact) |
| **Medium** | P3 alert, OR MEDIUM confidence + MEDIUM or HIGH impact (not already High) |
| **Low** | Everything else |

---

## Procedure

### Step 1: Fetch alerts

Call `get_alerts` with:
- `statuses: ["NOT_ACKNOWLEDGED"]`
- `created_after`: 24 hours ago (ISO format)
- `first: 100`

If no alerts are returned, report "No unacknowledged alerts in the last 24 hours." and stop.

Check for `truncation_note` — if present, paginate with `cursor` to retrieve the remaining alerts before continuing.

### Step 2: Score every alert

Call `alert_assessment` in parallel for every alert from Step 1, in batches of up to 10 at a time. Each result includes:
- `alert_confidence` (HIGH/MEDIUM/LOW)
- `alert_impact` (HIGH/MEDIUM/LOW)
- A natural-language summary of the alert

If an assessment returns an error or empty scores, mark the alert as unscored and continue.

### Step 3: Assign tiers

Apply the tier logic above to each alert. Use the alert's native `priority` field (P1–P5) and the `alert_confidence` / `alert_impact` scores from Step 2.

### Step 4: Post Slack summary

Post to #team-sinai (channel ID: `C0AM84B7F0D`) using the format below.

**Do not post individual comments on alerts.**

---

## Slack message format

```
*Monte Carlo Alert Triage — last 24h* | {total} alerts · {high} high · {medium} medium · {low} low{unscored_note}

━━━━━━━━━━━━━━━━━━━━━━
🔴 *HIGH PRIORITY* ({high} alerts)
━━━━━━━━━━━━━━━━━━━━━━

For each HIGH tier alert:
- If HIGH confidence: 🚨 *[HIGH confidence] {title}*
- If P1/P2 with LOW confidence: ⚠️ *[{priority}] {title}*
One sentence description from the assessment summary.
Confidence: {confidence} · Impact: {impact} · <{url}|View alert>

Group repeated firings of the same monitor into a single entry.

━━━━━━━━━━━━━━━━━━━━━━
🟡 *MEDIUM PRIORITY* ({medium} alerts)
━━━━━━━━━━━━━━━━━━━━━━

For each MEDIUM tier alert:
• *{title}*
  One sentence description.
  Confidence: {confidence} · Impact: {impact} · <{url}|View alert>

━━━━━━━━━━━━━━━━━━━━━━
⚪ *LOW PRIORITY* ({low} alerts{unscored})
━━━━━━━━━━━━━━━━━━━━━━
Brief summary — total count, dominant pattern (e.g. noisy monitors), notable calibration issues.
Do not list individual LOW tier alerts.

━━━━━━━━━━━━━━━━━━━━━━
💡 *Recommendations*
━━━━━━━━━━━━━━━━━━━━━━
2–4 bullet points based on what was observed:
- Flag HIGH-confidence alerts that warrant immediate investigation
- Call out monitors that are firing repeatedly with LOW confidence and no prior action
- Note any patterns worth a monitor health review
```

---

## Adapting this workflow

- **Change the time window** — adjust `created_after` in Step 1 (e.g. last 1 hour for a continuous loop)
- **Scope to a team** — add `domain_ids` or `audience_ids` filter in Step 1
- **Add individual comments** — call `create_or_update_alert_comment` on each alert in Step 4, before posting to Slack
- **Add status updates** — call `update_alert` for classified alerts (requires deep troubleshooting first — see `triage-example.md`)
- **Change the Slack channel** — update the channel ID in Step 4
- **Tune the tier thresholds** — adjust the tier logic table above
