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
- Python 3 installed
- A Monte Carlo account with API access

## Installation

Installation has two steps: the **plugin** (for skills + MCP) and the **hooks** (for enforcement).

### Step 1: Install hooks into your project

```bash
git clone https://github.com/monte-carlo-data/mcd-agent-toolkit.git
./mcd-agent-toolkit/plugins/copilot/scripts/install.sh /path/to/your/dbt-project
```

This copies hook scripts and registration to `.github/hooks/` in your project.

### Step 2: Install the plugin (skills + MCP)

```bash
copilot plugin install ./mcd-agent-toolkit/plugins/copilot
```

Verify:

```bash
copilot plugin list
```

> **Note:** Hooks live in the project repo (`.github/hooks/`) because Copilot CLI loads hooks from the working directory, not from plugins. The plugin delivers skills and MCP server configuration.

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
├── plugin.json          # Plugin manifest
├── hooks.json           # Hook registration (Copilot CLI format)
├── .mcp.json            # Monte Carlo MCP server config
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
- Check that `.mcp.json` exists in the plugin directory
- Run `/skills list` to verify the prevent skill is loaded
