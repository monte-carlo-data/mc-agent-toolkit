# Skills

Skills are platform-agnostic instruction sets that tell an AI coding agent what to do. Each skill lives in its own directory with a `SKILL.md` definition and optional supporting files (scripts, references, assets). Skills can be used standalone with any MCP-capable editor, or bundled into the [mc-agent-toolkit plugin](../plugins/) for a richer experience with hooks and enforcement.

## Available Skills

| Skill | Description |
|---|---|
| **[Asset Health](asset-health/)** | Checks the health of a data table — surfaces last activity, alerts, monitoring coverage, importance, and upstream dependency health from Monte Carlo. |
| **[Monitoring Advisor](monitoring-advisor/)** | Analyzes data coverage across warehouses and use cases, identifies monitoring gaps, and creates monitors to protect critical data. |
| **[Monitor Creation](monitor-creation/)** | Guides AI agents through creating monitors correctly — validates tables, fields, and parameters before generating monitors-as-code YAML. |
| **[Prevent](prevent/)** | Surfaces Monte Carlo context (lineage, alerts, blast radius) before code changes, generates monitors-as-code, and produces targeted validation queries. |
| **[Generate Validation Notebook](generate-validation-notebook/)** | Generates SQL validation notebooks for dbt model changes, with targeted queries comparing baseline and development data. |
| **[Push Ingestion](push-ingestion/)** | Generates warehouse-specific collection scripts for pushing metadata, lineage, and query logs to Monte Carlo. |
| **[Automated Triage](automated-triage/)** | Guides you through designing, testing, and deploying automated alert triage for your Monte Carlo environment — covering the triage stages, customisation options, and a working example to start from. |
| **[Analyze Root Cause](analyze-root-cause/)** | Investigates data incidents — freshness, volume, schema, ETL, query changes — with systematic root cause analysis using lineage and observability data. |
| **[Storage Cost Analysis](storage-cost-analysis/)** | Identifies storage waste patterns (unread, zombie, dead-end tables) and recommends safe cleanup with cost estimates. |
| **[Performance Diagnosis](performance-diagnosis/)** | Diagnoses slow pipelines and expensive queries across Airflow, dbt, and Databricks with tiered investigation. |
| **[Remediation](remediation/)** | Investigates and remediates data quality alerts — runs TSA root cause analysis, discovers available tools, executes fixes (or escalates), and documents the resolution. |
| **[Agent Monitoring](agent-monitoring/)** | Investigation and monitor creation guide for AI agent observability. |

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
