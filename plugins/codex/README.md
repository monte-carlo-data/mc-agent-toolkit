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
2. Registers the prevent skill in `<repo>/.agents/skills/prevent/`
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

The **prevent** skill is registered in `.agents/skills/prevent/` during installation. Codex activates it automatically when you work with dbt models or SQL files. You can also invoke it explicitly with `$monte-carlo-prevent`.

## Architecture

This plugin uses the shared core library at `hooks/prevent/lib/` (symlinked). All business logic lives in the shared library; the hooks in this plugin are thin adapters (~20 lines each) that translate Codex JSON to/from the platform-agnostic interface.
