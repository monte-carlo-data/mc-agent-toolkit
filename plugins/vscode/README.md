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

### From Git URL

1. Open VS Code
2. Run **Chat: Install Plugin From Source** from the Command Palette (`Ctrl+Shift+P` / `Cmd+Shift+P`)
3. Paste the repository URL: `https://github.com/monte-carlo-data/mcd-agent-toolkit`

### From a local clone

1. Clone the repo:
   ```bash
   git clone https://github.com/monte-carlo-data/mcd-agent-toolkit.git
   ```
2. In VS Code, add the plugin path to your settings:
   ```json
   "chat.pluginLocations": {
       "/path/to/mcd-agent-toolkit/plugins/vscode": true
   }
   ```

### Post-install

1. Start a Copilot Agent Mode session (`Ctrl+Shift+I` / `Cmd+Shift+I`)
2. The Monte Carlo MCP server will prompt for authentication on first use
3. The MC Prevent skill appears in the **Configure Skills** menu

## How it works

The plugin uses VS Code Copilot's hook system to intercept tool calls at key lifecycle points:

| Hook Event | Matcher | Behavior |
|---|---|---|
| `PreToolUse` | `editFiles`, `createFile` | Blocks dbt model edits until impact assessment completes |
| `PreToolUse` | `runTerminalCommand` | Prompts for validation queries before `git commit` |
| `PostToolUse` | `editFiles`, `createFile` | Silently tracks which models were modified |
| `Stop` | — | Prompts for validation and monitor coverage at turn end |

## Plugin structure

```
plugins/vscode/
├── plugin.json          # Plugin manifest
├── hooks.json           # Hook registration (Copilot format)
├── .mcp.json            # Monte Carlo MCP server config
├── hooks/
│   └── prevent/         # MC Prevent hook adapters (Python)
├── skills/
│   └── prevent/         # MC Prevent skill definition
```

## Differences from other editor plugins

| Aspect | VS Code | Claude Code | Cursor |
|---|---|---|---|
| Plugin format | Copilot agent plugin | Claude Code marketplace | Cursor plugin |
| Hook config | `hooks.json` at plugin root | `hooks/hooks.json` | `hooks/hooks.json` |
| Hook language | Python | Python | Python |
| Output format | `hookSpecificOutput` (same as Claude Code) | `hookSpecificOutput` | Cursor-specific |
| Input field names | camelCase (`sessionId`, `filePath`) | snake_case (`session_id`, `file_path`) | mixed |
| Tool names | `editFiles`, `createFile`, `runTerminalCommand` | `Write`, `Edit`, `Bash` | `Write`, `Edit` |
| MCP config | `.mcp.json` in plugin | `.mcp.json` in plugin | `mcp.json` in plugin |
| Installation | Git URL or marketplace | Marketplace | Install script |

## Known Issues

- **Hooks are in VS Code Preview.** The hook configuration format and behavior may change in future VS Code releases.
- **Matchers may be ignored.** VS Code currently parses but does not enforce matchers — all hooks for a given event type run regardless of matcher. The hook scripts check the tool name internally as a safeguard.
- **Plugin system is in Preview.** Agent plugins require `chat.plugins.enabled` to be true.

## Troubleshooting

**Plugin not appearing:**
- Ensure `chat.plugins.enabled` is true in VS Code settings
- Check that the plugin path is correct in `chat.pluginLocations`

**Hooks not firing:**
- Ensure you have the latest GitHub Copilot extension
- Verify Python 3 is available: `python3 --version`

**MCP tools not appearing:**
- Check that `.mcp.json` exists in the plugin directory
- The MCP server should auto-start when the plugin is enabled

**Permission errors on hook scripts:**
- Run `chmod +x plugins/vscode/hooks/prevent/*.py`
