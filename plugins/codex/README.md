# Monte Carlo Agent Toolkit — Codex Plugin

Data observability skills and enforcement hooks for AI coding agents, powered by Monte Carlo.

**Requires Python 3.10+.**

## Installation

Run the install script from your target repo:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/monte-carlo-data/mcd-agent-toolkit/main/plugins/codex/scripts/install.sh)
```

Or specify a target repo path:

```bash
bash install.sh /path/to/your/repo
```

The script handles everything:
1. Copies the plugin into `<repo>/plugins/mc-agent-toolkit/`
2. Registers skills in `<repo>/.agents/skills/` (prevent, generate-validation-notebook, push-ingestion)
3. Writes hooks to `<repo>/.codex/hooks.json` (project-level)
4. Creates `.agents/plugins/marketplace.json` for Codex plugin discovery
5. Adds the Monte Carlo MCP server to `~/.codex/config.toml` with the required `User-Agent` header (workaround for [codex#12859](https://github.com/openai/codex/issues/12859))
6. Enables `codex_hooks` in your config
7. Opens a browser for OAuth login with your Monte Carlo account

After installation, restart Codex in your project. You should see "Installed mc-agent-toolkit plugin" on startup.

## How It Works

The plugin uses two hooks to enforce the Monte Carlo Prevent workflow:

| Hook | Event | Matcher | Purpose |
|------|-------|---------|---------|
| pre_commit | PreToolUse | Bash | Prompt for validation before git commit |
| turn_end | Stop | — | Suggest validation queries for pending tables |

**Note:** Codex currently only emits PreToolUse/PostToolUse for the Bash tool. Pre-edit and post-edit hooks (Edit|Write) are included in the plugin for forward compatibility but are not registered until Codex expands tool coverage.

## Skills

All skills are registered in `.agents/skills/` during installation.

| Skill | Description | Details |
|---|---|---|
| **Prevent** | Gates dbt model edits with impact assessments, generates monitors-as-code, and produces targeted validation queries. | [Skill README](../../skills/prevent/README.md) |
| **Generate Validation Notebook** | Generates SQL validation notebooks for dbt model changes from a PR or local repo. | [Skill README](../../skills/generate-validation-notebook/README.md) |
| **Push Ingestion** | Generates warehouse-specific collection scripts for pushing metadata, lineage, and query logs to Monte Carlo. | [Skill README](../../skills/push-ingestion/README.md) |
| **Automated Triage** | Guides you through automated alert triage — scoring, deep troubleshooting, classification, and actions. Requires extended MCP toolset. | [SKILL](../../skills/automated-triage/SKILL.md) |

Codex activates skills automatically when you work with dbt models or SQL files. You can also invoke prevent explicitly with `$monte-carlo-prevent`.

## Known Issues

Codex hook coverage is incomplete, which may cause hooks to not fire consistently:

- [openai/codex#16732](https://github.com/openai/codex/issues/16732): `ApplyPatchHandler` doesn't emit PreToolUse/PostToolUse hook events — hooks only fire for the Bash tool. When Codex uses its native edit path (`• Edited`), our pre-edit gate is bypassed entirely. We work around this by parsing `apply_patch` commands within the Bash hook, but native edits remain ungated.
- [openai/codex#14754](https://github.com/openai/codex/issues/14754): Add PreToolUse and PostToolUse hook events for code quality enforcement — tracks the broader request for non-Bash hook parity.
- [openai/codex#16246](https://github.com/openai/codex/issues/16246): PostToolUse is missing for tools that complete via exec session / polling path — prevents reliable post-edit tracking.

The skill-based impact assessment (via `SKILL.md`) works reliably regardless of these hook limitations.

## Architecture

This plugin uses the shared core library at `hooks/prevent/lib/` (symlinked). All business logic lives in the shared library; the hooks in this plugin are thin adapters (~20 lines each) that translate Codex JSON to/from the platform-agnostic interface.
