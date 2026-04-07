# Monte Carlo Agent Toolkit — Claude Code Plugin

Claude Code plugin that brings Monte Carlo data observability into your editor. Bundles skills, hooks, commands, and permissions for all Monte Carlo features in a single plugin.

## Installation

### Via Marketplace (recommended)

1. Add the marketplace:
   ```
   /plugin marketplace add monte-carlo-data/mc-marketplace
   ```
2. Install the plugin:
   ```
   /plugin install mc-agent-toolkit@mc-marketplace
   ```
3. Updates — `claude plugin update` pulls in the latest changes.

### Manual

```bash
git clone https://github.com/monte-carlo-data/mc-agent-toolkit.git
cd mc-agent-toolkit
claude plugin install plugins/claude-code
```

Restart Claude Code after installing.

## Setup

1. **Authenticate with Monte Carlo** — run `/mcp` in Claude Code, select the Monte Carlo server, and complete the OAuth flow.
2. **Verify** — ask Claude: "Test my Monte Carlo connection."

## Available Features

### MC Prevent

Automatically gates dbt model edits with impact assessments, surfaces table health and lineage context, generates monitors-as-code, and produces targeted validation queries — all before you merge.

| Component | What it does |
|---|---|
| **Pre-edit hook** | Blocks edits to dbt models (and macros/snapshots) until a change impact assessment has been presented. |
| **Post-edit hook** | Tracks which models were modified in the session for downstream validation. |
| **Pre-commit hook** | Gates `git commit` when modified models have unresolved monitor coverage gaps. |
| **Turn-end hook** | Fires at the end of each turn to inject validation reminders when models were edited without running validation queries. |
| **`/mc-validate` command** | Explicitly generates validation queries for all dbt models changed in the session. |

**How it works:**

1. **You edit a model** — the pre-edit hook blocks until a change impact assessment runs. Claude surfaces downstream blast radius, active alerts, monitor coverage, and a risk-tiered recommendation.
2. **You confirm and edit** — the post-edit hook records the change. The skill offers to generate monitors for new logic.
3. **You commit** — the pre-commit hook checks for unresolved monitor coverage gaps flagged during the assessment.
4. **You validate** — run `/mc-validate` or ask Claude to generate validation queries. Targeted SQL checks are saved to `validation/<table>_<timestamp>.sql`.

### MC Generate Validation Notebook

Generates executable validation queries from a pull request and packages them into Monte Carlo notebooks for direct testing.

### MC Push Ingestion

Gives Claude expert knowledge of Monte Carlo's push ingestion model and generates ready-to-run collection scripts for your specific data warehouse.

**Slash commands:**

| Command | Description |
|---|---|
| `/mc-build-metadata-collector` | Generate a metadata collection script for your warehouse |
| `/mc-build-lineage-collector` | Generate a lineage collection script for your warehouse |
| `/mc-build-query-log-collector` | Generate a query log collection script for your warehouse |
| `/mc-validate-metadata` | Verify pushed metadata via the Monte Carlo GraphQL API |
| `/mc-validate-lineage` | Verify pushed lineage via the Monte Carlo GraphQL API |
| `/mc-validate-query-logs` | Verify pushed query logs via the Monte Carlo GraphQL API |
| `/mc-create-lineage-node` | Create a custom lineage node via GraphQL |
| `/mc-create-lineage-edge` | Create a custom lineage edge via GraphQL |
| `/mc-delete-lineage-node` | Delete a custom lineage node via GraphQL |
| `/mc-delete-push-tables` | Delete push-ingested tables via GraphQL |

**Prerequisites:** Push ingestion requires two separate Monte Carlo API keys (ingestion key + GraphQL API key). See [`prerequisites.md`](../../skills/push-ingestion/references/prerequisites.md) for setup instructions.

## Directory structure

```
plugins/claude-code/
├── .claude-plugin/plugin.json    # Plugin manifest
├── .mcp.json                     # Monte Carlo MCP server config
├── settings.json                 # MCP tool auto-approve permissions
├── hooks/
│   └── prevent/                  # MC Prevent hook adapters
│       ├── hooks.json
│       ├── pre_edit_hook.py
│       ├── post_edit_hook.py
│       ├── pre_commit_hook.py
│       ├── turn_end_hook.py
│       ├── validate_command.py
│       └── lib/                  # Shared utilities (symlink)
├── commands/
│   ├── prevent/                  # MC Prevent commands
│   └── push-ingestion/           # Push ingestion commands (10 /mc-* commands)
├── skills/                       # Symlinks to shared skill definitions
│   ├── prevent/
│   ├── generate-validation-notebook/
│   └── push-ingestion/
├── evals/
│   └── push-ingestion/           # Push ingestion evaluation suite
├── scripts/
│   ├── install.sh
│   └── uninstall.sh
└── tests/
    └── prevent/                  # Hook unit tests
```

## Architecture

- **Skills** — symlinked from `skills/` at the repo root (shared across all editors)
- **Shared hook logic** — symlinked from `plugins/shared/prevent/lib/` (platform-agnostic business logic)
- **Adapter hooks** — Claude Code-specific JSON parsing and output formatting under `hooks/prevent/`
- **Commands** — slash commands namespaced under `commands/<skill>/`
- **MCP config** — Monte Carlo MCP server connection (shared by all features)

## Updating

```
claude plugin update mc-agent-toolkit@mc-marketplace
```

## Uninstalling

```
claude plugin remove mc-agent-toolkit
```

The uninstall script restores standalone skill backups if they exist.

## Changelog

See [CHANGELOG.md](CHANGELOG.md).
