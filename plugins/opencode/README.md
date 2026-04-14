# Monte Carlo Prevent — OpenCode Plugin

Detect and prevent breaking schema changes in dbt projects using Monte Carlo lineage, monitoring, and data observability.

## What it does

When you edit a dbt model, the plugin:

1. **Blocks the edit** until a change impact assessment is completed via Monte Carlo tools
2. **Tracks edited tables** throughout your session
3. **Generates validation queries** to verify changes behaved as intended
4. **Generates monitors-as-code** (validation, metric, comparison, or custom SQL monitors) for new or changed logic
5. **Prompts for validation and monitor coverage** before committing changes

For detailed workflow descriptions, activation rules, and synthesis guidelines, see the [MC Prevent skill](../../../skills/prevent/SKILL.md).

## Prerequisites

- [OpenCode](https://opencode.ai) installed
- [Bun](https://bun.sh) installed
- A Monte Carlo account with API access

## Installation

### Quick install (recommended)

From the repo root, run the install script targeting your dbt project:

```bash
./plugins/opencode/install.sh /path/to/your/dbt-project
```

This installs all three components and creates the MCP server config:

- **Plugin** → `.opencode/plugins/mc-prevent/` (hooks that gate edits)
- **Skill** → `.opencode/skills/prevent/` (workflow instructions for the LLM)
- **Command** → `.opencode/commands/mc-validate.md` (slash command)
- **Config** → `opencode.json` with Monte Carlo MCP server

Then authenticate:

```bash
opencode mcp auth monte-carlo
```

### Manual install

If you prefer to install components individually:

**1. Plugin** (hooks that gate edits and track changes):

```bash
mkdir -p .opencode/plugins/mc-prevent
cp -r plugins/opencode/{src,package.json,tsconfig.json} .opencode/plugins/mc-prevent/
cd .opencode/plugins/mc-prevent && bun install
```

**2. Skill** (workflow instructions — required for impact assessments):

```bash
mkdir -p .opencode/skills
cp -r skills/prevent .opencode/skills/prevent
```

**3. Command** (slash command for validation queries):

```bash
mkdir -p .opencode/commands
cp plugins/opencode/commands/mc-validate.md .opencode/commands/
```

**4. MCP server config** (add to your `opencode.json`):

```json
{
  "mcp": {
    "monte-carlo-mcp": {
      "type": "remote",
      "url": "https://mcp.getmontecarlo.com/mcp"
    }
  }
}
```

**5. Authenticate:**

```bash
opencode mcp auth monte-carlo-mcp
```

### Updating

Re-run the install script to update all components. It will overwrite existing files and re-install dependencies.

```bash
./plugins/opencode/install.sh /path/to/your/dbt-project
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

| Hook            | Event                                                    | Behavior                                                |
| --------------- | -------------------------------------------------------- | ------------------------------------------------------- |
| Pre-edit gate   | `tool.execute.before` (edit/write/apply_patch/multiedit) | Blocks dbt model edits until impact assessment verified |
| Edit tracker    | `tool.execute.after` (edit/write/apply_patch/multiedit)  | Silently accumulates edited table names                 |
| Pre-commit gate | `tool.execute.before` (bash with `git commit`)           | Prompts for validation on staged dbt files              |
| Turn-end prompt | `session.idle` event                                     | Reminds about validation queries and monitor coverage   |

State is managed via temp files under `$TMPDIR/mc_prevent_*` with a three-state machine:

- `absent` → `injected` (instruction sent, waiting for completion)
- `injected` → `verified` (completion marker found in session messages)

All hooks are wrapped in error handling — failures never block the engineer.

## Differences from Claude Code plugin

| Feature             | Claude Code                          | OpenCode                                 |
| ------------------- | ------------------------------------ | ---------------------------------------- |
| Hook language       | Python                               | TypeScript                               |
| Packaging           | Marketplace plugin                   | `.opencode/plugins/` directory           |
| Pre-edit gate       | `PreToolUse` hook with deny decision | `tool.execute.before` with thrown error  |
| Transcript scanning | Reads transcript file                | Uses SDK client to read session messages |
| Turn-end prompt     | `Stop` hook with block decision      | `session.idle` event with SDK message    |
| Git staged files    | `subprocess.run(["git", ...])`       | `Bun.spawn(["git", ...])`                |

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

## Architecture

See the [plugins README](../README.md) for the overall plugin architecture and editor support comparison.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for release history.
