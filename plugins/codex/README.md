# Monte Carlo Agent Toolkit — Codex Plugin

Data observability skills and enforcement hooks for AI coding agents, powered by Monte Carlo.

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
2. Creates `.agents/plugins/marketplace.json` for Codex plugin discovery
3. Adds the Monte Carlo MCP server to `~/.codex/config.toml` with the required `User-Agent` header (workaround for [codex#12859](https://github.com/openai/codex/issues/12859))
4. Enables `codex_hooks` in your config
5. Opens a browser for OAuth login with your Monte Carlo account

After installation, restart Codex in your project. You should see "Installed mc-agent-toolkit plugin" on startup.

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
