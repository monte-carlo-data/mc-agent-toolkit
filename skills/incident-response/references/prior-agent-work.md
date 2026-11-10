# Reading prior agent work on an alert

Monte Carlo's agents (triage, the Troubleshooting Agent, the remediation agent, the monitor
tuning agent and the Bayes teammate) often reach an alert before you do. Read what they found
before running anything, and run an agent only for a step that has no result yet.

Read in this order. Each step names what to do when its result is empty.

## 1. Triage verdict: no extra call

`get_alerts` returns it on every alert:

- `triage_priority`: `HIGH`, `MEDIUM` or `LOW` once the alert is triaged.
- `triage_result`: `alert_confidence`, `alert_impact`, `alert_description`, `triage_summary`,
  `triaged_at`.

If `triage_priority` is empty, the alert is untriaged. Offer `triage_alert(alert_id=...)`. It
waits 1–2 minutes and returns an earlier verdict right away if one exists, so a repeat call never
starts a second triage.

## 2. Root cause

```
get_troubleshooting_agent_results(incident_id="<alert_uuid>")
```

- `success`: the root cause is in `tldr`, and the checks to confirm it are in `full_response`.
- `running`: an analysis is in progress. Poll it; do not start another.
- `not_found` or `failed`: no usable analysis. Offer `run_troubleshooting_agent` (async, 4–8
  minutes).

## 3. Remediation plan: only after a successful root cause

```
get_remediation_instructions(alert_id="<alert_uuid>")
```

The plan's `title`, `summary` and `destinations` say what to do next. `plan_in_progress` means
call again in a few seconds. Any other status means there is no plan for this analysis yet.

## 4. Tuning analysis for the alert's monitors

For each UUID in the alert's `monitor_uuids`:

```
get_monitor_tuning_suggestions(monitor_uuid="<monitor_uuid>")
```

Recommendations on record mean the tuning agent already considers this monitor noisy. Mention
it when the root cause points at monitor noise rather than a data problem.

## 5. What the Bayes teammate did: only when `get_teammate_activity` is available

Bayes, the Monte Carlo teammate in a domain's Slack channel, tunes monitors, watches issues and
skips alerts on its own. Skip this step when `get_teammate_activity` is not in your tool list.

1. Find the Bayes domain: `get_domains(mcon="<table mcon>", bayes_only=true)`. One domain: use
   it. Several: ask the user which. None: skip this step.
2. `get_teammate_activity(domain_id="<domain uuid>", since="<alert created_time>")`.
3. Keep only the entries about this alert, its monitors or its table. For example, Bayes may
   have already tuned the monitor, chosen not to post the alert, or be watching the issue.

## Report what you found

Before running anything, tell the user what is already known (triage verdict, root cause, plan,
tuning, teammate activity) and what is missing. Then offer to run what is missing rather than
running it unasked.
