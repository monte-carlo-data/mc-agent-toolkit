# Changelog

All notable changes to the Monte Carlo Agent Toolkit plugin for Codex will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.8.2] - 2026-04-23

### Changed

- `monitoring-advisor`: hardened the `create_*_monitor_mac` guidance against the top failure modes seen in production over the last 7 days (70 events across 14 categories). Changes span `data-monitor-creation.md` (domain-uuid resolution, warehouse-UUID requirement, column-verification gate, enum discipline, table existence check) and the per-type references (`alert_condition` shape constraints in `data-validation-monitor`, metric-name and operator-enum corrections in `data-metric-monitor` / `data-custom-sql-monitor`, `change`-threshold documentation in `data-custom-sql-monitor`, datetime-type requirement for `aggregate_time_field`, arg-shape constraints in `data-table-monitor` and `data-validation-monitor`, predicate/field-type semantics in `data-validation-monitor`, `threshold_value` requirement clarification in `data-comparison-monitor`). See [PR #66](https://github.com/monte-carlo-data/mc-agent-toolkit/pull/66) for the full error → fix mapping.

### Fixed

- `scripts/bump-version.sh` normalizes drifted plugin versions. Before this release, claude-code was at 1.8.1 while codex/copilot/cursor/opencode were stuck at 1.7.0 because the script's sed only matched the claude-code version. The non-monotonic 1.7.0 → 1.8.2 jump on those four plugins is intentional — they caught up to the canonical version in this PR. Future bumps stay in sync automatically.

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

## [1.0.0] - 2026-04-02

- Initial Codex plugin for Monte Carlo Agent Toolkit
- Shared core library with thin Codex adapters
- Hook support: PreToolUse (Edit|Write, Bash), PostToolUse (Edit|Write), Stop
- Note: Edit|Write matchers are wired for forward compatibility (Codex currently only emits PreToolUse/PostToolUse for Bash)
