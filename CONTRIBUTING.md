# Contributing to mc-agent-toolkit

Welcome! We appreciate contributions from both Monte Carlo engineers and the community.

**Repo layout:** `skills/` is the single source of truth for skill content. `plugins/shared/` contains platform-agnostic hook logic. Each editor under `plugins/<editor>/` is a single `mc-agent-toolkit` plugin.

## Repository structure

```
mc-agent-toolkit/
├── skills/                              # Shared skill definitions (platform-agnostic)
│   ├── monitor-creation/
│   │   ├── SKILL.md
│   │   └── references/
│   ├── prevent/
│   │   ├── SKILL.md
│   │   └── references/
│   ├── generate-validation-notebook/
│   ├── monitoring-advisor/
│   ├── push-ingestion/
│   └── remediation/
│
├── plugins/
│   ├── shared/                          # Platform-agnostic hook logic
│   │   └── prevent/lib/                 # Business logic (symlinked by editor plugins)
│   │
│   ├── claude-code/                     # Unified mc-agent-toolkit plugin
│   │   ├── .claude-plugin/plugin.json
│   │   ├── hooks/prevent/              # Hook adapters (thin, call shared lib)
│   │   ├── skills/ (monitor-creation, monitoring-advisor, prevent, generate-validation-notebook, push-ingestion, remediation → symlinks)
│   │   └── commands/ (prevent/, push-ingestion/, monitoring-advisor/)
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
2. **Register the skill as a command** (required for the skill to appear as user-invocable in the plugin):
   - Create `plugins/claude-code/commands/<skill-name>/` with at least one `.md` command file.
   - Add the directory to the `commands` array in `plugins/claude-code/.claude-plugin/plugin.json`.
   - Without a commands entry, the skill will not be discoverable as `mc-agent-toolkit:<skill-name>`.
   - If the skill has sub-commands (e.g., `/mc-validate`), add additional `.md` files in the same directory.
3. If the skill needs hooks, create adapters in `plugins/claude-code/hooks/<skill-name>/` following the two-layer pattern (see below).
4. Bump the `version` in `plugins/claude-code/.claude-plugin/plugin.json`.
5. Test locally with `claude --plugin-dir ./plugins/claude-code`.

## Updating an existing skill

1. Edit files directly under `skills/<skill-name>/`. The corresponding plugin picks up changes automatically via the symlink — no additional steps needed.
2. If the change is user-facing, bump the version: `./scripts/bump-version.sh patch` (or `minor`/`major` — see [Version bumping](#version-bumping)). This updates all 5 plugin config files in sync. Claude Code uses the version field to determine whether to update an installed plugin.

## Fixing a bug

1. For skill content bugs: fix in `skills/<skill-name>/` and bump the version with `./scripts/bump-version.sh patch`.
2. For plugin-level bugs (hooks, plugin.json config): fix in `plugins/claude-code/<skill-name>/` and bump the version with `./scripts/bump-version.sh patch`.

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

## Releasing

Version is tracked in code (the 5 plugin config files). Bump it as part of your feature PR — no separate release step needed. When the version change merges to `main`, a GitHub Actions workflow automatically creates the corresponding git tag and GitHub Release.

### Bump the version

Use the convenience script to update all 5 plugin config files and changelogs in one step:

```bash
# Bump patch version (1.0.0 → 1.0.1)
./scripts/bump-version.sh patch

# Bump minor version (1.0.0 → 1.1.0)
./scripts/bump-version.sh minor

# Set an explicit version
./scripts/bump-version.sh 2.0.0

# Preview what would happen without making changes
./scripts/bump-version.sh patch --dry-run
```

The script:
1. Reads the current version from `plugins/claude-code/.claude-plugin/plugin.json`
2. Computes the next version based on the bump type
3. Opens `$EDITOR` with a changelog template pre-filled with commits since the last tag
4. Updates `"version"` in all 5 plugin config files
5. Prepends the changelog entry to all 5 `CHANGELOG.md` files

Commit the resulting changes as part of your PR.

### Automated checks

Two automated checks help catch missing version bumps:

- **`/ship`** — before opening a PR, checks whether the diff touches shipped content (`skills/`, `plugins/`) without a version bump, and prompts you to run the script.
- **`/code-review`** — the `versioning` reviewer agent runs on every PR and flags missing or inconsistent version bumps as an ISSUE-level finding, with a suggested bump level.

### GitHub Release

When a version bump merges to `main`, the GitHub Actions workflow (`.github/workflows/release-on-tag.yml`) automatically creates a git tag and GitHub Release with auto-generated release notes from PR titles.

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
