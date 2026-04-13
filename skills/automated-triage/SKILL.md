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

---

## Activation flow

When this skill is activated, follow this sequence in order.

### Step 1: Check MCP tools

Verify that `get_alerts`, `alert_assessment`, and `run_troubleshooting_agent` are accessible. If `alert_assessment` is missing, show the extended toolset configuration from the Prerequisites section and stop — the user needs to fix this before continuing.

### Step 2: Orient the user to their workflow file

Ask whether the user has an existing triage workflow file, or is starting fresh.

**Starting fresh:**

1. Read `references/triage-example.md` (relative to this skill file) and display its full contents to the user — not a summary, the actual content. This is their starting point and they need to see exactly what will run.
2. Offer to save a copy to their project (e.g. `triage.md` or `.claude/triage.md`) so they have a file they own and can edit.
3. Once a copy is saved (or they decline and want to use the example as-is), ask: **"Want to edit this before running, or run it as-is for your first test?"**

**Has an existing file:**

1. Read it and confirm the key settings: time window, filter threshold, and whether it includes a mode-selection step.
2. Summarise what it will do, then ask the same question: **"Want to edit anything, or run it as-is?"**

### Step 3: Run the workflow

Before executing, ask: **"Run all stages straight through, or step through each stage one at a time — pausing to show results before continuing?"**

In **step-by-step mode**: after each stage completes, summarise what it produced, discuss options and wait for confirmation before moving to the next.

Execute the workflow from the file, following its instructions exactly. Do not improvise steps or add actions not described in the file.

---

## Getting started

Build up your triage automation in three stages:

**1. Manual runs with recommendations.** Run the triage workflow manually and configure it to post comments with recommendations only — no status updates or external actions. Use this to tune your triage prompt until the classifications and recommendations match how your team would respond manually.

**2. Automate with recommendations.** Once you're happy with the output, automate the process to pick up new alerts on a schedule. Keep it in recommendations-only mode and monitor the results to verify the recommended actions meet your expectations.

**3. Replace recommendations with actions.** When you're confident in the automation, replace comment recommendations with real actions — status updates, Slack messages, ticket creation, or whatever fits your workflow.

See `references/triage-example.md` for a complete working example you can use as a starting point.
