# Plugins

This directory contains the **mc-agent-toolkit** plugin for each supported AI coding agent. Each plugin bundles skills, hooks, MCP server configuration, and agent-specific adapters into a single installable package.

For the user-facing feature list and installation instructions, see the [main README](../README.md).

## Coding Agent Support

| Agent | Status | Skills | MCP | Installation |
|---|---|---|---|---|
| **Claude Code** | Full | All 4 | OAuth | [Setup guide](claude-code/README.md) |
| **Cursor** | Full | All 4 | OAuth | [Setup guide](cursor/README.md) |
| **OpenCode** | Full | All 4 | OAuth | [Setup guide](opencode/README.md) |
| **Copilot CLI** | Preliminary | All 4 | OAuth | [Setup guide](copilot/README.md) |
| **Codex** | Preliminary | All 4 | OAuth | [Setup guide](codex/README.md) |

Currently, only the **Prevent** skill leverages hooks for enforcement. The other skills are instruction-only.

### Prevent Hook Behavior

The Prevent feature uses four hooks and a slash command to enforce the impact-assessment-first workflow:

| Component | What it does |
|---|---|
| **Pre-edit hook** | Blocks edits to dbt models (and macros/snapshots) until a change impact assessment has been presented. |
| **Post-edit hook** | Tracks which models were modified in the session for downstream validation. |
| **Pre-commit hook** | Gates `git commit` when modified models have unresolved monitor coverage gaps. |
| **Turn-end hook** | Fires at the end of each turn to inject validation reminders when models were edited without running validation queries. |
| **`/mc-validate` command** | Explicitly generates validation queries for all dbt models changed in the session. |

**How it works:**

1. **You edit a model** — the pre-edit hook blocks until a change impact assessment runs. The agent surfaces downstream blast radius, active alerts, monitor coverage, and a risk-tiered recommendation.
2. **You confirm and edit** — the post-edit hook records the change. The skill offers to generate monitors for new logic.
3. **You commit** — the pre-commit hook checks for unresolved monitor coverage gaps flagged during the assessment.
4. **You validate** — run `/mc-validate` or ask the agent to generate validation queries. Targeted SQL checks are saved to `validation/<table>_<timestamp>.sql`.

Hook availability and behavior varies by agent — see each agent's README for platform-specific details. The [Hook Format Comparison](#hook-format-comparison) table below shows the technical differences.

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
