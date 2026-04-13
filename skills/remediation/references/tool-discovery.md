# Tool Discovery at Runtime

This reference explains how to discover what remediation tools are available to you at runtime. Since different users have different MCP servers configured, you must check before attempting any external action.

## How MCP tools are named

In Claude Code and other MCP-capable editors, external tools follow the naming convention:

```
mcp__<server_name>__<tool_name>
```

For example:
- `mcp__airflow__trigger_dag_run` — an Airflow tool
- `mcp__dbt_cloud__trigger_run` — a dbt Cloud tool
- `mcp__github__create_pull_request` — a GitHub tool
- `mcp__slack__send_message` — a Slack tool

Monte Carlo tools also follow this pattern but may use different server names depending on configuration:
- `mcp__monte_carlo__getAlerts`
- `mcp__mc__search`

## Discovery procedure

### Step 1: Scan your available tools

Look through your tool list (available in your system prompt or tool inventory) for any tools matching `mcp__*__*`. Group them by server name.

### Step 2: Map servers to capabilities

Use this mapping table to understand what each server enables:

| Server Name Pattern | Capability | Remediation Actions |
| ------------------- | ---------- | ------------------- |
| `*airflow*` | Pipeline orchestration | Trigger DAG runs, retry failed tasks, check DAG/task status, pause/unpause DAGs |
| `*dagster*` | Pipeline orchestration | Launch pipeline runs, check run status, terminate runs |
| `*prefect*` | Pipeline orchestration | Create flow runs, check flow run status |
| `*dbt*` | dbt operations | Trigger job runs, get run status, list jobs, cancel runs |
| `*github*` | Code changes | Create branches, create/update PRs, create issues, read file contents |
| `*gitlab*` | Code changes | Create merge requests, create issues, read file contents |
| `*slack*` | Notifications | Send messages to channels, post thread replies, search messages |
| `*pagerduty*` | Incident management | Create incidents, escalate, acknowledge, resolve |
| `*teams*` | Notifications | Send messages, create cards |
| `*jira*` | Issue tracking | Create issues, update status, add comments |
| `*snowflake*` | Warehouse access | Execute queries, get table info |
| `*bigquery*` | Warehouse access | Execute queries, get table info |
| `*databricks*` | Warehouse access + orchestration | Execute queries, trigger jobs, check job status |
| `*fivetran*` | Ingestion | Trigger connector sync, check sync status |

### Step 3: Assess coverage

For the current remediation task, determine:

1. **Can I investigate?** — Monte Carlo MCP is always needed. If it's not connected, you cannot proceed.
2. **Can I execute the fix?** — Check if the needed orchestration/code/notification tool is available.
3. **Can I notify the right people?** — Check for Slack, PagerDuty, or similar.

### Step 4: Report capabilities

Present what you found to the user before proceeding:

> "I've checked your connected MCP servers. For this remediation, I can:
> - ✅ Investigate the issue (Monte Carlo)
> - ✅ Restart the Airflow DAG (Airflow MCP connected)
> - ❌ Create a code fix (no GitHub/GitLab MCP)
> - ✅ Notify the team (Slack MCP connected)"

## Graceful degradation

When a needed tool is NOT available, follow this priority:

### Priority 1: Provide actionable manual instructions

Give the user the exact commands or steps to execute themselves:

```
# If Airflow MCP is not available but you identified the DAG:
"The DAG `etl_orders_daily` needs to be triggered. Run:
  airflow dags trigger etl_orders_daily
Or via the Airflow UI: navigate to DAGs → etl_orders_daily → Trigger DAG"

# If dbt Cloud MCP is not available:
"dbt job 'Daily Transform' (job ID: 12345) needs to be rerun. Run:
  dbt Cloud UI → Jobs → Daily Transform → Run Now
Or via CLI: dbt run --select stg_orders+"

# If GitHub MCP is not available:
"File `models/staging/stg_orders.sql` needs line 14 changed from
  `user_id` to `customer_id`. Create a branch and PR with this change."
```

### Priority 2: Escalate via available notification channels

If Slack or PagerDuty is available, send the remediation plan:

```
Slack message format:
"🔧 Remediation needed — [table_name]

Alert: [type] ([severity])
Root cause: [TSA summary]

Required action: [specific fix]
Manual steps:
1. [step 1]
2. [step 2]

I couldn't execute this automatically because [reason].
Alert link: [MC alert URL]"
```

### Priority 3: Document on the alert

Always, regardless of what other tools are available:

```
createOrUpdateAlertComment(
  alert_id="<alert_uuid>",
  comment="## Remediation Plan\n\n**Root cause:** [summary]\n**Required action:** [specific fix]\n**Manual steps:**\n1. [step]\n2. [step]\n\n**Note:** Automated execution was not possible — [tool name] MCP not connected.\n**Investigated by:** AI agent via remediation skill"
)
```

## Tool-specific notes

### Airflow MCP

Common tools you might find:
- `trigger_dag_run` — start a DAG run (may need `dag_id`, optionally `conf` for parameters)
- `get_dag_runs` — check recent runs and their status
- `get_task_instances` — get task-level status for a specific run
- `clear_task_instances` — retry failed tasks (resets their state)

**Caution:** `trigger_dag_run` starts a NEW run. If the issue was a failed task in an existing run, `clear_task_instances` (retry) may be more appropriate than starting fresh.

### dbt Cloud MCP

Common tools you might find:
- `trigger_run` / `trigger_job` — start a dbt job run (needs `job_id` or `account_id` + `job_id`)
- `get_run` — check run status and results
- `list_jobs` — find the right job ID
- `cancel_run` — stop a running job

**Note:** dbt Cloud jobs often include multiple models. Triggering a job reruns ALL models in that job, not just the failed one. Consider whether a full rerun is appropriate.

### GitHub MCP

Common tools you might find:
- `create_pull_request` — open a PR (needs `owner`, `repo`, `title`, `body`, `head`, `base`)
- `create_issue` — open an issue for tracking
- `create_or_update_file` — directly edit a file on a branch
- `create_branch` — create a new branch for the fix

**Best practice:** For code fixes, create a branch → make the change → open a PR. Don't push directly to main.

### Slack MCP

Common tools you might find:
- `send_message` / `post_message` — send to a channel (needs `channel` and `text`)
- `search_channels` — find the right channel
- `send_message_draft` — create a draft for review before sending

**Tip:** If you don't know which channel to post to, ask the user. Don't guess — posting to the wrong channel is noisy.

### PagerDuty MCP

Common tools you might find:
- `create_incident` — create a new incident (needs `service_id`, `title`, `urgency`)
- `acknowledge_incident` — acknowledge an existing incident
- `resolve_incident` — mark incident as resolved

**Use PagerDuty for HIGH severity alerts only.** Don't page people for low-severity issues that can wait.
