# Skills

Skills are platform-agnostic instruction sets that tell an AI coding agent what to do. Each skill lives in its own directory with a `SKILL.md` definition and optional supporting files (scripts, references, assets). Skills can be used standalone with any MCP-capable editor, or bundled into the [mc-agent-toolkit plugin](../plugins/) for a richer experience with hooks and enforcement.

## Available Skills

| Skill | Description |
|---|---|
| **[Prevent](prevent/)** | Surfaces Monte Carlo context (lineage, alerts, blast radius) before code changes, generates monitors-as-code, and produces targeted validation queries. |
| **[Generate Validation Notebook](generate-validation-notebook/)** | Generates SQL validation notebooks for dbt model changes, with targeted queries comparing baseline and development data. |
| **[Push Ingestion](push-ingestion/)** | Generates warehouse-specific collection scripts for pushing metadata, lineage, and query logs to Monte Carlo. |

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
