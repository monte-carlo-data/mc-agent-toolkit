# Monte Carlo Prevent Plugin

Claude Code plugin that brings Monte Carlo data observability into your editor. Automatically gates dbt model edits with impact assessments, surfaces table health and lineage context, generates monitors-as-code, and produces targeted validation queries — all before you merge.

## What the plugin adds

The plugin wraps the [Prevent skill](../../../skills/prevent/) with hooks, commands, and permissions that enforce safety checks automatically:

| Component | What it does |
|---|---|
| **Pre-edit hook** | Blocks edits to dbt models (and macros/snapshots) until a change impact assessment has been presented. Checks transcript markers to verify the assessment completed. |
| **Post-edit hook** | Tracks which models were modified in the session for downstream validation. |
| **Pre-commit hook** | Gates `git commit` when modified models have unresolved monitor coverage gaps. |
| **Turn-end hook** | Fires at the end of each turn to inject validation reminders when models were edited without running validation queries. |
| **`/mc-validate` command** | Explicitly generates validation queries for all dbt models changed in the session. |
| **MCP permissions** | Auto-approves Monte Carlo MCP tool calls so you don't get prompted on every API request. |
| **Install/uninstall scripts** | Cleans up standalone skill copies and legacy `safe-change` files on install; restores standalone skill on uninstall. |

## Installation

### Via Marketplace (recommended)

```
/plugin marketplace add monte-carlo-data/mcd-agent-toolkit
/plugin install mc-prevent@mcd-agent-toolkit
```

### Manual

```bash
git clone https://github.com/monte-carlo-data/mcd-agent-toolkit.git
cd mcd-agent-toolkit
claude plugin install plugins/claude-code/prevent
```

Restart Claude Code after installing.

## Setup

1. **Authenticate with Monte Carlo** — run `/mcp` in Claude Code, select the Monte Carlo server, and complete the OAuth flow.
2. **Verify** — ask Claude: "Test my Monte Carlo connection."

See the [skill README](skills/prevent/README.md) for full setup details including standalone MCP server configuration and legacy auth options.

## How it works

Open your dbt project and start working. The plugin activates automatically:

1. **You edit a model** — the pre-edit hook fires and blocks until a change impact assessment runs (Workflow 4 from the skill). Claude surfaces downstream blast radius, active alerts, monitor coverage, and a risk-tiered recommendation.
2. **You confirm and edit** — the post-edit hook records the change. The skill offers to generate monitors for new logic (Workflow 2).
3. **You commit** — the pre-commit hook checks for unresolved monitor coverage gaps flagged during the assessment.
4. **You validate** — run `/mc-validate` or ask Claude to generate validation queries. Targeted SQL checks are saved to `validation/<table>_<timestamp>.sql`.

## Directory structure

```
prevent/
  CHANGELOG.md          # Release history
  settings.json         # Plugin permissions (MCP tool auto-approve)
  commands/
    mc-validate.md      # /mc-validate slash command definition
  hooks/
    hooks.json          # Hook registration (pre-edit, post-edit, pre-commit, turn-end)
    pre_edit_hook.py    # Impact assessment gate
    post_edit_hook.py   # Edit tracking
    pre_commit_hook.py  # Monitor gap gate
    turn_end_hook.py    # Validation reminder
    validate_command.py # /mc-validate handler
    lib/                # Shared utilities (cache, detection, fail-open)
  scripts/
    install.sh          # Post-install cleanup
    uninstall.sh        # Post-uninstall restore
  skills/
    prevent/            # Bundled skill (SKILL.md, README.md, references/)
  tests/                # Hook and lib unit tests
```

## Updating

```
claude plugin update mc-prevent@mcd-agent-toolkit
```

## Uninstalling

```
claude plugin remove mc-prevent
```

The uninstall script restores a standalone skill backup if one exists.

## Changelog

See [CHANGELOG.md](CHANGELOG.md).
