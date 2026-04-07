# Plugins

This directory contains the **mc-agent-toolkit** plugin for each supported AI coding agent. Each plugin bundles skills, hooks, MCP server configuration, and agent-specific adapters into a single installable package.

For the user-facing feature list and installation instructions, see the [main README](../README.md).

## Coding Agent Support

| Agent | Status | Skills | MCP |
|---|---|---|---|
| **[Claude Code](claude-code/README.md)** | Full | All 3 | OAuth |
| **[Cursor](cursor/README.md)** | Full | All 3 | OAuth |
| **[OpenCode](opencode/README.md)** | Full | All 3 | OAuth |
| **[Copilot CLI](copilot/README.md)** | Preliminary | All 3 | OAuth |
| **[Codex](codex/README.md)** | Preliminary | All 3 | OAuth |

Currently, only the **Prevent** skill leverages hooks for enforcement (pre-edit gate, post-edit tracking, pre-commit gate, turn-end prompt). The other skills are instruction-only. See each agent's README for hook details specific to that platform.

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
