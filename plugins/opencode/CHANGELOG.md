# Changelog

All notable changes to the Monte Carlo Agent Toolkit plugin for OpenCode will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.6.1] - 2026-04-16

### Changed

- Add connection-auth-rules skill for building Connection Auth Rules configs

## [1.6.0] - 2026-04-16

### Changed

- Consolidate `monitor-creation`, `agent-monitoring`, and `monitoring-advisor` into a single `monitoring-advisor` skill
- Add `data-monitor-creation.md` and `agent-monitor-creation.md` mid-level creation procedures
- Move per-type references with `data-`/`agent-` prefixes and distribute constraints
- Fix MCP tool names to snake_case across all skill docs
- Update trigger evals: direct monitor creation and agent monitoring now trigger this skill

## [1.5.0] - 2026-04-15

### Changed

- Add asset-health skill (#33)
- Add AI agent monitoring to monitoring-advisor skill (#48)

## [1.4.0] - 2026-04-14

### Changed

- c4842c4 fix: add missing skill registrations — READMEs, symlinks, and sync rules (#46)
- 647669a feat: add automated-triage skill (#40)
- 9477ae1 feat: add analyze-root-cause skill for incident investigation (#37)

## [1.3.0] - 2026-04-14

### Changed

- f46cdfb Add remediation skill for investigating and fixing data quality alerts (#39)
- c5dd6a5 feat: add agent-monitoring skill and plugin (AI-167) (#35)
- 9884442 feat: add storage cost analysis and performance diagnosis skills (#36)

## [1.2.0] - 2026-04-13

### Changed

- f40f262 fix: add --force flag to release script to skip branch check
- 9155214 fix: release script PR flow + awk multiline bug
- ad388c7 fix: register monitoring-advisor as plugin command + add trigger evals (#38)
- 9147282 K2-287: add monitoring-advisor skill (#34)
- 930a745 feat: add prevent trigger evals and shared eval runner (#29)
- cf09cb8 fix: add missing name field to generate-validation-notebook SKILL.md (#32)
- 44f85ab Add monitor-creation skill and wire into all editor plugins (#31)
- 6bc245d fix: correct marketplace add command to use repo name (#30)
- e8597c9 fix: improve release script post-run message (#28)

## [1.0.0] - 2026-04-06

### Changed

- Restructure from per-skill `@montecarlo/opencode-prevent` to unified `@montecarlo/mc-agent-toolkit` plugin
- Plugin directory is now `plugins/opencode/` (was `plugins/opencode/prevent/`)
- Prevent feature module namespaced under `src/prevent/` for multi-skill support
- Top-level `src/index.ts` entry point registers all feature modules

### Upgrade instructions

Existing users should re-run the install script to pick up the new structure.

---

_History prior to the unified toolkit restructure (when this was `@montecarlo/opencode-prevent`):_

## [1.0.0-prevent] - 2026-04-02

### Added

- TypeScript plugin porting all 4 Claude Code prevent hooks to OpenCode's event system:
  - `tool.execute.before` — pre-edit gate blocking dbt model edits until impact assessment runs
  - `tool.execute.after` — post-edit tracking accumulating edited table names per turn
  - `tool.execute.before` (bash) — pre-commit gate prompting for validation on staged dbt files
  - `session.idle` event — turn-end prompt for validation queries and monitor coverage
- `apply_patch` support with multi-file patchText parsing
- Install script (`install.sh`) that sets up plugin, skill, command, and MCP config in one step
- `/mc-validate` slash command for generating validation queries
- `opencode.json` template with Monte Carlo MCP server config and plugin registration
- 84 unit tests covering cache, detection, and all hook behaviors

### Fixed

- Plugin must be explicitly registered in `opencode.json` `"plugin"` array (OpenCode does not auto-discover subdirectory plugins)
- Package.json `exports` field required for OpenCode to resolve the entry point (`"."` and `"./server"`)
- Use `writeSecure` (O_TRUNC) instead of `appendSecure` (O_APPEND) for turn files — O_APPEND files disappeared under Bun on macOS
