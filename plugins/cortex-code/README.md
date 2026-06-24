# Monte Carlo Agent Toolkit — Cortex Code Plugin

Cortex Code (CoCo) plugin that brings Monte Carlo data observability into Snowflake's CLI coding agent. Bundles skills, hooks, commands, and the Monte Carlo MCP server in a single plugin.

**Requires Python 3.10+ and the [Cortex Code CLI](https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code).**

## Installation

Cortex Code's `cortex plugin install` can't consume this plugin directly from the repo, because the skill entries are symlinks shared across all editor plugins (they point outside the plugin directory, which the installer rejects). The install script materializes a symlink-resolved copy and installs that for you:

```bash
git clone https://github.com/monte-carlo-data/mc-agent-toolkit.git
cd mc-agent-toolkit
bash plugins/cortex-code/scripts/install.sh
```

The script clones (or uses your local checkout), resolves the symlinks into a staging copy, and runs `cortex plugin install`. Verify with:

```bash
cortex plugin list
```

You should see `mc-agent-toolkit` listed as `[enabled, managed]` with command, skill, hook, and MCP-server components.

## Setup

1. **Authenticate with Monte Carlo** — run `/mcp` inside Cortex Code (or `cortex mcp` from the CLI), select the Monte Carlo server, and complete the OAuth flow.
2. **Verify** — ask Cortex: "Test my Monte Carlo connection."

## Usage

- **Invoke a skill explicitly** with `$<skill-name>`, e.g. `$monte-carlo-prevent` or `$monte-carlo-asset-health`. Run `/skill list` to see what's available.
- **Auto-activation** — Cortex selects the right skill from your request (e.g. editing a dbt model activates Prevent; "how healthy is this table?" activates Asset Health).
- **Validation** — run `/mc-validate` (or `/mc-agent-toolkit:mc-validate`) to generate or run validation queries for the dbt models you changed this session.

## Telemetry

The toolkit sends anonymous skill-usage telemetry by default — which skills are invoked, how often. Each event includes an opaque per-install UUID, a per-session UUID, the skill name, the toolkit version, and the editor it runs in (`cortex-code`). No prompts, arguments, or code are ever sent.

It also sends a `Toolkit Installed` beacon once per toolkit version — the first time you start Cortex Code after installing, and again after each version change — deduped by a local marker, independent of whether you ever run a skill. It carries the install/session UUIDs, toolkit version, and editor (`cortex-code`) — no skill field. Like the skill beacon, it is fail-open and non-blocking.

**Authenticated MCP traffic (v1.13.3+).** The same anonymous `install_id`, a per-session id, and the toolkit version also ride as HTTP headers (`x-mcd-toolkit-install-id`, `x-mcd-toolkit-session-id`, `x-mcd-toolkit-version`) on **authenticated** requests to the Monte Carlo MCP server. This lets the otherwise-anonymous install record be correlated with your account's MCP tool usage server-side — still no prompts, arguments, or code, only the opaque ids and version. The opt-out below disables these headers too.

To opt out, set `MC_AGENT_TOOLKIT_TELEMETRY_DISABLED=1` in your shell environment before starting Cortex Code. The toolkit will not phone home.

The data is stored in Mixpanel and Datadog and is used only for product-development decisions about which skills to invest in. The UUIDs are generated locally on first session and stored under `~/.snowflake/cortex/mc-agent-toolkit/` (Cortex Code's own config home) — separate from any Claude Code toolkit install, so each editor keeps its own anonymous identity. Deleting that directory resets the Cortex Code install identity to a fresh one.

## Available Features

| Feature | Description | Details |
|---|---|---|
| **Monitoring Advisor** | Analyzes data coverage, creates monitors for warehouse tables and AI agents — covers coverage gaps, use-case analysis, data monitor creation, and agent observability. | [Skill README](../../skills/monitoring-advisor/README.md) |
| **Prevent** | Gates dbt model edits with impact assessments, generates monitors-as-code, and produces targeted validation queries. Full hook enforcement. | [Skill README](../../skills/prevent/README.md) |
| **Generate Validation Notebook** | Generates SQL validation notebooks for dbt model changes from a PR or local repo. | [Skill README](../../skills/generate-validation-notebook/README.md) |
| **Push Ingestion** | Generates warehouse-specific collection scripts for pushing metadata, lineage, and query logs to Monte Carlo. Includes 10 `/mc-*` slash commands. | [Skill README](../../skills/push-ingestion/README.md) |
| **Automated Triage** | Guides you through automated alert triage — scoring, deep troubleshooting, classification, and actions. Requires extended MCP toolset. | [SKILL](../../skills/automated-triage/SKILL.md) |

All 17 skills are bundled — see the [skills directory](../../skills/) for the full list.

The Prevent feature includes **PreToolUse hooks that block edits to dbt SQL files** until an impact assessment runs. The hooks only fire on `.sql` files inside dbt model, macro, or snapshot directories — they do not affect non-dbt files.

**To disable the Prevent hooks**, set `MC_PREVENT_HOOKS_DISABLED=1` in your environment. The hooks will exit immediately without blocking any edits.

See the [Prevent Hook Behavior](../README.md#prevent-hook-behavior) section in the plugins README for full details on scope and configuration.

## Updating

Re-run the installer from your repo checkout (the clone from the Installation step) to pull the latest skills and hooks:

```bash
cd mc-agent-toolkit
git pull
bash plugins/cortex-code/scripts/install.sh
```

## Uninstalling

```bash
cortex plugin uninstall mc-agent-toolkit
```

## Architecture

Cortex Code wraps Claude Code, so this plugin reuses the same SKILL.md skills, the same prevent hook lifecycle (PreToolUse/PostToolUse/Stop), and the same MCP configuration. The one Cortex-specific adaptation is the prevent transcript reader: Cortex stores session messages in a sibling `<id>.history.jsonl` and persists hook output back into the transcript, so the gate scans only assistant-authored text to find its completion marker. See the [plugins README](../README.md) for the editor-support comparison and hook-format details, and the [Plugin Architecture Guide](../../docs/plugin-architecture-guide.md) for the shared-core/adapter design.

## Changelog

See [CHANGELOG.md](CHANGELOG.md).
