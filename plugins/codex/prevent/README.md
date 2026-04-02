# Monte Carlo Prevent — Codex Plugin

Detects and prevents breaking schema changes to dbt models using Monte Carlo lineage and monitoring data.

## Installation

This plugin is available via the Codex marketplace. Add it to your repo by including `.agents/plugins/marketplace.json` at the repo root (already present in this repo).

### MCP Server

The plugin bundles MCP configuration in `.mcp.json`. If Codex doesn't auto-discover it, register manually:

```bash
codex mcp add monte-carlo --url https://integrations.getmontecarlo.com/mcp
```

### Hooks

Ensure hooks are enabled in your Codex config:

```toml
# ~/.codex/config.toml
[features]
codex_hooks = true
```

## How It Works

The plugin uses four hooks to enforce the Monte Carlo Prevent workflow:

| Hook | Event | Matcher | Purpose |
|------|-------|---------|---------|
| pre_edit | PreToolUse | Edit\|Write | Gate dbt model edits until impact assessment completes |
| post_edit | PostToolUse | Edit\|Write | Silently track which tables were edited |
| pre_commit | PreToolUse | Bash | Prompt for validation before git commit |
| turn_end | Stop | — | Suggest validation queries for pending tables |

**Note:** Edit|Write matchers are wired for forward compatibility. Codex currently only emits PreToolUse/PostToolUse for the Bash tool. Pre-commit and turn-end hooks work today.

## Commands

- `/mc-validate` — Generate validation queries for all dbt models changed in this session

## Architecture

This plugin uses the shared core library at `hooks/prevent/lib/` (symlinked). All business logic lives in the shared library; the hooks in this plugin are thin adapters (~20 lines each) that translate Codex JSON to/from the platform-agnostic interface.
