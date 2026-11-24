# Plugins

This directory contains the **mc-agent-toolkit** plugin for each supported AI coding agent. Each plugin bundles skills, hooks, MCP server configuration, and agent-specific adapters into a single installable package.

For the user-facing feature list and installation instructions, see the [main README](../README.md).

## Coding Agent Support

| Agent | Status | Skills | MCP | Installation |
|---|---|---|---|---|
| **Claude Code** | Full | All 21 | OAuth | [Setup guide](claude-code/README.md) |
| **Cursor** | Full | All 21 | OAuth | [Setup guide](cursor/README.md) |
| **OpenCode** | Full | All 21 | OAuth | [Setup guide](opencode/README.md) |
| **Cortex Code** | Full | All 21 | OAuth | [Setup guide](cortex-code/README.md) |
| **Copilot CLI** | Preliminary | All 21 | OAuth | [Setup guide](copilot/README.md) |
| **Codex** | Preliminary | All 21 | OAuth | [Setup guide](codex/README.md) |

Currently, only the **Prevent** skill leverages hooks for *enforcement*; the other skills are instruction-only. (Telemetry also uses a lightweight `SessionStart` hook to fire an anonymous install beacon — see each plugin's README and the Telemetry section in the root README.)

### Prevent Hook Behavior

The Prevent feature uses five hooks and a slash command to enforce the impact-assessment-first workflow:

| Component | What it does |
|---|---|
| **Pre-edit hook** | Blocks edits to dbt models (and macros/snapshots) until a change impact assessment has been presented. |
| **Post-edit hook** | Tracks which models were modified in the session for downstream validation. |
| **Pre-commit hook** | Before `git commit`, when assessed models are staged, asks whether to run validation queries, and whether to generate monitors for coverage gaps the assessment found. |
| **Post-commit hook** | After a commit that changes a dbt model, asks the agent to offer a Bayes follow-up on those tables (Claude Code and Cursor). Nothing is scheduled unless the user says yes. Turn off with `MC_BAYES_FOLLOWUP_DISABLED=1`. |
| **Turn-end hook** | Fires at the end of each turn to inject validation reminders when models were edited without running validation queries. |
| **`/mc-validate` command** | Explicitly generates validation queries for all dbt models changed in the session. |

**How it works:**

1. **You edit a model** — the pre-edit hook blocks until a change impact assessment runs. The agent surfaces downstream blast radius, active alerts, monitor coverage, and a risk-tiered recommendation.
2. **You confirm and edit** — the post-edit hook records the change. The skill offers to generate monitors for new logic.
3. **You commit** — when assessed models are staged, the pre-commit hook asks whether to run validation queries first, and whether to generate monitors for any coverage gap the assessment found. In Cortex Code it pauses the commit once to ask. In Claude Code and Cursor, once a commit that changes a dbt model lands, the agent offers to have Bayes, Monte Carlo's AI teammate, check the changed tables and their downstream tables after the change deploys, when `schedule_agent_task` is available. The answer arrives in Slack, as a direct message or in the domain's Teammate channel, whichever you pick. Each table is offered once per session.
4. **You validate** — run `/mc-validate` or ask the agent to generate validation queries. Targeted SQL checks are saved to `validation/<table>_<timestamp>.sql`.

Hook availability and behavior varies by agent — see each agent's README for platform-specific details. The [Hook Format Comparison](#hook-format-comparison) table below shows the technical differences.

**Editor compatibility:** Most agents run inside popular editors. **VS Code** users can use Copilot CLI or Claude Code. **JetBrains** users can use Copilot CLI. **Cursor** is a standalone editor with its own plugin. Claude Code, Copilot CLI, and OpenCode also run in any **terminal**. Codex runs on **GitHub**. **Cortex Code** is Snowflake's coding agent, available as the `cortex` terminal CLI and the CoCo Desktop app.

## Architecture

Each editor plugin follows the **unified toolkit model** — one plugin per editor named `mc-agent-toolkit`, with skills as features within it.

```
plugins/
├── shared/              # Shared hook logic, synced into each editor plugin
│   ├── prevent/lib/     # Business logic used by all editor adapters (Python)
│   └── telemetry/lib/   # Canonical install-beacon (bash), synced into hooks/telemetry/lib/
├── claude-code/         # Claude Code plugin
├── cursor/              # Cursor plugin
├── opencode/            # OpenCode plugin (TypeScript port)
├── copilot/             # Copilot CLI plugin
├── codex/               # Codex plugin
└── cortex-code/         # Cortex Code plugin (wraps Claude Code)
```

**Key patterns:**
- **Shared hook logic** lives in `shared/<skill>/lib/`. Editor plugins copy it (kept in sync via `scripts/bump-version.sh --sync-only`; symlinks under `hooks/` are rejected by CI) and provide thin adapter scripts that translate editor-specific JSON formats.
- **Skills** are symlinked from `../skills/` — authored once, shared across all editors.
- **OpenCode** is an exception — it ports the shared logic to TypeScript since the `@opencode-ai/plugin` SDK requires it.

For detailed architecture decisions, see the [Plugin Architecture Guide](../docs/plugin-architecture-guide.md). For contribution guidelines, see [CONTRIBUTING.md](../CONTRIBUTING.md).

## Hook Format Comparison

| Aspect | Claude Code | Cursor | OpenCode | Copilot CLI | Codex | Cortex Code |
|---|---|---|---|---|---|---|
| Language | Python | Python | TypeScript | Python | Python | Python |
| Hook config | `hooks/<skill>/hooks.json` | `hooks/<skill>/hooks.json` | Event handlers in `src/` | `hooks.json` (v1 format) at plugin root | `hooks/prevent/hooks.json` (manifest `hooks`), or `.codex/hooks.json` from `install.sh` | One `hooks/hooks.json` for all skills |
| Command field | `"command"` | `"command"` | SDK events | `"bash"` | `"command"` | `"command"` |
| Tool names | `Write`, `Edit`, `Bash` | `Write`, `Edit`, `Shell` | `edit`, `write`, `apply_patch` | `edit`, `create`, `bash` | `Bash`, `apply_patch` (Codex 0.124.0+) | `edit`, `write`, `multi_edit`, `apply_patch`, `bash`, `skill` (regex matchers; CoCo Desktop matches case-sensitively) |
| Deny format | `hookSpecificOutput.permissionDecision` | `permission: "deny"` | Thrown `Error` | `permissionDecision: "deny"` | `hookSpecificOutput.permissionDecision` | `hookSpecificOutput.permissionDecision` |
| Session ID | `session_id` | `conversation_id` | SDK client | PID (not provided) | `session_id` | `session_id` |

**Codex** edits files with `apply_patch`, either its own tool (`tool_name` `apply_patch`, the patch in `tool_input.command`; Codex 0.124.0+) or a shell command such as `cd <dir> && apply_patch <<'EOF'` (`tool_name` `Bash`). The Bash hook finds the patch in the command and the directory it runs in; the plugin has no edit or write hooks. Codex sends PostToolUse for its own `apply_patch` only after a successful patch, and not for a patch run from the shell, so the Bash hook tracks a shell patch itself once it is allowed. See the [Codex README](codex/README.md).

**Cortex Code** wraps Claude Code, so its hook I/O JSON matches Claude Code, and `${CORTEX_PLUGIN_ROOT}` is substituted into hook commands (the analog of Claude Code's `${CLAUDE_PLUGIN_ROOT}`). It is substituted into the command text, not exported, so quote it. One difference in hook output: neither CoCo Desktop nor the CLI passes a PreToolUse hook's `additionalContext` to the model, so the pre-commit checkpoint denies the commit once, with the questions as the reason, instead of adding context. Four differences in hook config: the plugin keeps every hook in `hooks/hooks.json` at the plugin root and declares no `hooks` in the manifest, because CoCo Desktop 2.0.0 loaded that file and ignored the manifest's list of hook files; matchers are unanchored regexes tested case-sensitively against lowercase tool IDs (Snowflake documents this for the CLI, and Desktop 2.0.0 does it; CLI 1.2.46 also fired PascalCase matchers in our probe), so the plugin uses anchored lowercase matchers such as `^bash$` (PascalCase names like `Bash` never matched in Desktop); the hook `transcript_path` points at a `<id>.json` metadata file, while the session messages live in a sibling `<id>.history.jsonl`, so the prevent pre-edit hook reads that sibling and matches markers only in assistant-authored text; and Cortex Code gives GPT and OpenAI models `apply_patch` instead of the edit tools, so the edit hooks parse the patch in `tool_input.input` and check or track every file it touches.
