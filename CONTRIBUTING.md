# Contributing to mc-agent-toolkit

Welcome! We appreciate contributions from both Monte Carlo engineers and the community.

**Repo layout:** `skills/` is the single source of truth for skill content. `plugins/shared/` contains platform-agnostic hook logic. Each editor under `plugins/<editor>/` is a single `mc-agent-toolkit` plugin.

## Repository structure

```
mc-agent-toolkit/
├── skills/                              # Shared skill definitions (platform-agnostic)
│   ├── monitoring-advisor/
│   │   ├── SKILL.md                     # Unified router for all monitoring
│   │   └── references/                  # data-* and agent-* monitor type refs
│   ├── prevent/
│   │   ├── SKILL.md
│   │   └── references/
│   ├── generate-validation-notebook/
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
│   │   ├── skills/ (monitoring-advisor, prevent, generate-validation-notebook, push-ingestion, remediation → symlinks)
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

**Prefer `/skill-author`.** Repo contributors can run `/skill-author` in a Claude session at the repo root. It interviews you, applies the extend-or-split rules below, and walks the full registration checklist. Requires Anthropic's `skill-creator` plugin (`/plugin install skill-creator@claude-plugins-official`).

Manual steps (if you prefer):

1. Create a new directory under `skills/` with a kebab-case name (e.g., `skills/my-new-skill/`).
2. Add a `SKILL.md` with valid YAML frontmatter (`name` and `description` are required). Follow the [Agent Skills specification](https://agentskills.io) and the [Skill authoring standards](#skill-authoring-standards) below.
3. Optionally add supporting directories: `scripts/`, `references/`, `assets/`.
4. [Register the skill with the orchestration layer](#orchestration-registration) so it's discoverable via context detection and the `/mc` catalog.
5. Add a trigger-eval entry under `plugins/claude-code/evals/<skill-name>/` so skill activation can be measured. See [live evals framework (PR #53)](https://github.com/monte-carlo-data/mc-agent-toolkit/pull/53) and existing eval files for the expected structure.
6. Test the skill locally by copying it to `~/.claude/skills/my-new-skill/` and verifying Claude discovers and activates it correctly.

## Skill authoring standards

These standards exist so the toolkit stays coherent as it grows. New skill PRs should comply; existing skills are being brought up to compliance incrementally.

### Extend or split?

**Default: extend an existing skill.** Splitting is the exception — a new atomic skill
is one more thing the router has to disambiguate, and one more entry in the catalog.
Only split if one of the tests below forces it.

1. **Find the nearest peer.** Search `skills/` for candidates that share any of:
   - the same capability bucket,
   - overlapping user phrasings in `description` or `when_to_use`,
   - the same primary MCP surface or data input.

   For each candidate, try to write a realistic user prompt that *should* route
   to your new skill but could plausibly activate the candidate instead. If you
   can write one, that candidate is a peer — continue to step 2 with it. If no
   candidate survives this test, there's no routing collision; create the new
   skill and stop here.

2. **Budget check.** Open the peer's `SKILL.md`. If adding a sentence to
   `description` or a bullet to `when_to_use` would push the combined text past
   ~1,400 characters (the 1,536 ceiling minus headroom), you must split. Routing
   quality degrades once the frontmatter is truncated.

3. **Surface check.** Does the new behavior hit a different MCP surface, produce
   a different output artifact, or belong to a different capability bucket than
   the peer? If yes, split. If no, extend.

4. **Otherwise, extend.** Phrasing overlap, "it feels like its own thing," or
   wanting a cleaner file on its own are not reasons to split. Add a bullet to
   the peer's `when_to_use`, add a `references/` file if the workflow needs more
   room, and move on.

**PR requirement.** If you split, name the peer(s) you considered in the PR
description and point to which test above forced the split. If none did, extend.

### Capability buckets

Capability buckets are how we organize the toolkit's story in [our public documentation](https://docs.getmontecarlo.com/docs/agent-toolkit) — they're the sections customers read when deciding which skills matter for their use case. They don't affect how skills are loaded or routed (the agent discovers skills by name and `when_to_use`, not by bucket). The bucket is a communication tool, not a technical one.

Every user-facing skill belongs to one of the following buckets. Declare the bucket in the PR description when adding a new skill so we know where it lands in the public docs:

- **Trust** — foundational pre-query and pre-build checks so the agent doesn't reach for data that isn't ready (e.g., `asset-health`).
- **Incident Response** — reactive investigation and fix workflows (e.g., `analyze-root-cause`, `remediation`, `automated-triage`).
- **Monitoring** — proactive coverage analysis and monitor creation/tuning (e.g., `monitoring-advisor`, `tune-monitor`).
- **Prevent** — silent, auto-activating skills that shape code changes before and after they happen (e.g., `prevent`, `generate-validation-notebook`).
- **Optimize** — cost and performance work on existing data assets (e.g., `storage-cost-analysis`, `performance-diagnosis`).

If none of these fit, that's a signal to discuss with the toolkit maintainers before merging — a genuinely new bucket is a meaningful addition to the toolkit's story.

Two other kinds of skills sit outside the user-facing buckets and don't need a bucket declaration:

- **Setup skills** — admin/onboarding only, invoked by name during initial setup rather than discovered through routing (e.g., `push-ingestion`, `connection-auth-rules`).
- **Agent-routing skills** — context detection and workflow orchestration (`context-detection`, `incident-response`, `proactive-monitoring`). These are meta-skills, not capability skills; new routing skills are owned by the agent-toolkit core team, not contributed ad hoc.

### Frontmatter schema

Every `SKILL.md` requires the following frontmatter fields:

```yaml
---
name: kebab-case-skill-name
description: |
  A one-paragraph description of what the skill does and when it activates.
when_to_use: |
  Explicit activation cues and example user phrasings.
---
```

- `name` and `description` are required by Claude Code.
- `when_to_use` is strongly recommended — it's a Claude-specific convention today but likely to be adopted by other editors.
- Additional fields are allowed but ignored by Claude. Plugin versions live in the plugin manifests (`plugins/*/.*-plugin/plugin.json`) and are managed by `scripts/bump-version.sh`, not at the skill level.

### Description hygiene

The `description` field is the primary mechanism by which the agent decides whether to activate the skill. Descriptions are not free-form marketing copy — they are routing instructions.

- **Length:** ≤1,024 characters. Claude Code truncates the combined `description` + `when_to_use` text to 1,536 characters when loading the skill listing, so stay within that combined budget.
- **Voice:** third person. Describe what the skill does, not what "this skill" does. Avoid openings like "This skill…" or "Use this skill when…".
- **Front-load triggers:** specific verbs, artifact names, and representative user phrasings should appear in the first sentence, where they have the highest weight during skill ranking.
- **Be specific:** vague descriptions ("helps with data quality") under-route. Concrete descriptions ("investigates data incidents using alert lookup, lineage tracing, and ETL checks; activates on 'something is broken', 'triage my alerts', 'why is this failing'") route reliably.

### `when_to_use` conventions

Use `when_to_use` to extend the activation surface without bloating the main description:

- List explicit activation cues: verbs, artifact names, user phrasings.
- Include example user prompts in quotes where helpful: `"how is table X"`, `"tune this monitor"`, `"reduce false positives on..."`.
- Call out what the skill does **not** cover if a peer skill is likely to get confused (see Disambiguation below).

### Disambiguation

If a new skill's scope overlaps a peer skill, the `description` or `when_to_use` must name the peer and explain the boundary. This prevents activation ambiguity.

Example: if adding a skill that acts on alerts, explicitly call out how it differs from `analyze-root-cause` and `remediation` — investigation vs. action.

### Naming

- Use kebab-case (e.g., `monitoring-advisor`, not `MonitoringAdvisor`).
- Keep names short and verb- or noun-phrase based.

The existing skill catalog has an inconsistency between `monte-carlo-*`-prefixed names and bare names (carried over from separate authoring contexts). Standardization will happen in a dedicated follow-up; for now, match the convention used by neighboring skills in the same bucket.

### Orchestration registration

The toolkit uses an agent-routing layer (added in [PR #56](https://github.com/monte-carlo-data/mc-agent-toolkit/pull/56)) that decides which skill to invoke on ambiguous requests and sequences skills into workflows. When a new atomic skill lands without registering with this layer, it becomes reachable only by explicit invocation and the orchestration layer silently rots.

Every new user-facing atomic skill PR must include, in the same diff:

1. **Signal definition** — add a row to `skills/context-detection/references/signal-definitions.md` under *Conversation Signals* (and/or *Workspace Signals*) describing the keywords, artifacts, and user phrasings that should route to the new skill. This is the map context-detection uses to route ambiguous requests.
2. **Workflow orchestrator updates (if applicable)** — if the skill belongs in an existing workflow (`skills/incident-response/SKILL.md` or `skills/proactive-monitoring/SKILL.md`), add it to the appropriate step.
3. **Catalog entry** — add a row to `plugins/claude-code/commands/catalog/mc.md` so the `/mc` catalog lists the new skill.

Setup and agent-routing skills are exempt from this rule. Setup skills are invoked by name, not routed to; routing skills *are* the orchestration layer.

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
