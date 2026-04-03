# Monte Carlo Agent Toolkit — VS Code Plugin

Integrate Monte Carlo's data observability into VS Code with GitHub Copilot. Detects and prevents breaking schema changes in dbt projects using Monte Carlo lineage, monitoring, and data observability.

## What it does

When you edit a dbt model in Copilot Agent Mode, the plugin:

1. **Blocks the edit** until a change impact assessment is completed via Monte Carlo tools
2. **Tracks edited tables** throughout your session
3. **Generates validation queries** to verify changes behaved as intended
4. **Generates monitors-as-code** (validation, metric, comparison, or custom SQL monitors) for new or changed logic
5. **Prompts for validation and monitor coverage** before committing changes

For detailed workflow descriptions, activation rules, and synthesis guidelines, see the [MC Prevent skill](../../skills/prevent/SKILL.md).

## Prerequisites

- [VS Code](https://code.visualstudio.com/) with the [GitHub Copilot](https://marketplace.visualstudio.com/items?itemName=GitHub.copilot) extension
- Python 3 installed
- A Monte Carlo account with API access

## Installation

### Quick install (recommended)

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/monte-carlo-data/mcd-agent-toolkit/main/plugins/vscode/scripts/install.sh)
```

### From a local clone

```bash
git clone https://github.com/monte-carlo-data/mcd-agent-toolkit.git
cd mcd-agent-toolkit
./plugins/vscode/scripts/install.sh /path/to/your/dbt-project
```

### What gets installed

The install script copies the following into your project:

| Destination | Contents |
|---|---|
| `.github/hooks/hooks.json` | Hook registration for Copilot |
| `.github/hooks/prevent/` | MC Prevent hook adapters (Python) |
| `.github/hooks/lib/` | Shared hook logic (protocol, cache, detection) |
| `.github/skills/prevent/` | MC Prevent skill definition |
| `.github/commands/mc-validate.md` | Validation query slash command |
| `.vscode/mcp.json` | Monte Carlo MCP server configuration |

### Post-install

1. Open the project in VS Code
2. Start a Copilot Agent Mode session (`Ctrl+Shift+I` / `Cmd+Shift+I`)
3. The Monte Carlo MCP server will prompt for OAuth authentication on first use

## How it works

The plugin uses VS Code Copilot's hook system to intercept tool calls at key lifecycle points:

| Hook Event | Matcher | Behavior |
|---|---|---|
| `PreToolUse` | `editFiles`, `createFile` | Blocks dbt model edits until impact assessment completes |
| `PreToolUse` | `runTerminalCommand` | Prompts for validation queries before `git commit` |
| `PostToolUse` | `editFiles`, `createFile` | Silently tracks which models were modified |
| `Stop` | — | Prompts for validation and monitor coverage at turn end |

## Differences from other editor plugins

| Aspect | VS Code | Claude Code | Cursor |
|---|---|---|---|
| Hook language | Python | Python | Python |
| Hook config | `.github/hooks/hooks.json` | `hooks/hooks.json` in plugin | `hooks/hooks.json` in plugin |
| Output format | `hookSpecificOutput` (same as Claude Code) | `hookSpecificOutput` | Cursor-specific (`permission`/`agent_message`) |
| Input field names | camelCase (`sessionId`, `filePath`) | snake_case (`session_id`, `file_path`) | mixed (`conversation_id`, `file_path`) |
| Tool names | `editFiles`, `createFile`, `runTerminalCommand` | `Write`, `Edit`, `Bash` | `Write`, `Edit` |
| Installation | Project-level (`.github/hooks/`) | Marketplace plugin cache | `~/.cursor/plugins/local/` |

## Known Issues

- **Hooks are in VS Code Preview.** The hook configuration format and behavior may change in future VS Code releases.
- **Matchers may be ignored.** VS Code currently parses but does not enforce matchers — all hooks for a given event type run regardless of matcher. The hook scripts check the tool name internally as a safeguard.

## Troubleshooting

**Hooks not firing:**
- Ensure you have the latest GitHub Copilot extension
- Check that `.github/hooks/hooks.json` exists in your project root
- Verify Python 3 is available: `python3 --version`

**MCP tools not appearing:**
- Check `.vscode/mcp.json` exists with the `monte-carlo` server entry
- Run the MCP auth flow: open Copilot and try calling a Monte Carlo tool

**Permission errors on hook scripts:**
- Run `chmod +x .github/hooks/prevent/*.py`
