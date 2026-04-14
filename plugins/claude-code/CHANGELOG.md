# Changelog

All notable changes to the Monte Carlo Agent Toolkit plugin for Claude Code will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

## [1.1.0] - 2026-04-08

### Added

- Monitor Creation skill — guides AI agents through creating Monte Carlo monitors correctly with validation, field-type compatibility checks, and monitors-as-code YAML generation. Covers metric, validation, custom SQL, comparison, and table monitors.

## [1.0.0] - 2026-04-07

### Changed

- Restructure from three separate plugins (`mc-prevent`, `mc-generate-validation-notebook`, `mc-push-ingestion`) to unified `mc-agent-toolkit` plugin
- All skills, commands, hooks, and config merged into a single plugin directory
- Hooks namespaced under `hooks/prevent/` for multi-skill support
- Commands namespaced under `commands/<skill>/`
- MCP server and permissions configured once at plugin root

### Upgrade instructions

Claude Code treats this as a new plugin. Existing users must uninstall old plugins and install the new one:

```bash
# 1. Uninstall old plugins
claude plugin remove mc-prevent
claude plugin remove mc-generate-validation-notebook
claude plugin remove mc-push-ingestion

# 2. Install the unified plugin
/plugin install mc-agent-toolkit@mc-marketplace
```

---

_History prior to the unified toolkit restructure (mc-prevent plugin only):_

## [1.0.0-prevent] - 2026-04-01

### Changed

- Rename plugin from `mc-safe-change` to `mc-prevent`
- Rename skill from `monte-carlo-safe-change` to `monte-carlo-prevent`
- Reset version to 1.0.0 as a fresh identity

---

_Entries below predate the rename from `mc-safe-change` to `mc-prevent`._

## [1.1.2] - 2026-03-30

### Changed

- Migrate MCP server from header-based auth (`npx mcp-remote` + env vars) to zero-config HTTP/OAuth
- Plugin now bundles `.mcp.json` with HTTP transport — no manual key setup required
- Auto-approve MCP tool calls via `permissions.allow` for both plugin-bundled and standalone server prefixes
- Update all setup docs to OAuth-first flow; legacy header-based auth moved to collapsible fallback sections

### Fixed

- Use `permissions.allow` instead of `allowedTools` in `settings.json` (was silently ignored)
- Restore `commands` field in `plugin.json` (accidentally removed in initial branch)
- Track plugin `.mcp.json` in git via `.gitignore` negation rule

## [1.1.1] - 2026-03-30

### Fixed

- Session cache is now keyed per Claude Code session ID, preventing state from leaking across sessions

## [1.1.0] - 2026-03-26

### Added

- Hook-based enforcement for dbt model edits (pre-edit gate, post-edit accumulator, turn-end validation prompt, commit gate)
- `/mc-validate` slash command for explicit validation
- Shared lib: dbt model detection, session cache, fail-open decorator
- Monte Carlo MCP server wiring

## [1.0.0-initial] - 2026-03-22

- Initial plugin shell with skill file and manifest
