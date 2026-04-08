# Monte Carlo Agent Toolkit — Claude Code Plugin

Claude Code plugin that brings Monte Carlo data observability into your editor. Bundles skills, hooks, commands, and permissions for all Monte Carlo features in a single plugin.

## Installation

### Via Marketplace (recommended)

1. Add the marketplace:
   ```
   /plugin marketplace add monte-carlo-data/mc-agent-toolkit
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

| Feature | Description | Details |
|---|---|---|
| **Prevent** | Gates dbt model edits with impact assessments, generates monitors-as-code, and produces targeted validation queries. Full hook enforcement. | [Skill README](../../skills/prevent/README.md) |
| **Generate Validation Notebook** | Generates SQL validation notebooks for dbt model changes from a PR or local repo. | [Skill README](../../skills/generate-validation-notebook/README.md) |
| **Push Ingestion** | Generates warehouse-specific collection scripts for pushing metadata, lineage, and query logs to Monte Carlo. Includes 10 `/mc-*` slash commands. | [Skill README](../../skills/push-ingestion/README.md) |

The Prevent feature includes hooks that enforce the impact-assessment-first workflow. See the [Prevent Hook Behavior](../README.md#prevent-hook-behavior) section in the plugins README for details.

## Updating

```
claude plugin update mc-agent-toolkit@mc-marketplace
```

## Uninstalling

```
claude plugin remove mc-agent-toolkit
```

The uninstall script restores standalone skill backups if they exist.

## Architecture

See the [plugins README](../README.md) for the overall plugin architecture, editor support comparison, and hook format details.

## Changelog

See [CHANGELOG.md](CHANGELOG.md).
