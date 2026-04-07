# Plugins

This directory contains the **mc-agent-toolkit** plugin for each supported AI coding agent. Each plugin bundles skills, hooks, MCP server configuration, and agent-specific adapters into a single installable package.

For the user-facing feature list and installation instructions, see the [main README](../README.md).

## Coding Agent Support

| Agent | Status | Skills | MCP | Installation |
|---|---|---|---|---|
| **Claude Code** | Full | All 3 | OAuth | [Setup guide](claude-code/README.md) |
| **Cursor** | Full | All 3 | OAuth | [Setup guide](cursor/README.md) |
| **OpenCode** | Full | All 3 | OAuth | [Setup guide](opencode/README.md) |
| **Copilot CLI** | Preliminary | All 3 | OAuth | [Setup guide](copilot/README.md) |
| **Codex** | Preliminary | All 3 | OAuth | [Setup guide](codex/README.md) |

Currently, only the **Prevent** skill leverages hooks for enforcement (pre-edit gate, post-edit tracking, pre-commit gate, turn-end prompt). The other skills are instruction-only. See each agent's README for hook details specific to that platform.

**Editor compatibility:** Most agents run inside popular editors. **VS Code** users can use Copilot CLI or Claude Code. **JetBrains** users can use Copilot CLI. **Cursor** is a standalone editor with its own plugin. Claude Code, Copilot CLI, and OpenCode also run in any **terminal**. Codex runs on **GitHub**.

## Architecture

Each editor plugin follows the **unified toolkit model** — one plugin per editor named `mc-agent-toolkit`, with skills as features within it.

```
plugins/
├── shared/              # Platform-agnostic hook logic (Python)
│   └── prevent/lib/     # Business logic used by all editor adapters
├── claude-code/         # Claude Code plugin
├── cursor/              # Cursor plugin
├── opencode/            # OpenCode plugin (TypeScript port)
├── copilot/             # Copilot CLI plugin
└── codex/               # Codex plugin (skills only)
```

**Key patterns:**
- **Shared hook logic** lives in `shared/<skill>/lib/`. Editor plugins symlink to it and provide thin adapter scripts that translate editor-specific JSON formats.
- **Skills** are symlinked from `../skills/` — authored once, shared across all editors.
- **OpenCode** is an exception — it ports the shared logic to TypeScript since the `@opencode-ai/plugin` SDK requires it.

For detailed architecture decisions, see the [Plugin Architecture Guide](../docs/plugin-architecture-guide.md). For contribution guidelines, see [CONTRIBUTING.md](../CONTRIBUTING.md).

## Hook Format Comparison

| Aspect | Claude Code | Cursor | OpenCode | Copilot CLI |
|---|---|---|---|---|
| Language | Python | Python | TypeScript | Python |
| Hook config | `hooks/<skill>/hooks.json` | `hooks/<skill>/hooks.json` | Event handlers in `src/` | `hooks.json` (v1 format) at plugin root |
| Command field | `"command"` | `"command"` | SDK events | `"bash"` |
| Tool names | `Write`, `Edit`, `Bash` | `Write`, `Edit` | `edit`, `write`, `apply_patch` | `edit`, `create`, `bash` |
| Deny format | `hookSpecificOutput.permissionDecision` | `permission: "deny"` | Thrown `Error` | `permissionDecision: "deny"` |
| Session ID | `session_id` | `conversation_id` | SDK client | PID (not provided) |
