# Plugins

This directory contains the **mc-agent-toolkit** plugin for each supported AI code editor. Each editor plugin bundles skills, hooks, MCP server configuration, and editor-specific adapters into a single installable package.

For the user-facing feature list and installation instructions, see the [main README](../README.md).

## Editor Support

| Editor | Status | Hooks | Skills | MCP | Details |
|---|---|---|---|---|---|
| **Claude Code** | Full | Pre-edit gate, post-edit tracking, pre-commit gate, turn-end prompt | All 3 skills | OAuth | [README](claude-code/README.md) |
| **Cursor** | Full | Pre-edit gate, post-edit tracking, pre-commit gate, turn-end prompt | MC Prevent | OAuth | [README](cursor/README.md) |
| **OpenCode** | Full | Pre-edit gate, post-edit tracking, pre-commit gate, turn-end prompt | MC Prevent | Remote | [README](opencode/README.md) |
| **Copilot CLI** | Preliminary | Pre-edit gate, post-edit tracking, pre-commit gate (hooks installed separately) | MC Prevent | HTTP | [README](copilot/README.md) |
| **Codex** | Preliminary | None (instruction-only) | MC Prevent | N/A | [README](codex/README.md) |

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
