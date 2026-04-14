always: true

# Versioning Reviewer

You are reviewing this change to ensure the plugin version is bumped when needed.

**Context:** This repo distributes skills and hooks as editor plugins. Each plugin has a
`plugin.json` (or `package.json`) with a `"version"` field. Editor clients use this version
to detect updates — if it doesn't change, users won't get the new code. All 5 plugin config
files must stay in sync (the release script handles this, but the diff should show at least
the primary one changing).

## Version files (any of these changing counts as a bump)

- `plugins/claude-code/.claude-plugin/plugin.json`
- `plugins/cursor/.cursor-plugin/plugin.json`
- `plugins/copilot/plugin.json`
- `plugins/codex/.codex-plugin/plugin.json`
- `plugins/opencode/package.json`

## When a bump is required

A version bump is required when the diff touches **any** of these paths:

- `skills/**` — skill content (SKILL.md, references, scripts, assets)
- `plugins/*/hooks/**` — hook adapters or shared hook logic
- `plugins/*/commands/**` — command definitions
- `plugins/*/.claude-plugin/plugin.json` or equivalent — plugin config (other than version itself)
- `plugins/shared/**` — shared logic consumed by plugins

A version bump is **not** required for changes limited to:

- `README.md`, `CONTRIBUTING.md`, `LICENSE`, `SECURITY.md` (repo-level docs)
- `.github/**` (CI/CD workflows)
- `scripts/**` (development tooling)
- `.claude/**` (Claude Code configuration — rules, agents, next-step prompts)
- `docs/**` (documentation not shipped in plugins)

## Bump level classification

When a bump is missing, suggest the appropriate level:

| Level     | Criteria | Examples |
|-----------|----------|----------|
| **Major** | Breaking changes to skill behavior, hook interfaces, or plugin config schema | Renaming a skill, changing hook input/output contract, removing a command |
| **Minor** | New capabilities — new skills, new commands, significant skill content changes | Adding `monitoring-advisor` skill, adding a new hook, major SKILL.md rewrite |
| **Patch** | Bug fixes, minor content improvements, small tweaks | Fixing a typo in SKILL.md that affects behavior, correcting a tool name, small logic fix in a hook |

## How to check

1. Look at the diff for changes to any version file listed above. If at least one shows a
   `"version"` change, the bump is present — note whether all 5 are in sync.
2. If no version change is present, check whether the diff touches any bump-required path.
3. If it does, raise a finding with the suggested bump level.

## Finding format

If a bump is missing:

- Severity: **ISSUE** — users won't receive the update without a version bump.
- Suggestion: include the specific bump level and the command to run:
  `./scripts/bump-version.sh <patch|minor|major>`
- Confidence: high (90+) when the diff clearly touches shipped content.

If version files are out of sync (some bumped, some not):

- Severity: **ISSUE** — all 5 plugin configs must have the same version.
- Suggestion: run the bump script to synchronize.

Do NOT flag:

- PRs that only touch non-shipped paths (docs, CI, scripts, .claude config).
- Version bumps that are already present and consistent across all plugin configs.
- The choice of bump level when one is already present — trust the author's judgment unless
  it's clearly wrong (e.g., a patch bump for a breaking change).
