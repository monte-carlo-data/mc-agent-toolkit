# Monte Carlo Remediation Skill

Investigate and fix data quality issues detected by Monte Carlo — automatically, with safety rails.

## What this does

When you have a data quality alert (freshness, volume, schema change, etc.), this skill guides an AI coding agent through the full remediation lifecycle:

1. **Investigate** — fetches alert details, runs TSA root cause analysis, maps blast radius via lineage, checks table state and monitoring coverage
2. **Discover capabilities** — scans connected MCP servers to determine what remediation actions are possible (pipeline restarts, dbt reruns, code fixes, notifications)
3. **Remediate** — proposes a fix with clear reasoning, confirms with the user, executes via available tools, and verifies the result
4. **Close out** — updates alert status, documents what was done, and suggests prevention measures

The skill works with whatever tools you have connected. If an Airflow MCP is available, it can restart pipelines. If only Slack is connected, it escalates with full context. If no external MCPs are connected, it produces a detailed remediation plan you can execute manually.

## Design: single document, not playbooks

This skill uses a single `SKILL.md` with reference examples — not separate playbooks for each alert type. Here's why:

**Opus-class models generalize better from examples + principles than from rigid playbook branching.** A single document that teaches the reasoning pattern (investigate → discover capabilities → select action → execute safely) handles edge cases and combined root causes naturally. Real incidents rarely fit neatly into a single category — a freshness alert might be caused by a schema change upstream that broke a dbt model. Rigid playbooks force the agent down a single path; principles let it compose the right response.

**Maintenance scales linearly with playbooks, but not with principles.** Adding a new alert type or remediation pattern means adding an example to `references/patterns.md` — not creating and maintaining a new playbook file with its own workflow, tool table, and edge case handling.

**The reference examples are illustrative, not prescriptive.** They show the agent what good remediation looks like for common patterns. The agent uses these as a starting point and adapts based on the specific TSA findings and available tools.

## Editor & stack compatibility

The skill works with any AI editor that supports MCP and the Agent Skills format — including Claude Code, Cursor, and VS Code.

| Stack | Support | Notes |
|---|---|---|
| Any MC-supported warehouse | ✅ Full | Investigation works for all warehouse types |
| Airflow / Dagster / Prefect | ✅ Full (with MCP) | Can restart pipelines automatically |
| dbt Cloud | ✅ Full (with MCP) | Can rerun dbt jobs automatically |
| GitHub / GitLab | ✅ Full (with MCP) | Can create PRs for code fixes |
| Slack / PagerDuty | ✅ Full (with MCP) | Can escalate and notify |
| No external MCPs | 🟡 Investigation only | Produces remediation plan for manual execution |

## Prerequisites

- Claude Code, Cursor, VS Code, or any editor with MCP support
- Monte Carlo account with Editor role or above
- Monte Carlo MCP server configured and authenticated

**Optional but recommended** (for automated execution):
- One or more external MCP servers for your pipeline orchestrator, code platform, or notification system

## Setup

### Via the mc-agent-toolkit plugin (recommended)

Install the plugin for your editor — it bundles the skill, MCP server, and permissions automatically. See the [main README](../../README.md#installing-the-plugin-recommended) for editor-specific instructions.

### Standalone

1. Configure the Monte Carlo MCP server:
   ```
   claude mcp add --transport http monte-carlo-mcp https://integrations.getmontecarlo.com/mcp
   ```

2. Install the skill:
   ```bash
   npx skills add monte-carlo-data/mc-agent-toolkit --skill remediation
   ```

3. Authenticate: run `/mcp` in your editor, select `monte-carlo-mcp`, and complete the OAuth flow.

4. Verify: ask your editor "Test my Monte Carlo connection" — it should call `testConnection` and confirm.

### Adding external MCPs for execution

The remediation skill can use any MCP server you have configured. Here are common ones for data teams:

| MCP Server | What it enables | Setup |
|---|---|---|
| **Airflow** | Restart DAGs, retry failed tasks | [Airflow MCP](https://github.com/apache/airflow-mcp) |
| **dbt Cloud** | Rerun dbt jobs | [dbt Cloud MCP](https://github.com/dbt-labs/dbt-cloud-mcp) |
| **GitHub** | Create PRs for code fixes | [GitHub MCP](https://github.com/github/github-mcp-server) |
| **Slack** | Notify teams, escalate issues | [Slack MCP](https://github.com/modelcontextprotocol/servers/tree/main/src/slack) |
| **PagerDuty** | Page on-call for critical incidents | [PagerDuty MCP](https://github.com/PagerDuty/mcp-server-pagerduty) |

## How to use it

Open your editor and prompt with the alert or issue you want to fix. Examples:

```
"Remediate alert ABC-123"

"Fix the freshness issue on the orders table"

"We have a schema change alert on raw_events — can you investigate and fix it?"

"Triage and remediate all open alerts on the analytics schema"

"The daily pipeline hasn't run — diagnose and fix it"
```

The skill handles the full workflow: investigation → capability discovery → remediation → verification → documentation. It will ask for confirmation before taking any destructive action.

## Safety

The skill has built-in safety rails:

- **Always explains** what it's about to do and why before executing
- **Always confirms** destructive operations (pipeline triggers, data modifications, code changes)
- **Escalates** when uncertain rather than guessing at a fix
- **Documents** all findings and actions on the alert
- **Never chains** multiple actions without verifying each one
- **Never modifies data** without explicit confirmation and a rollback plan

See `references/safety.md` for the complete safety protocol.
