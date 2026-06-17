# Monte Carlo Agent Toolkit — Claude Code Plugin

Claude Code plugin that brings Monte Carlo data observability into your editor. Bundles skills, hooks, commands, and permissions for all Monte Carlo features in a single plugin.

**Requires Python 3.10+.**

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

## Telemetry

The toolkit sends anonymous skill-usage telemetry by default — which skills are invoked, how often. Each event includes an opaque per-install UUID, a per-session UUID, the skill name, the toolkit version, and the editor it runs in (`claude-code`). No prompts, arguments, or code are ever sent.

To opt out, set `MC_AGENT_TOOLKIT_TELEMETRY_DISABLED=1` in your shell environment before starting Claude Code. The toolkit will not phone home.

The data is stored in Mixpanel and Datadog and is used only for product-development decisions about which skills to invest in. The UUIDs are generated locally on first session and stored under `~/.claude/mc-agent-toolkit/`. Deleting that directory resets your install identity to a fresh anonymous one.

## Available Features

| Feature | Description | Details |
|---|---|---|
| **Monitoring Advisor** | Analyzes data coverage, creates monitors for warehouse tables and AI agents — covers coverage gaps, use-case analysis, data monitor creation, and agent observability. | [Skill README](../../skills/monitoring-advisor/README.md) |
| **Prevent** | Gates dbt model edits with impact assessments, generates monitors-as-code, and produces targeted validation queries. Full hook enforcement. | [Skill README](../../skills/prevent/README.md) |
| **Generate Validation Notebook** | Generates SQL validation notebooks for dbt model changes from a PR or local repo. | [Skill README](../../skills/generate-validation-notebook/README.md) |
| **Push Ingestion** | Generates warehouse-specific collection scripts for pushing metadata, lineage, and query logs to Monte Carlo. Includes 10 `/mc-*` slash commands. | [Skill README](../../skills/push-ingestion/README.md) |
| **Automated Triage** | Guides you through automated alert triage — scoring, deep troubleshooting, classification, and actions. Requires extended MCP toolset. | [SKILL](../../skills/automated-triage/SKILL.md) |

The Prevent feature includes **PreToolUse hooks that can block edits to dbt SQL files** until an impact assessment runs. The hooks only fire on `.sql` files inside dbt model, macro, or snapshot directories — they do not affect non-dbt files.

**To disable the Prevent hooks**, set `MC_PREVENT_HOOKS_DISABLED=1` in your environment (e.g. in your `.zshrc` or `.bashrc`, or via `.claude/settings.json` under `env`). The hooks will exit immediately without blocking any edits.

See the [Prevent Hook Behavior](../README.md#prevent-hook-behavior) section in the plugins README for full details on scope and configuration.

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
