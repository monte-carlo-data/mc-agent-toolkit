# Monte Carlo Prevent — OpenCode Plugin

Detect and prevent breaking schema changes in dbt projects using Monte Carlo lineage, monitoring, and data observability.

## What it does

When you edit a dbt model, the plugin:

1. **Blocks the edit** until a change impact assessment (Workflow 4) is completed via Monte Carlo tools
2. **Tracks edited tables** throughout your session
3. **Prompts for validation queries** before committing changes to dbt models
4. **Reminds about monitor coverage gaps** when custom monitors are missing on changed columns

## Prerequisites

- [OpenCode](https://opencode.ai) installed
- A Monte Carlo account with API access

## Installation

### Option 1: Project plugin (recommended)

Copy the plugin into your project's `.opencode/plugins/` directory:

```bash
mkdir -p .opencode/plugins
cp -r plugins/opencode/prevent .opencode/plugins/mc-prevent
cd .opencode/plugins/mc-prevent && bun install
```

### Option 2: Global plugin

Install globally for all projects:

```bash
mkdir -p ~/.config/opencode/plugins
cp -r plugins/opencode/prevent ~/.config/opencode/plugins/mc-prevent
cd ~/.config/opencode/plugins/mc-prevent && bun install
```

### Configure the MCP server

Merge the MCP server configuration into your project's `opencode.json`:

```json
{
  "mcp": {
    "monte-carlo": {
      "type": "remote",
      "url": "https://integrations.getmontecarlo.com/mcp"
    }
  }
}
```

### Authenticate

Run OpenCode and authenticate with Monte Carlo:

```bash
opencode mcp auth monte-carlo
```

### Install the skill (optional)

OpenCode reads `.claude/skills/` natively. If your project already has the MC Prevent skill installed for Claude Code, it will be picked up automatically.

To install explicitly for OpenCode:

```bash
mkdir -p .opencode/skills
cp -r skills/prevent .opencode/skills/prevent
```

## Usage

### Automatic behavior (via hooks)

- **Edit a dbt model** — the plugin blocks the edit and asks you to run an impact assessment first
- **Complete the assessment** — emit `MC_IMPACT_CHECK_COMPLETE: <table_name>` markers and the edit is unblocked
- **Commit dbt changes** — the plugin prompts about validation queries and monitor coverage

### Slash command

Use `/mc-validate` to generate validation queries for all dbt models changed in the current session.

## How it works

The plugin registers three OpenCode hook events:

| Hook | Event | Behavior |
|---|---|---|
| Pre-edit gate | `tool.execute.before` (edit/write/patch) | Blocks dbt model edits until impact assessment verified |
| Edit tracker | `tool.execute.after` (edit/write/patch) | Silently accumulates edited table names |
| Pre-commit gate | `tool.execute.before` (bash with `git commit`) | Prompts for validation on staged dbt files |
| Turn-end prompt | `session.idle` event | Reminds about validation queries and monitor coverage |

State is managed via temp files under `$TMPDIR/mc_prevent_*` with a three-state machine:
- `absent` → `injected` (instruction sent, waiting for completion)
- `injected` → `verified` (completion marker found in session messages)

All hooks are wrapped in error handling — failures never block the engineer.

## Differences from Claude Code plugin

| Feature | Claude Code | OpenCode |
|---|---|---|
| Hook language | Python | TypeScript |
| Packaging | Marketplace plugin | `.opencode/plugins/` directory |
| Pre-edit gate | `PreToolUse` hook with deny decision | `tool.execute.before` with thrown error |
| Transcript scanning | Reads transcript file | Uses SDK client to read session messages |
| Turn-end prompt | `Stop` hook with block decision | `session.idle` event with SDK message |
| Git staged files | `subprocess.run(["git", ...])` | `Bun.spawn(["git", ...])` |

## Troubleshooting

See [skills/prevent/references/TROUBLESHOOTING.md](../../../skills/prevent/references/TROUBLESHOOTING.md) for common issues.

### Plugin not loading

1. Ensure `bun install` was run in the plugin directory
2. Check OpenCode logs: `.opencode/logs/`
3. Verify the plugin directory contains `src/index.ts` with a default export

### MCP tools not appearing

1. Run `opencode mcp auth monte-carlo` to authenticate
2. Check that `opencode.json` has the `mcp.monte-carlo` configuration
3. Verify connectivity: the `testConnection` tool should succeed
