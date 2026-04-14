# Changelog

All notable changes to the Monte Carlo Agent Toolkit plugin for Cursor will be documented in this file.

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

## [1.0.0] - 2026-04-06

### Changed

- Restructure from per-skill `mc-prevent` plugin to unified `mc-agent-toolkit` plugin
- Plugin directory is now `plugins/cursor/` (was `plugins/cursor/prevent/`)
- Hooks namespaced under `hooks/prevent/` for multi-skill support
- Shared hook logic moved to `plugins/shared/prevent/lib/`

### Upgrade instructions

Existing users should re-run the install script to pick up the new structure:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/monte-carlo-data/mc-agent-toolkit/main/plugins/cursor/scripts/install.sh)
```

---

_History prior to the unified toolkit restructure (when this was the `mc-prevent` plugin):_

## [1.0.0-prevent] - 2026-04-02

### Added

- Initial Cursor adapter for Monte Carlo Prevent
- Hook-based enforcement for dbt model edits (pre-edit gate, post-edit accumulator, turn-end validation prompt, commit gate)
- `/mc-validate` command for explicit validation
- Monte Carlo MCP server wiring
- Shared platform-agnostic hook logic via `hooks/prevent/lib/`
