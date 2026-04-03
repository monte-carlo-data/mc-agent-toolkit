# Plugin Architecture Guide

This document explains how skills and plugins are structured in `mcd-agent-toolkit`, the reasoning behind the architecture, and how to extend it for new skills and editors.

For step-by-step contribution instructions, see [CONTRIBUTING.md](../CONTRIBUTING.md).

## Overview

`mcd-agent-toolkit` distributes Monte Carlo capabilities into AI code editors through two layers:

1. **Skills** — platform-agnostic instruction sets that tell an AI agent what to do (e.g., run impact assessments, generate validation queries). Skills live in `skills/` and are the single source of truth.
2. **Plugins** — editor-specific wrappers that install skills, configure MCP servers, and add hooks/gates that enforce workflows. Plugins live in `plugins/<editor>/`.

Not every skill needs a plugin. A skill without a plugin is just a set of instructions the agent follows. A plugin adds enforcement — blocking edits until assessments run, gating commits until validation is complete, etc.

## Architecture Decision: Unified Toolkit Plugin (Option B)

### The Problem

As more skills are added, a per-skill-per-editor plugin model creates `skills × editors` plugins to maintain. Each plugin independently configures the same MCP server, handles the same auth flow, and duplicates install logic.

### Options Considered

**Option A — Toolkit as invisible plumbing.** A single plugin per editor handles distribution (MCP, auth, updates), but the plugin identity is hidden from users. All user-facing surfaces show individual skill names only (e.g., "MC Prevent").

- *Pro:* Individual skills get standalone brand recognition.
- *Con:* Users see a plugin name (`mcd-agent-toolkit`) in their editor's plugin list that doesn't match what they interact with. No natural place for enable/disable configuration. Hard to make truly invisible across all editors.

**Option B — Unified toolkit with namespaced features (chosen).** One plugin per editor named `mcd-agent-toolkit`. Each skill is a named feature within it. Users understand they installed "Monte Carlo's toolkit" and interact with features like "MC Prevent" inside it.

- *Pro:* Consistent identity across all editors. Natural enable/disable model. New skills appear as new features in a product users already know. MCP and auth configured once. Single install, single update path.
- *Con:* Users get all features, not just the ones they want (mitigated by enable/disable config). A bug in one feature's hooks could theoretically affect the plugin — mitigated by feature isolation (see below).

**Option C — Separate plugins per skill.** Each skill that needs a plugin gets its own. Distribution is handled by install scripts, not by bundling.

- *Pro:* Maximum isolation. Users opt in per skill.
- *Con:* Duplicated MCP/auth config across plugins. `skills × editors` maintenance burden. No shared update mechanism.

### Why Option B

1. **Cross-editor consistency.** Every editor surfaces plugin names — in marketplace listings, extension panels, config files. One name (`mcd-agent-toolkit`) everywhere is clearer than hiding it.
2. **Shared infrastructure.** MCP server configuration, OAuth, and base permissions are identical across skills. Configure once, not per-skill.
3. **Scalable UX.** New skills showing up as features in an existing toolkit is expected. New standalone plugins appearing unexpectedly is confusing.
4. **Enable/disable is natural.** A toolkit has features you can toggle. A hidden plumbing layer doesn't.

### Claude Code Marketplace Exception

Claude Code's marketplace uniquely supports listing multiple plugins from a single repo (e.g., `/plugin install mc-prevent@mcd-agent-toolkit`). The current per-skill marketplace entries will be maintained for now. This decision is being evaluated separately and may align with Option B in the future.

All other editors (VS Code, Cursor, OpenCode, Codex) follow the unified toolkit plugin model.

## How It Works Per Editor

| Editor | Plugin Format | Skill Loading | Hooks | MCP Config |
|--------|--------------|---------------|-------|------------|
| **Claude Code** | `.claude-plugin/plugin.json` + marketplace | `skills/` dir in plugin | `hooks.json` → Python scripts | `.mcp.json` |
| **Cursor** | `.cursor-plugin/plugin.json` | Symlinked from `skills/` | `hooks.json` → Python scripts | `mcp.json` |
| **OpenCode** | `@opencode-ai/plugin` SDK (TypeScript) | Copied to `.opencode/skills/` | Event handlers in `index.ts` | `opencode.json` |
| **VS Code** | VS Code extension (`package.json`) | Bundled in extension | Extension API events | `.vscode/mcp.json` |
| **Codex** | `AGENTS.md` + config files | Copied to project | N/A (instruction-only) | Config file |

## Separation of Concerns

Each skill maintains strict isolation within the toolkit plugin:

### Directory Structure

This is the **target state**. Cursor and OpenCode are being migrated from per-skill directories to this unified model.

```
mcd-agent-toolkit/
├── skills/                              # Shared skill definitions (platform-agnostic)
│   ├── prevent/
│   │   ├── SKILL.md
│   │   └── references/
│   └── <future-skill>/
│       ├── SKILL.md
│       └── references/
│
├── hooks/                               # Shared hook logic (platform-agnostic)
│   ├── prevent/lib/
│   │   ├── protocol.py                  # Business logic (evaluate_pre_edit, etc.)
│   │   ├── cache.py                     # State management (mc_prevent_* prefixed)
│   │   ├── detect.py                    # dbt file detection
│   │   └── safe_run.py                  # Error safety decorator
│   └── <future-skill>/lib/
│       ├── protocol.py                  # Separate business logic
│       └── cache.py                     # Separate cache (mc_<skill>_* prefixed)
│
├── plugins/
│   │
│   │  # --- Claude Code: per-skill plugins (marketplace exception) ---
│   ├── claude-code/
│   │   ├── prevent/                     # mc-prevent plugin
│   │   │   ├── .claude-plugin/plugin.json
│   │   │   ├── hooks/                   # Thin adapters → hooks/prevent/lib/
│   │   │   └── skills/prevent → symlink
│   │   └── <future-skill>/              # Separate plugin per skill
│   │       ├── .claude-plugin/plugin.json
│   │       └── skills/<future-skill> → symlink
│   │
│   │  # --- All other editors: ONE mcd-agent-toolkit plugin each ---
│   ├── cursor/                          # mcd-agent-toolkit plugin for Cursor
│   │   ├── .cursor-plugin/plugin.json
│   │   ├── hooks/
│   │   │   ├── prevent/                 # MC Prevent hook adapters
│   │   │   └── <future-skill>/          # Future feature hook adapters
│   │   ├── skills/
│   │   │   ├── prevent → symlink
│   │   │   └── <future-skill> → symlink
│   │   └── mcp.json
│   │
│   ├── opencode/                        # mcd-agent-toolkit plugin for OpenCode
│   │   ├── src/
│   │   │   ├── prevent/                 # MC Prevent feature module
│   │   │   └── <future-skill>/          # Future feature module
│   │   ├── package.json
│   │   └── opencode.json
│   │
│   ├── vscode/                          # mcd-agent-toolkit plugin for VS Code
│   │   ├── hooks/
│   │   │   ├── prevent/                 # MC Prevent hook adapters
│   │   │   └── <future-skill>/          # Future feature hook adapters
│   │   ├── skills/
│   │   │   ├── prevent → symlink
│   │   │   └── <future-skill> → symlink
│   │   └── mcp.json
│   │
│   └── codex/                           # mcd-agent-toolkit plugin for Codex
│       ├── skills/
│       │   ├── prevent → symlink
│       │   └── <future-skill> → symlink
│       └── install.sh
```

**Key distinction:** Under `claude-code/`, each skill is its own plugin with its own `plugin.json`. Under every other editor, the editor directory itself is the plugin, and skills are feature modules within it.

### Isolation Guarantees

1. **Cache prefixes.** Each skill uses unique prefixes for temp files (`mc_prevent_*`, `mc_<skill>_*`). No cross-contamination.
2. **Session scoping.** Cache keys include session IDs. Different editor sessions never interfere.
3. **Independent hooks.** Each skill registers its own hooks. A bug in one skill's hook logic doesn't affect another's.
4. **Self-contained skills.** Skill definitions in `skills/` have no cross-references. Each skill is a standalone instruction set.

### Adding a New Feature to the Toolkit

When adding a new skill that needs hooks:

1. Create the skill in `skills/<name>/`
2. Create shared hook logic in `hooks/<name>/lib/` with a unique cache prefix (`mc_<name>_*`)
3. For each editor plugin, add an adapter module that wires the shared logic into the editor's hook system
4. The plugin's entry point registers hooks for all enabled features

When adding a skill that doesn't need hooks:

1. Create the skill in `skills/<name>/`
2. Each editor plugin's install process copies it alongside existing skills
3. No hook wiring needed — the skill is purely instructional

## Skill Registry Compatibility

Skills and plugins are distributed through independent channels:

| Channel | Granularity | Affected by plugin structure? |
|---------|-------------|-------------------------------|
| **skills.sh** (`npx skills add ... --skill <name>`) | Per-skill | No — discovers skills by scanning `skills/` directory |
| **skillsmp.com** | Per-skill | No — auto-indexes from repo, reads `skills/` |
| **Claude Code marketplace** | Per-plugin | Maintained separately (see exception above) |
| **Editor plugin installs** | Per-toolkit | Yes — one install gets all features |

The `--skill` flag in `npx skills add monte-carlo-data/mcd-agent-toolkit --skill monte-carlo-prevent` addresses individual skills by directory name. This is independent of plugin organization. **Moving to a unified toolkit plugin does not affect individual skill publishability.**

## For Contributors

### When to create a new skill vs. extend an existing one

- **New skill:** The capability serves a distinct workflow (e.g., "prevent bad changes" vs. "observe data quality trends"). It would make sense as a standalone product feature.
- **Extend existing:** The capability enhances an existing workflow (e.g., adding a new check type to MC Prevent's impact assessment).

### When a skill needs a plugin

A skill needs a plugin when it requires **enforcement** — gating edits, blocking commits, injecting prompts at specific lifecycle points. If the skill is purely advisory (the agent follows instructions without needing workflow gates), it doesn't need a plugin.

### Hook implementation pattern

For skills that need hooks, follow the existing two-layer pattern:

1. **Shared logic** (`hooks/<skill>/lib/`): Platform-agnostic Python. Contains all decision-making. No editor-specific I/O.
2. **Editor adapters** (`plugins/<editor>/hooks/<skill>/`): Thin scripts that read editor-specific JSON input, call shared logic, and format editor-specific output. For Claude Code, the path is `plugins/claude-code/<skill>/hooks/` due to the per-skill plugin structure.

This ensures business logic is written and tested once, with only I/O adapters varying per editor. OpenCode is an exception — it ports the logic to TypeScript since the plugin SDK requires it.
