# Monte Carlo Skills

Public Claude Code skills by [Monte Carlo Data](https://www.montecarlodata.com/).

## Installation

**Option A — Manual (copy skill files directly):**

```bash
# safe-change
mkdir -p ~/.claude/skills/monte-carlo-safe-change
curl -o ~/.claude/skills/monte-carlo-safe-change/SKILL.md \
  https://raw.githubusercontent.com/monte-carlo-data/mcd-skills/main/safe-change/SKILL.md

# generate-validation-notebook (includes required Python scripts)
mkdir -p ~/.claude/skills/monte-carlo-generate-validation-notebook/scripts
curl -o ~/.claude/skills/monte-carlo-generate-validation-notebook/SKILL.md \
  https://raw.githubusercontent.com/monte-carlo-data/mcd-skills/main/generate-validation-notebook/SKILL.md
curl -o ~/.claude/skills/monte-carlo-generate-validation-notebook/scripts/generate_notebook_url.py \
  https://raw.githubusercontent.com/monte-carlo-data/mcd-skills/main/generate-validation-notebook/scripts/generate_notebook_url.py
curl -o ~/.claude/skills/monte-carlo-generate-validation-notebook/scripts/resolve_dbt_schema.py \
  https://raw.githubusercontent.com/monte-carlo-data/mcd-skills/main/generate-validation-notebook/scripts/resolve_dbt_schema.py
```

**Option B — via [skills.sh](https://skills.sh) CLI:**

```bash
npx skilladd monte-carlo-data/mcd-skills
```

**Option C — via Claude Code plugin marketplace:**

```
/plugin marketplace add monte-carlo-data/mcd-skills
/plugin install monte-carlo@mcd-skills
```

> **Note:** The `safe-change` skill requires the [Monte Carlo MCP Server](https://docs.getmontecarlo.com/docs/mcp-server) to be configured. See [setup instructions](safe-change/README.md#setup) before use.

## Available Skills

### safe-change
Automatically activates when a dbt model, SQL file, or table is referenced. Surfaces Monte Carlo context — table health, active alerts, lineage, blast radius — before any code is written, and uses those findings to shape code recommendations.

See [Introduction](safe-change/README.md), [Installation](safe-change/README.md#setup) and [Usage](safe-change/README.md#how-to-use-it). Requires the [Monte Carlo MCP Server](https://docs.getmontecarlo.com/docs/mcp-server).

### generate-validation-notebook

Generate SQL validation notebooks for dbt PR changes. Analyzes a GitHub PR or local dbt repo, classifies models as new or modified, and produces a notebook with validation queries.

```
/monte-carlo:generate-validation-notebook <PR_URL or local path>
```
