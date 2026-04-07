# Contributing to mc-agent-toolkit

Welcome! We appreciate contributions from both Monte Carlo engineers and the community.

**Repo layout:** `skills/` is the single source of truth for skill content. `plugins/shared/` contains platform-agnostic hook logic. Each editor under `plugins/<editor>/` is a single `mc-agent-toolkit` plugin.

## Repository structure

```
mc-agent-toolkit/
├── skills/                              # Shared skill definitions (platform-agnostic)
│   ├── prevent/
│   │   ├── SKILL.md
│   │   └── references/
│   ├── generate-validation-notebook/
│   └── push-ingestion/
│
├── plugins/
│   ├── shared/                          # Platform-agnostic hook logic
│   │   └── prevent/lib/                 # Business logic (symlinked by editor plugins)
│   │
│   ├── claude-code/                     # Unified mc-agent-toolkit plugin
│   │   ├── .claude-plugin/plugin.json
│   │   ├── hooks/prevent/              # Hook adapters (thin, call shared lib)
│   │   ├── skills/ (prevent, generate-validation-notebook, push-ingestion → symlinks)
│   │   └── commands/ (prevent/, push-ingestion/)
│   │
│   ├── cursor/                          # Unified mc-agent-toolkit plugin
│   │   ├── .cursor-plugin/plugin.json
│   │   ├── hooks/prevent/              # Hook adapters (thin, call shared lib)
│   │   ├── skills/prevent → symlink
│   │   └── mcp.json
│   │
│   ├── opencode/                        # Unified mc-agent-toolkit plugin
│   │   ├── src/prevent/                # TypeScript feature module
│   │   ├── skills/prevent → symlink
│   │   └── opencode.json
│   │
│   └── codex/                           # Unified mc-agent-toolkit plugin
│       └── skills/prevent → symlink
│
├── .claude-plugin/marketplace.json
├── .cursor-plugin/marketplace.json
├── README.md
├── LICENSE
└── SECURITY.md
```

Plugins reference skills via symlinks so that skills are authored once and shared across all editor plugins. Shared hook logic in `plugins/shared/<skill>/lib/` is also symlinked into editor-specific adapter directories.

## Adding a new skill

1. Create a new directory under `skills/` with a kebab-case name (e.g., `skills/my-new-skill/`).
2. Add a `SKILL.md` with valid YAML frontmatter (`name` and `description` are required). Follow the [Agent Skills specification](https://agentskills.io).
3. Optionally add supporting directories: `scripts/`, `references/`, `assets/`.
4. Test the skill locally by copying it to `~/.claude/skills/my-new-skill/` and verifying Claude discovers and activates it correctly.

## Adding a new skill to the Claude Code plugin

1. Add a symlink in `plugins/claude-code/skills/`:
   ```bash
   cd plugins/claude-code/skills
   ln -s ../../../skills/<skill-name> <skill-name>
   ```
2. If the skill has slash commands, create `plugins/claude-code/commands/<skill-name>/` and add `.md` command files. Update the `commands` array in `plugins/claude-code/.claude-plugin/plugin.json`.
3. If the skill needs hooks, create adapters in `plugins/claude-code/hooks/<skill-name>/` following the two-layer pattern (see below).
4. Bump the `version` in `plugins/claude-code/.claude-plugin/plugin.json`.
5. Test locally with `claude --plugin-dir ./plugins/claude-code`.

## Updating an existing skill

1. Edit files directly under `skills/<skill-name>/`. The corresponding plugin picks up changes automatically via the symlink — no additional steps needed.
2. If the change is user-facing, bump the `version` in the corresponding plugin's `plugin.json`. Claude Code uses the version field to determine whether to update an installed plugin.

## Fixing a bug

1. For skill content bugs: fix in `skills/<skill-name>/` and bump the plugin version.
2. For plugin-level bugs (hooks, plugin.json config): fix in `plugins/claude-code/<skill-name>/` and bump the plugin version.

## Pull request guidelines

- One skill or plugin per PR unless changes are tightly coupled.
- Include a clear description of what the skill/plugin does and when it should activate.
- For new skills: include example prompts that should trigger the skill.
- For bug fixes: describe the incorrect behavior and how to reproduce.
- Ensure symlinks are relative and resolve correctly (CI will verify this).
- Run `git log --follow` on any moved files to confirm history is preserved.

## Version bumping

- **Patch** (`1.0.0` → `1.0.1`): bug fixes and minor content improvements.
- **Minor** (`1.0.0` → `1.1.0`): new features, new scripts, or significant skill content changes.
- **Major** (`1.0.0` → `2.0.0`): breaking changes to skill behavior or hook interfaces.

## Architecture

For the reasoning behind the plugin structure, the unified toolkit model, and guidelines on how skills and plugins interact across editors, see the [Plugin Architecture Guide](docs/plugin-architecture-guide.md).

## Adding support for a new editor

1. Create a single `mc-agent-toolkit` plugin directory under `plugins/<editor>/`.
2. Add skill symlinks under `plugins/<editor>/skills/` pointing to `skills/<skill-name>`.
3. If the skill needs hooks, create shared logic in `plugins/shared/<skill>/lib/` and thin editor-specific adapters in `plugins/<editor>/hooks/<skill>/`.
4. Document the installation steps in the plugin's own README and in the repo's main README.

### Hook implementation pattern

For skills that need hooks, follow the two-layer pattern:

1. **Shared logic** (`plugins/shared/<skill>/lib/`): Platform-agnostic Python. All decision-making. No editor-specific I/O.
2. **Editor adapters** (`plugins/<editor>/hooks/<skill>/`): Thin scripts that read editor-specific JSON, call shared logic, and format output.

OpenCode is an exception — it ports hook logic to TypeScript since the `@opencode-ai/plugin` SDK requires it. See `plugins/opencode/src/prevent/` for a complete example.
