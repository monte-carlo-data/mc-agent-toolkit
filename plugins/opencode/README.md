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

- [OpenCode](https://opencode.ai) installed. The plugin loads on both OpenCode 1.x and 2.x from the same files. It is tested on OpenCode 1.19.6 and 2.4.1. OpenCode documents the dual 1.x/2.x entry it uses as working on 1.18.29 and newer; older 1.x releases are untested.
- [Bun](https://bun.sh) installed
- A Monte Carlo account with API access

## Installation

### Quick install (recommended)

From the repo root, run the install script targeting your dbt project:

```bash
./plugins/opencode/install.sh /path/to/your/dbt-project
```

This installs all three components and creates the MCP server config:

- **Plugin** → `.opencode/plugins/mc-agent-toolkit/` (hooks that gate edits)
- **Skill** → `.opencode/skills/prevent/` (workflow instructions for the LLM)
- **Command** → `.opencode/commands/mc-validate.md` (slash command)
- **Config** → `opencode.json` with the plugin registration and the Monte Carlo MCP server

Then authenticate:

```bash
opencode mcp auth monte-carlo-mcp
```

### Manual install

If you prefer to install components individually:

**1. Plugin** (hooks that gate edits and track changes):

```bash
mkdir -p .opencode/plugins/mc-agent-toolkit
cp -r plugins/opencode/{src,package.json,tsconfig.json} .opencode/plugins/mc-agent-toolkit/
cd .opencode/plugins/mc-agent-toolkit && bun install --production
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

**4. Plugin registration and MCP server config** (add to your `opencode.json` at the project root):

```json
{
  "plugin": ["./.opencode/plugins/mc-agent-toolkit"],
  "mcp": {
    "monte-carlo-mcp": {
      "type": "remote",
      "url": "https://mcp.getmontecarlo.com/mcp/toolkit"
    }
  }
}
```

See [OpenCode 1.x and 2.x config](#opencode-1x-and-2x-config) for what the `plugin` entry does on each version.

**5. Authenticate:**

```bash
opencode mcp auth monte-carlo-mcp
```

### OpenCode 1.x and 2.x config

- OpenCode 1.x loads the plugin only from the `plugin` entry. It doesn't scan `.opencode/plugins/` for folders.
- OpenCode 2.x finds the `.opencode/plugins/mc-agent-toolkit/` folder by itself. It also reads the 1.x `plugin` key (its own key is `plugins`), and an entry that names the same folder loads it once.
- Write the entry with a leading `./`. OpenCode 2.x treats a path without `./` or `../` as a package name: with the entry `".opencode/plugins/mc-agent-toolkit"` that installs before 1.34.0 wrote, it installs a second copy through its package cache, reports it as a duplicate plugin ID, and logs a failed update check. The copy it found in the folder still runs. Change the entry to `"./.opencode/plugins/mc-agent-toolkit"`. OpenCode 1.x accepts both spellings.
- In an `opencode.json` inside `.opencode/`, paths are relative to that folder: use `"./plugins/mc-agent-toolkit"`.
- Install the plugin once, in the project or in your global OpenCode config, not both: OpenCode 2.x reports the second copy as a duplicate plugin ID.
- To check that it loaded on OpenCode 2.x, run `opencode plugin list` and look for `mc-prevent`.

### Updating

Re-run the install script to update all components. It will overwrite existing files and re-install dependencies.

```bash
./plugins/opencode/install.sh /path/to/your/dbt-project
```

## Usage

### Automatic behavior (via hooks)

- **Edit a dbt model** — the plugin blocks the edit and asks you to run an impact assessment first
- **Complete the assessment** — once the edit is going ahead (after the engineer's yes, if the agent asked), the agent writes `MC_IMPACT_CHECK_COMPLETE: <table_name>` in its reply, and the next edit to that model is unblocked
- **Commit dbt changes** — the plugin prompts about validation queries and monitor coverage

### Slash command

Use `/mc-validate` to generate validation queries for all dbt models changed in the current session.

## How it works

One module serves both OpenCode versions: its default export carries `server` for OpenCode 1.x and `setup` for OpenCode 2.x, and each version ignores the other's key. The decisions are shared (`src/prevent/core.ts`); `src/prevent/v1.ts` and `src/prevent/v2.ts` connect them to each version's hooks.

| Hook            | OpenCode 1.x                                             | OpenCode 2.x                                            | Behavior                                                |
| --------------- | -------------------------------------------------------- | ------------------------------------------------------- | ------------------------------------------------------- |
| Pre-edit gate   | `tool.execute.before` (edit/write/apply_patch/multiedit) | `ctx.tool.hook("execute.before")` (edit/write/patch)    | Blocks dbt model edits until impact assessment verified |
| Edit tracker    | `tool.execute.after` (edit/write/apply_patch/multiedit)  | `ctx.tool.hook("execute.after")`, completed calls only  | Silently accumulates edited table names                 |
| Pre-commit gate | `tool.execute.before` (bash with `git commit`)           | `ctx.tool.hook("execute.before")` (shell with `git commit`) | Prompts for validation on staged dbt files          |
| Turn-end prompt | `session.idle` event                                     | `ctx.session.hook("experimental.idle")`                 | Reminds about validation queries and monitor coverage   |
| MCP headers     | `config` hook                                            | `ctx.mcp.transform`                                     | Adds the toolkit telemetry headers                      |

The turn-end reminder behaves differently on the two versions. On OpenCode 1.x it is added to the session without a reply, and the agent sees it on your next message. On OpenCode 2.x it is added just before the session goes idle, so the agent takes one more step and asks you the question, as in Claude Code. OpenCode 2.x's idle hook is marked experimental. The reminder isn't sent to a subagent's session, and it waits while the session's own shell or subagent is still running.

On OpenCode 2.x the completion marker counts only in the agent's own reply text, not in your messages. Markers are also remembered from the event stream, so one written before the session was compacted still counts.

OpenCode 2.x can run plugins under Node instead of Bun. The plugin's sources load under Node (CI runs `bun run test:node`), but only the regular, Bun-based OpenCode 2.x build is tested end to end. Paths are checked on this machine: a session on a remote OpenCode workspace isn't gated.

State is managed via temp files under `$TMPDIR/mc_prevent_*` with a three-state machine:

- `absent` → `injected` (instruction sent, waiting for completion)
- `injected` → `verified` (completion marker found in session messages)

An `apply_patch` call (`patch` on OpenCode 2.x) can touch several files. The pre-edit gate checks every file the patch adds, updates, deletes or moves, including the destination of a `*** Move to:`, so moving a file onto an existing model is gated for that model. Patch paths are resolved against the session directory, as OpenCode does. After the patch runs, the edit tracker counts the files OpenCode 1.x reports it changed; OpenCode 2.x's `patch` reports none, so the tracker reads them from the patch. This holds for every edit tool: a SQL file an edit deleted, moved away or overwrote with plain SQL counts only if it was a dbt model just before the edit ran.

All hooks are wrapped in error handling — failures never block the engineer.

## Differences from Claude Code plugin

| Feature             | Claude Code                          | OpenCode                                 |
| ------------------- | ------------------------------------ | ---------------------------------------- |
| Hook language       | Python                               | TypeScript                               |
| Packaging           | Marketplace plugin                   | `.opencode/plugins/` directory           |
| Pre-edit gate       | `PreToolUse` hook with deny decision | Tool `execute.before` hook with thrown error |
| Transcript scanning | Reads transcript file                | Reads session messages through OpenCode's API |
| Turn-end prompt     | `Stop` hook with block decision      | 1.x: message without a reply; 2.x: message the agent answers |
| Git staged files    | `subprocess.run(["git", ...])`       | `execFile("git", ...)` from `node:child_process` |

## Troubleshooting

See [skills/prevent/references/TROUBLESHOOTING.md](../../../skills/prevent/references/TROUBLESHOOTING.md) for common issues.

### Plugin not loading

1. Ensure `bun install` was run in the plugin directory
2. Check OpenCode logs: `.opencode/logs/`
3. Verify the plugin directory contains `src/index.ts` with a default export

### MCP tools not appearing

1. Run `opencode mcp auth monte-carlo-mcp` to authenticate
2. Check that `opencode.json` has the `mcp.monte-carlo-mcp` configuration
3. Verify connectivity: the `testConnection` tool should succeed

## Telemetry

The toolkit sends an anonymous install beacon — a `Toolkit Installed` event so we can count installations and version adoption. It includes an opaque per-install UUID, a per-session UUID, the toolkit version, and the editor it runs in (`opencode`). No prompts, arguments, skill names, or code are ever sent. It fires once per machine per toolkit version — the first time you start OpenCode after installing, and again after each version change (deduped by a local marker) — and is fail-open and non-blocking, never delaying or interrupting your session.

**Authenticated MCP traffic (v1.13.3+).** The same anonymous `install_id` and the toolkit version also ride as HTTP headers (`x-mcd-toolkit-install-id`, `x-mcd-toolkit-version`) on **authenticated** requests to the Monte Carlo MCP server (injected at config-load by the plugin's `config` hook). This lets the otherwise-anonymous install record be correlated with your account's MCP tool usage server-side — still no prompts, arguments, or code. The opt-out below disables these headers too.

To opt out, set `MC_AGENT_TOOLKIT_TELEMETRY_DISABLED=1` in your shell environment before starting OpenCode. The toolkit will not phone home.

The data is stored in Mixpanel and Datadog and is used only for product-development decisions. The UUIDs are generated locally on first session and stored under `~/.config/opencode/mc-agent-toolkit/`. Deleting that directory resets your install identity to a fresh anonymous one.

## Architecture

See the [plugins README](../README.md) for the overall plugin architecture and editor support comparison.

## Development

From `plugins/opencode/`, the same checks CI runs:

```bash
bun install
bun run typecheck   # fetches TypeScript 5.6.3 with bunx, so user installs don't download it
bun test
```

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for release history.
