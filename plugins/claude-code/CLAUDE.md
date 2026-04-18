# Monte Carlo Agent Toolkit

This plugin provides data observability skills powered by Monte Carlo.

## Session Start

On your first response in a session (when there is only one human message so far),
use the Glob tool to search for `**/dbt_project.yml` or `**/montecarlo.yml` anywhere
in the workspace (either qualifies; the file may be in a subdirectory).
If at least one match is found, append this brief note to your response:

> I see this is a dbt project with Monte Carlo. If you run into data issues,
> I can help triage alerts, investigate root causes, and set up monitoring.
> I'll also flag impact when you edit models. Ask me anything or type /mc
> to see what's available.

Rules:
- One brief paragraph, appended to your actual response
- Once per session only
- Silent if neither file is found
- No API calls — workspace glob only

## Routing

When a user sends a message, check if it matches a row in this routing table.
**Only apply routing when no skill or workflow is currently active** — if a
skill is already handling the conversation, it owns the session. Do not
intercept mid-task messages.

**Important:** Route based on the user's **message intent**, not just which file is open.
Having a `.sql` file open provides table context (use the filename to identify the table),
but it does NOT mean the user is editing it. Only match the "editing" row when the user is
actively making or asking to make changes to a model.

| User intent | Route to |
|---|---|
| Actively editing or about to edit a dbt model or SQL file (e.g., "change this model", "refactor this query", making code changes) | `prevent` skill (auto-activates via hooks — no manual routing needed) |
| Create a specific monitor (type + table known) | Read and follow `skills/monitoring-advisor/SKILL.md` |
| Check health of a specific table | Read and follow `skills/asset-health/SKILL.md` |
| Generate validation notebook / compare baseline vs dev | Read and follow `skills/generate-validation-notebook/SKILL.md` |
| Set up push ingestion / data collection scripts | Read and follow `skills/push-ingestion/SKILL.md` |
| Storage costs, unused tables, zombie tables | Read and follow `skills/storage-cost-analysis/SKILL.md` |
| Slow pipelines, expensive queries | Read and follow `skills/performance-diagnosis/SKILL.md` |
| Mentions alerts, incidents, data broken/stale, coverage gaps, Monte Carlo, or data quality — but doesn't clearly match a single skill above | Read and follow `skills/context-detection/SKILL.md` |

If the message does not match any row, it is not data-related — respond
normally without activating any Monte Carlo skill.
