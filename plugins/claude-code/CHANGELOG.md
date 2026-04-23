# Changelog

All notable changes to the Monte Carlo Agent Toolkit plugin for Claude Code will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.8.2] - 2026-04-23

### Changed

- `monitoring-advisor`: hardened the `create_*_monitor_mac` guidance against the top failure modes seen in production over the last 7 days (70 events across 14 categories). Changes span `data-monitor-creation.md` (domain-uuid resolution, warehouse-UUID requirement, column-verification gate, enum discipline, table existence check) and the per-type references (`alert_condition` shape constraints in `data-validation-monitor`, metric-name and operator-enum corrections in `data-metric-monitor` / `data-custom-sql-monitor`, `change`-threshold documentation in `data-custom-sql-monitor`, datetime-type requirement for `aggregate_time_field`, arg-shape constraints in `data-table-monitor` and `data-validation-monitor`, predicate/field-type semantics in `data-validation-monitor`, `threshold_value` requirement clarification in `data-comparison-monitor`). See [PR #66](https://github.com/monte-carlo-data/mc-agent-toolkit/pull/66) for the full error → fix mapping.

### Fixed

- `scripts/bump-version.sh` normalizes drifted plugin versions. Before this release, claude-code was at 1.8.1 while codex/copilot/cursor/opencode were stuck at 1.7.0 because the script's sed only matched the claude-code version. The non-monotonic 1.7.0 → 1.8.2 jump on those four plugins is intentional — they caught up to the canonical version in this PR. Future bumps stay in sync automatically.

## [1.8.1] - 2026-04-20

### Fixed

- Plugin update failed on 1.8.0 with `commands path not found` for `incident-response` and `proactive-monitoring`. The 1.8.0 manifest declared these command paths but the directories were never committed. Added the missing `/monte-carlo-incident-response` and `/monte-carlo-proactive-monitoring` slash-command files so the paths resolve and the workflows documented in `/mc` are actually invokable.

## [1.8.0] - 2026-04-20

### Added

- `context-detection` skill that routes ambiguous data-related asks to the right workflow by probing available MCP tools
- `incident-response` workflow skill that runs a root-cause investigation for a reported alert or incident
- `proactive-monitoring` workflow skill that walks users from "what should I monitor?" to concrete monitor creation
- `/mc` catalog command
- SessionStart welcome hook — a minimal one-line greeting triggered only when a dbt project or `montecarlo.yml` is detected in the workspace
- `when_to_use` frontmatter on the new workflow skills so the router has explicit trigger examples

## [1.7.1] - 2026-04-17

### Changed

- feat(automated-triage): add mark_event_as_normal guidance and scope interactive triage by domain/audience

## [1.7.0] - 2026-04-17

### Changed

- Add tune-monitor skill for monitor noise reduction analysis

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
