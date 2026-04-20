# Skills

Skills are platform-agnostic instruction sets that tell an AI coding agent what to do. Each skill lives in its own directory with a `SKILL.md` definition and optional supporting files (scripts, references, assets). Skills can be used standalone with any MCP-capable editor, or bundled into the [mc-agent-toolkit plugin](../plugins/) for a richer experience with hooks and enforcement.

## Available Skills

| Skill | Description |
|---|---|
| **[Context Detection](context-detection/)** | Detects user context and routes to the right skill or workflow. Inspects workspace signals, conversation intent, and scoped API data to suggest or auto-activate the best skill. |
| **[Incident Response](incident-response/)** | Orchestrates incident response — triage alerts, investigate root causes, remediate issues, and add monitoring to prevent recurrence. Sequences existing skills into a guided workflow. |
| **[Asset Health](asset-health/)** | Checks the health of a data table — surfaces last activity, alerts, monitoring coverage, importance, and upstream dependency health from Monte Carlo. |
| **[Monitoring Advisor](monitoring-advisor/)** | Analyzes data coverage, creates monitors for warehouse tables and AI agents — covers coverage gaps, use-case analysis, data monitor creation, and agent observability. |
| **[Proactive Monitoring](proactive-monitoring/)** | Guides users from coverage analysis to monitor creation. Sequences asset-health assessment, gap identification via monitoring-advisor, and monitor creation into a guided workflow. |
| **[Prevent](prevent/)** | Surfaces Monte Carlo context (lineage, alerts, blast radius) before code changes, generates monitors-as-code, and produces targeted validation queries. |
| **[Generate Validation Notebook](generate-validation-notebook/)** | Generates SQL validation notebooks for dbt model changes, with targeted queries comparing baseline and development data. |
| **[Push Ingestion](push-ingestion/)** | Generates warehouse-specific collection scripts for pushing metadata, lineage, and query logs to Monte Carlo. |
| **[Automated Triage](automated-triage/)** | Guides you through designing, testing, and deploying automated alert triage for your Monte Carlo environment — covering the triage stages, customisation options, and a working example to start from. |
| **[Analyze Root Cause](analyze-root-cause/)** | Investigates data incidents — freshness, volume, schema, ETL, query changes — with systematic root cause analysis using lineage and observability data. |
| **[Storage Cost Analysis](storage-cost-analysis/)** | Identifies storage waste patterns (unread, zombie, dead-end tables) and recommends safe cleanup with cost estimates. |
| **[Performance Diagnosis](performance-diagnosis/)** | Diagnoses slow pipelines and expensive queries across Airflow, dbt, and Databricks with tiered investigation. |
| **[Remediation](remediation/)** | Investigates and remediates data quality alerts — runs TSA root cause analysis, discovers available tools, executes fixes (or escalates), and documents the resolution. |
| **[Tune Monitor](tune-monitor/)** | Analyzes a Monte Carlo metric monitor's alert history and recommends configuration changes to reduce noise — sensitivity, WHERE conditions, segment exclusions, schedule, and aggregation. |
| **[Connection Auth Rules](connection-auth-rules/)** | Build a Connection Auth Rules configuration for a Monte Carlo connection type. Fetches live connector schemas and transform steps from the apollo-agent repo. |

## Standalone Installation

Skills can be installed without the plugin via skill registries:

```bash
npx skills add monte-carlo-data/mc-agent-toolkit --skill prevent
```

Or by copying directly:

```bash
cp -r skills/prevent ~/.claude/skills/prevent
```

See individual skill READMEs for prerequisites and setup details.
