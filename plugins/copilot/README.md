# Monte Carlo Agent Toolkit — Copilot CLI Plugin

Integrate Monte Carlo's data observability into GitHub Copilot CLI. Detects and prevents breaking schema changes in dbt projects using Monte Carlo lineage, monitoring, and data observability.

## What it does

When you edit a dbt model in a Copilot CLI session, the plugin:

1. **Blocks the edit** until a change impact assessment is completed via Monte Carlo tools
2. **Tracks edited tables** throughout your session
3. **Generates validation queries** to verify changes behaved as intended
4. **Generates monitors-as-code** (validation, metric, comparison, or custom SQL monitors) for new or changed logic
5. **Prompts for validation before committing** when dbt models have been modified

For detailed workflow descriptions, activation rules, and synthesis guidelines, see the [MC Prevent skill](../../skills/prevent/SKILL.md).

## Prerequisites

- [GitHub Copilot CLI](https://docs.github.com/en/copilot/how-tos/copilot-cli) installed
- Python 3.10+ installed
- A Monte Carlo account with API access

## Installation

Installation has two steps: the **install script** (hooks + the Monte Carlo MCP server) and the **plugin** (skills).

### Step 1: Run the install script

```bash
git clone https://github.com/monte-carlo-data/mc-agent-toolkit.git
./mc-agent-toolkit/plugins/copilot/scripts/install.sh /path/to/your/dbt-project
```

This copies the enforcement hooks to `.github/hooks/` in your project, registers a user-level session-start telemetry hook, and registers the Monte Carlo MCP server in `~/.copilot/mcp-config.json` (via `copilot mcp add`).

### Step 2: Install the plugin (skills)

```bash
copilot plugin install ./mc-agent-toolkit/plugins/copilot
```

Verify:

```bash
copilot plugin list
copilot mcp list   # should list monte-carlo-mcp
```

> **Note:** Hooks live in the project repo (`.github/hooks/`) because Copilot CLI loads hooks from the working directory, not from plugins. The MCP server is registered by the install script via `copilot mcp add` — Copilot CLI has no runtime header mechanism, so the toolkit's telemetry headers are baked in at registration time. The plugin delivers skills.

## How it works

The plugin uses Copilot CLI's hook system to intercept tool calls at key lifecycle points:

| Hook Event | Tool Check | Behavior |
|---|---|---|
| `preToolUse` | `edit`, `create` | Blocks dbt model edits until impact assessment completes |
| `preToolUse` | `bash` (git commit) | Denies commit with validation prompt when dbt models are staged |
| `postToolUse` | `edit`, `create` | Silently tracks which models were modified |
| `agentStop` | — | Updates cache state (output ignored by Copilot CLI) |

## Plugin structure

```
plugins/copilot/
├── plugin.json          # Plugin manifest (skills + hooks; MCP is registered by install.sh)
├── hooks.json           # Hook registration (Copilot CLI format)
├── hooks/
│   └── prevent/         # MC Prevent hook adapters (Python)
├── skills/
│   └── prevent/         # MC Prevent skill definition
```

## Differences from other editor plugins

| Aspect | Copilot CLI | Claude Code | Cursor |
|---|---|---|---|
| Hook event names | `preToolUse`, `postToolUse`, `agentStop` | `PreToolUse`, `PostToolUse`, `Stop` | `preToolUse`, `afterFileEdit`, `stop` |
| Hook command field | `"bash": "..."` | `"command": "..."` | `"command": "..."` |
| Hook config | `"version": 1` required | No version field | No version field |
| Tool names | `edit`, `create`, `bash`, `view` | `Write`, `Edit`, `Bash` | `Write`, `Edit` |
| Input format | `toolName` + `toolArgs` (JSON string) | `tool_input` (object) | `tool_input` (object) |
| Deny output | `{"permissionDecision": "deny", ...}` | `{"hookSpecificOutput": {...}}` | `{"permission": "deny", ...}` |
| Context inject | Not supported (deny with reason instead) | `additionalContext` field | `agent_message` field |
| Turn-end output | Ignored (`agentStop`) | Blocks with message | `followup_message` |
| Session ID | Not provided (use PID) | `session_id` | `conversation_id` |

## Known Limitations

- **No session ID**: Copilot CLI doesn't provide a session identifier. The plugin uses the process PID as a fallback, which means cache isolation between concurrent sessions is approximate.
- **No transcript scanning**: Copilot CLI doesn't provide a transcript path. Impact assessment marker detection (`MC_IMPACT_CHECK_COMPLETE`) relies on cache state only.
- **agentStop output ignored**: The turn-end hook cannot inject messages or block completion — it can only perform side effects (cache updates).
- **No additionalContext**: Pre-commit validation uses `deny` with the context message as the reason, rather than injecting advisory context.

## Troubleshooting

**Plugin not loading:**
- Run `copilot plugin install ./plugins/copilot` again
- Check `copilot plugin list` for the plugin name

**Hooks not firing:**
- Verify Python 3 is available: `python3 --version`
- Check hook scripts are executable: `chmod +x plugins/copilot/hooks/prevent/*.py`

**MCP tools not appearing:**
- Run `copilot mcp list` — `monte-carlo-mcp` should be listed; if not, re-run the install script (`scripts/install.sh`)
- Run `/skills list` to verify the prevent skill is loaded

## Telemetry

The toolkit sends an anonymous install beacon — a `Toolkit Installed` event so we can count installations and version adoption. It includes an opaque per-install UUID, a per-session UUID, the toolkit version, and the editor it runs in (`copilot`). No prompts, arguments, skill names, or code are ever sent. It fires once per machine per toolkit version — the first time you start Copilot CLI after installing, and again after each version change (deduped by a local marker) — and is fail-open and non-blocking, never delaying or interrupting your session. The session-start hook is registered at the user level (`~/.copilot/hooks/`) so the install is counted once per machine, not once per repo.

**Authenticated MCP traffic (v1.13.3+).** The same anonymous `install_id` and the toolkit version also ride as HTTP headers (`x-mcd-toolkit-install-id`, `x-mcd-toolkit-version`) on **authenticated** requests to the Monte Carlo MCP server (registered into `~/.copilot/mcp-config.json` via `copilot mcp add` at install time). This lets the otherwise-anonymous install record be correlated with your account's MCP tool usage server-side — still no prompts, arguments, or code. The opt-out below disables these headers too.

To opt out, set `MC_AGENT_TOOLKIT_TELEMETRY_DISABLED=1` in your shell environment before starting Copilot CLI. The toolkit will not phone home.

The data is stored in Mixpanel and Datadog and is used only for product-development decisions. The UUIDs are generated locally on first session and stored under `~/.copilot/mc-agent-toolkit/`. Deleting that directory resets your install identity to a fresh anonymous one.

## Architecture

See the [plugins README](../README.md) for the overall plugin architecture and editor support comparison.
