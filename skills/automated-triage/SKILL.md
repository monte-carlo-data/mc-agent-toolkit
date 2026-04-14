---
name: monte-carlo-automated-triage
description: |
  Guides users through setting up and running automated alert triage for
  their Monte Carlo environment. Activates when a user asks to triage alerts,
  set up automated triage, run agentic triage, or investigate recent alert
  activity. Covers MCP setup, the stages of a triage workflow, and how to
  customise each stage to match how their team responds to alerts manually.
version: 1.0.0
---

# Monte Carlo Automated Triage

This skill helps you design, test, and deploy an automated triage agent for Monte Carlo alerts. Rather than a fixed workflow, it gives you the building blocks — a set of MCP tools, a description of each triage stage, and a working example — so you can build a process that matches how your team actually responds to alerts.

Read the reference files before proceeding:

- Triage stages and customisation: `references/triage-stages.md` (relative to this file)
- Working example workflow: `references/triage-example.md` (relative to this file)

---

## When to activate this skill

Activate when the user:

- Wants to set up automated triage for Monte Carlo alerts
- Asks to run agentic triage or investigate recent alert activity
- Wants to understand what triage tools are available and how to use them
- Is building or refining a triage prompt for their environment
- Wants to move from manual alert review to automated or semi-automated triage

## When NOT to activate this skill

Do not activate when the user is:

- Investigating a specific known incident (help them directly)
- Creating or configuring monitors (use the monitor-creation skill)
- Running impact analysis before a code change (use the prevent skill)

---

## Prerequisites

**Alert scoring (`alert_assessment`) requires the extended MCP toolset.** Deep troubleshooting (`run_troubleshooting_agent`, `get_troubleshooting_agent_results`) is available in the default toolset.

To enable the extended toolset for alert scoring, update your MCP server configuration:

**Claude Code** (`.claude/settings.json` or `~/.claude/settings.json`):
```json
{
  "mcpServers": {
    "monte-carlo": {
      "command": "...",
      "args": ["..."],
      "env": {
        "toolset": "extended"
      }
    }
  }
}
```

**Cursor** (`.cursor/mcp.json`):
```json
{
  "mcpServers": {
    "monte-carlo": {
      "command": "...",
      "env": {
        "toolset": "extended"
      }
    }
  }
}
```

Without `toolset: extended`, alert scoring (`alert_assessment`) will fail.

---

## Available MCP tools

All tools are available via the `monte-carlo` MCP server.

| Tool                             | Toolset  | Purpose                                                         |
| -------------------------------- | -------- | --------------------------------------------------------------- |
| `get_alerts`                          | default  | Fetch recent alerts for a time window                                                                             |
| `alert_assessment`                    | extended | Score an alert by confidence and impact (HIGH/MEDIUM/LOW each)                                                    |
| `run_troubleshooting_agent`           | default  | Run the Monte Carlo Troubleshooting Agent on a single alert; async by default — returns immediately, reuses existing results when available |
| `get_troubleshooting_agent_results`   | default  | Poll an async troubleshooting run by `incident_id`; returns status (`not_found`/`running`/`success`/`failed`) and results when complete |
| `update_alert`                        | default  | Update an alert's status and/or declare an incident by setting severity                                           |
| `set_alert_owner`                     | default  | Assign an owner to an alert by email                                                                              |
| `create_or_update_alert_comment`      | default  | Post or update a triage comment on an alert                                                                       |

---

## How to approach automated triage

Read `references/triage-stages.md` for a full description of each stage and how to customise it. The high-level flow is:

1. **Fetch alerts** — decide which alerts to triage and over what time window
2. **Initial investigation** — score every alert by confidence and impact using `alert_assessment`
3. **Deep troubleshooting** — run `run_troubleshooting_agent` on high-signal alerts to get root cause analysis
4. **Classify** — use the troubleshooting output to classify each alert
5. **Take actions** — post comments, update statuses, message Slack, create tickets

The triage process is not fixed. Read the stages reference to understand the options and tradeoffs at each step, then design a workflow that fits your team's needs.

## The longer-term direction

Most teams move through roughly the same arc, though the pace and path vary:

- **Start with recommendations.** Run manually and have the agent post comments describing what it found and what it would do — no actual status changes or external actions. Use this to tune the workflow until the output matches how your team would respond manually.
- **Automate, still in recommendation mode.** Once the output looks right, put it on a schedule. Keep it in recommendation mode while you validate it's behaving well on real traffic.
- **Replace recommendations with actions.** When you're confident, swap the comment recommendations for real actions — status updates, Slack messages, ticket creation.

Don't force this progression — it's a direction, not a checklist. The path will depend on how your environment behaves and how much trust you want to build before each step.

---

## Activation flow

When this skill is activated, follow this sequence in order.

### Step 1: Check MCP tools

Verify that `get_alerts`, `alert_assessment`, and `run_troubleshooting_agent` are accessible. If `alert_assessment` is missing, show the extended toolset configuration from the Prerequisites section and stop — the user needs to fix this before continuing.

### Step 2: Orient the user to their workflow file

Ask whether the user has an existing triage workflow file, or is starting fresh.

**Starting fresh:**

1. Read `references/triage-example.md` (relative to this skill file). Give a brief description: it fetches alerts from the last 3 hours, scores every alert, runs deep troubleshooting on high-signal ones, and shows what actions it would take — no writes on a first run.
2. Run in recommendation mode, step by step (see Step 3). No need to ask.

**Has an existing file:**

1. Read it and confirm the key settings: time window, filter threshold, and whether it includes a mode-selection step.
2. Summarise what it will do, then ask: **"Run straight through, or step through each stage one at a time? And recommendation or action mode?"**

### Step 3: Run the workflow

Execute the workflow from the file, following its instructions exactly. Do not improvise steps or add actions not described in the file.

**For first runs (starting fresh):** always run step by step — after each stage completes, summarise what it produced, proactively suggest alternatives or adjustments based on what you observed, and wait for confirmation before continuing.

At each stage, draw on the options in `references/triage-stages.md` to make concrete suggestions:

- **After fetching alerts** — suggest filter adjustments if the set looks too broad or narrow: `NOT_ACKNOWLEDGED` to skip already-triaged alerts, domain/audience filters if alerts span multiple teams, a slightly longer time window for the initial testing if we need more examples to work with.
- **After scoring** — Suggest whether to adjust the troubleshooting filter (e.g. run when either score is HIGH, not just both MEDIUM+) or tune `alert_assessment` via `user_instructions`.
- **After troubleshooting** — if the TSA found a clear root cause, suggest whether to declare an incident severity, assign an owner.
- **After actions** — note cases where the default action mapping may not fit, e.g. a verified incident that warrants a Slack message or ticket rather than just a status update.

**For existing-file runs:** use whichever mode the user chose in Step 2.

### Step 4: Wrap up

After the workflow completes:

1. Ask: **"Want me to save a copy of our workflow to your project (e.g. `triage.md`) so you can customise it?"** If yes, write it to the path they choose.

2. Then present next steps based on what just happened and what you were asked to do in the first place.  For example:

   > "What would you like to do next?
   > - **Refine the workflow** — walk through the stages and tune what's not working (filter, scoring weights, troubleshooting threshold, action mapping)
   > - **Test on a different alert set** — re-run on a different time window or day to see how it handles a different set of alerts
   > - **Set up a schedule** — automate this to run on a fixed cadence using the `/schedule` skill
   > - **Something else** — just tell me"

   Adapt the options to context — if the run had many LOW-scoring alerts with no troubleshooting, lean towards refinement; if results looked solid, lean towards scheduling.

