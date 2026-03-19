# Monte Carlo Claude Plugin

Bring Monte Carlo data observability into your editor — automatically, before you write a single line of code.

When you reference a dbt model or table, Monte Carlo context comes to you: table health, active alerts, lineage, and downstream blast radius. Your AI editor uses that context to shape the code it writes — not just surface it. If you try to rename a column with 500 downstream dependents, the editor recommends a safe transition strategy and explains why, citing the specific MC data it found. When you add new logic, it generates and deploys the right monitor for your logic — validation, metric, comparison, or custom SQL — before you merge.

## Editor & Stack Compatibility

The plugin works with any AI editor that supports MCP and the Agent Skills format — including Claude Code, Cursor, and VS Code.

| Stack | Support | Notes |
|---|---|---|
| dbt + any MC-supported warehouse | ✅ Full | Optimized and tested |
| SQL-first, no dbt | 🟡 Partial | Core workflows work via explicit prompting |
| Databricks notebooks | 🟡 Partial | Health check, impact assessment, and alert triage work |
| SQLMesh | 🟡 Partial | Core workflows work; native project structure support coming soon |
| PySpark / non-SQL pipelines | 🟠 Limited | Manual prompting only |

## Prerequisites

- Claude Code, Cursor, VS Code, or any editor with MCP support
- Monte Carlo account with Editor role or above
- [MC CLI](https://docs.getmontecarlo.com/docs/using-the-cli) installed for monitor deployment (`pip install montecarlodata`)
- `python3` and `pyyaml` (`pip install pyyaml`) for the `generate-validation-notebook` skill

## Setup

### Step 1 — Obtain an MCP server key

1. Go to **Monte Carlo → Settings → API Keys**
2. Click **Add** and select type **MCP Server**
3. Copy the key — it has two parts: `KEY_ID` and `KEY_SECRET`

MCP keys are separate from standard API keys. Standard keys work for the CLI; MCP keys work for the editor integration.

### Step 2 — Clone this repo and initialize submodules

```bash
git clone --recurse-submodules git@github.com:monte-carlo-data/monte-carlo-claude-plugin.git
cd monte-carlo-claude-plugin
```

If you already cloned without `--recurse-submodules`:
```bash
git submodule update --init --recursive
```

### Step 3 — Install the skills

Copy SKILL.md files to your editor's skills directory:

```bash
mkdir -p ~/.claude/skills/monte-carlo
cp skills/monte-carlo/safe-change/SKILL.md ~/.claude/skills/monte-carlo/safe-change.md
cp skills/monte-carlo/generate-validation-notebook/SKILL.md ~/.claude/skills/monte-carlo/generate-validation-notebook.md
```

### Step 4 — Configure your MCP server

Copy `.mcp.json.example` to your project directory and fill in your credentials:

```bash
cp .mcp.json.example /path/to/your/project/.mcp.json
```

Then edit the file and replace `<KEY_ID>` and `<KEY_SECRET>` with your MCP key values.

### Step 5 — Verify the connection

In Claude Code, paste:

> "Test my Monte Carlo connection"

Claude will call `testConnection` and confirm your credentials are working.

### Step 6 — Configure tool permissions (recommended)

Add the following to `.claude/settings.local.json` in your project to allow Monte Carlo MCP tools without prompting on every call:

```json
{
  "allowedTools": [
    "mcp__monte-carlo__*"
  ]
}
```

## Available Skills

### safe-change

Automatically activates when a dbt model, SQL file, or table is referenced. See [safe-change/README.md](skills/monte-carlo/safe-change/README.md) for full documentation.

### generate-validation-notebook

Generate SQL validation notebooks for dbt PR changes:

```
/monte-carlo:generate-validation-notebook <PR_URL or local path>
```

## Deploying Generated Monitors

When Claude generates a monitor, it saves the YAML to `monitors/<table>.yml`. Deploy with:

```bash
montecarlo monitors apply --dry-run    # preview
montecarlo monitors apply --auto-yes   # apply
```

Your project needs a `montecarlo.yml` config in the working directory:

```yaml
version: 1
namespace: <your-namespace>
default_resource: <your-warehouse-name>
```

## Troubleshooting

See [skills/monte-carlo/safe-change/references/TROUBLESHOOTING.md](skills/monte-carlo/safe-change/references/TROUBLESHOOTING.md) for common setup and runtime issues.
