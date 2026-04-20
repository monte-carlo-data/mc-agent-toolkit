---
description: List all Monte Carlo data observability skills and workflows
---

List all available Monte Carlo skills and workflows. Present them grouped by category:

## Workflows

| Command | Description |
|---------|-------------|
| `/monte-carlo-incident-response` | Triage, investigate, fix, and prevent data incidents. Sequences automated-triage, root cause analysis, remediation, and monitor creation. |
| `/monte-carlo-proactive-monitoring` | Assess coverage gaps and create monitors. Sequences asset-health, coverage analysis, and monitor creation. |

## Skills

| Command | Description |
|---------|-------------|
| `/mc-triage` | Triage Monte Carlo alerts — score, classify, and investigate interactively or build an automated workflow |
| `/monitoring-advisor` | Analyze data coverage, identify gaps, and create monitors for warehouse tables and AI agents |
| `/mc-validate` | Generate and run validation queries for dbt model changes |
| `/tune-monitor` | Tune an existing Monte Carlo monitor's thresholds and configuration |
| `/mc-build-*` | Push ingestion commands — build metadata, lineage, and query log collectors |

## Skills Available via Natural Language

These skills don't have dedicated commands but activate automatically when you ask about their topics:

| Skill | Triggers on |
|-------|------------|
| Asset Health | "check health of table X", "how is X doing?", "status of X" |
| Root Cause Analysis | "why is this table stale?", "investigate this alert", "debug this incident" |
| Remediation | "fix this alert", "remediate this issue", "handle this incident" |
| Storage Cost Analysis | "unused tables", "storage costs", "zombie tables" |
| Performance Diagnosis | "slow pipeline", "expensive queries", "query performance" |
| Prevent | Auto-activates via hooks when you edit dbt models or SQL files |

**User provided input**: $ARGUMENTS
