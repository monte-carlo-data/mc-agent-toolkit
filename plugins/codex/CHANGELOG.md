# Changelog

All notable changes to the Monte Carlo Agent Toolkit plugin for Codex will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

### Changed

- monitoring-advisor: align coverage and data-monitor-creation guidance with the internal Monte Carlo coverage agent — default to HIGH+MEDIUM scope (don't ask) with action-bias batching, "create a use case" handling, importance-score-is-not-business-criticality caveat, dedup + no-fabricated-credit-cost guidance, description(title)/notes(reasoning) split, a profiling-before-thresholds matrix, the field-monitor-requires-a-live-table-monitor prerequisite, and view fixed-schedule rule.

## [1.12.0] - 2026-05-20

### Added

- New `/manage-mac` skill: create, edit, validate, and import Monitors-as-Code YAML files — CLI-first: uses `montecarlo monitors compile` to validate and `apply` to deploy; falls back to MC MCP tools then manual validation
- Schema validation gates injected into `monitoring-advisor` and `tune-monitor` — agents now validate generated YAML against the published schema before presenting it to the user

## [1.11.1] - 2026-05-13

### Added

- Add `MC_PREVENT_HOOKS_DISABLED=1` env var to disable prevent hooks (block-edit, pre-commit, turn-end) for users who want the skills without the gating behavior.

### Changed

- Clarify telemetry disclosure in plugin README: explicit opt-out instructions and confirmation that no prompts/arguments/code are sent.
- Polish `plugin.json` metadata for Anthropic plugin directory submission (expanded description, `author.email`, `homepage`).
- Add `"category": "monitoring"` to the marketplace.json entry.

## [1.11.0] - 2026-05-07

### Added

- **Instrument Agent skill** — walks Monte Carlo Agent Observability customers through instrumenting a new Python AI agent for Monte Carlo. Detects AI libraries in the codebase, proposes the Monte Carlo OpenTelemetry SDK install with matching instrumentors, generates tracing setup tailored to serverless or long-running runtimes, suggests where workflow and task decorators belong, and verifies traces appear in Monte Carlo. Always asks before editing any file. Trigger by asking to "instrument my agent" or "set up Monte Carlo tracing".

## [1.10.5] - 2026-05-11

### Changed

- 1b2f114 fix(hooks): replace lib symlinks with real file copies (#82)
- 39c4dd6 AI-256: analyze-root-cause runs TSA first when an incident UUID is present (#79)

## [1.10.3] - 2026-05-06

### Changed

- Internal tracking only: MCP route updated to `/mcp/toolkit`.

## [1.10.2] - 2026-05-05

### Changed

- Correct `alert_assessment` output field descriptions in automated-triage skill: replace the stale "natural-language summary" reference with explicit `alert_description` (what happened) and `triage_summary` (scoring reasoning) fields, and clarify that `alert_description` is used in triage comments for untroubleshot alerts.

## [1.10.1] - 2026-04-30

### Changed

- Version sync with claude-code (welcome-hook removal). No functional changes here.

## [1.10.0] - 2026-04-28

### Added

- **Workflow 4 (sandbox build)** in the Prevent skill — parses `profiles.yml`, classifies the active database as personal/dev/shared-dev/prod/unknown, detects hard-coded `database:` kwargs in model `{{ config() }}` blocks, and runs `dbt build --select <model>`. Hard-stops against shared prod. Skipped automatically for YAML-only diffs.
- **Workflow 5 (execute validation)** in the Prevent skill — substitutes `<YOUR_DEV_DATABASE>` with the user-confirmed value, shows the full execution plan (including any literal prod databases referenced for parity checks), enforces read-only before execution, runs each query via Snowflake MCP, and produces ✅/⚠️/🔴 per-query verdicts plus a consolidated summary. All execution-time scratch output lives under `validation/run/`.
- **Five new sandbox helper scripts** under `skills/prevent/scripts/sandbox/`: `parse_profiles.py`, `classify_sandbox.py`, `detect_hardcoded_db.py`, `substitute_placeholders.py`, `readonly_check.py`. All independently tested and composable via CLI-emitted JSON.
- **Session markers** `MC_BUILD_RAN` and `MC_VALIDATE_RAN` for hook coordination across the new workflows.

### Note

This plugin does not yet expose a slash-command for the Prevent skill. Users can trigger Workflows 4 and 5 by asking natural-language prompts like "build my model into sandbox and run the validation queries". A slash-command surface may be added in a later release.

### Changed

- Workflow 3 (generate validation queries) now always ends by offering the run-validation next step, regardless of how it was triggered.

## [1.9.0] - 2026-04-27

### Changed

- Slim the prevent skill: delegate Workflow 1 (table health check) to `monte-carlo-asset-health` and Workflow 6 (add monitor) to `monte-carlo-monitoring-advisor`. Remove the alert-triage workflow entirely.
- Renumber the impact-assessment and validation-query workflows to W2 and W3. Workflow numbers 4 and 5 are reserved for sandbox-build and execute-validation steps from the in-flight `mc-validate run` work.
- Single-line `description` field in `skills/prevent/SKILL.md` per the ≤250-char authoring rule.
- Drop alert-mutation tools (`updateAlert`, `setAlertOwner`, `createOrUpdateAlertComment`) from the prevent skill's MCP tool table — those belong to the incident-response peer skill.

### Fixed

- Clear the `MC_MONITOR_GAP` cache marker after the post-edit / pre-commit prompt has been delivered, so subsequent prompts don't re-nag for the same gap (Python hooks and OpenCode TS hooks).

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
