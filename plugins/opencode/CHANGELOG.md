# Changelog

All notable changes to the Monte Carlo Agent Toolkit plugin for OpenCode will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.13.2] - 2026-06-19

### Changed

- Skills now route Monte Carlo MCP tool calls explicitly to the plugin-bundled server. Every skill that uses Monte Carlo MCP tools carries a standard routing rule directing the model to the fully-qualified `mcp__plugin_mc-agent-toolkit_monte-carlo-mcp__<tool>` names, so a separately-configured server of the same name can no longer shadow the bundled one. Soft (model-compliance) enforcement, with the canonical rule documented as the single source of truth in `.claude/rules/skills.md`.

### Fixed

- Replaced obsolete Monte Carlo tool-namespace examples (`mcp__monte_carlo__getAlerts`, `mcp__mc__search`) in the remediation skill's tool-discovery reference with current plugin-bundled, snake_case names.

## [1.13.1] - 2026-06-18

### Added

- `Toolkit Installed` telemetry beacon, fired once per machine+editor **per toolkit version** — on first install and after each version change — independent of skill usage, closing the gap where an install that never invoked a skill was invisible and adding version-adoption signal. Deduped by a per-editor `beacon_sent_version` marker. Wired across all six editor plugins (Claude Code, Cortex Code, Cursor, Codex, Copilot, OpenCode). Fail-open and non-blocking; honors `MC_AGENT_TOOLKIT_TELEMETRY_DISABLED=1` and the `MCD_TOOLKIT_BEACON_URL` override.

### Changed

- Shared hook logic now also covers telemetry: the canonical install beacon lives in `plugins/shared/telemetry/lib/` and is synced into each editor plugin by `./scripts/bump-version.sh --sync-only`, with a CI check enforcing it stays in sync — mirroring the existing `prevent/lib` convention.

## [1.13.0] - 2026-06-15

### Added

- Snowflake Cortex Code plugin (`plugins/cortex-code/`) — the 6th supported editor. Cortex Code wraps Claude Code, so it ships all 17 skills, the full prevent hook lifecycle, slash commands, and the Monte Carlo MCP server; install via `plugins/cortex-code/scripts/install.sh`.

### Changed

- Hardened the prevent impact-check gate: the pre-edit deny reason no longer contains a string that satisfies its own marker scanner, closing a latent self-unlock on harnesses that persist hook output back into the scanned transcript. Added `table_name` path sanitization for the `/tmp` cache, an unknown-transcript-format fail-closed guard, and tolerance for stray bytes when scanning Cortex's `.history.jsonl`. These shared-lib changes apply to all editor plugins.

## [1.12.1] - 2026-06-17

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

- **`/mc-validate run` subcommand** — extends the Monte Carlo Prevent skill's validation workflow to actually execute the generated queries. `/mc-validate` alone still generates the validation SQL as before; `/mc-validate run` additionally builds the changed model into your dev database (`dbt build --select <model>`) and runs the validation queries through the Snowflake MCP, reporting per-query verdicts against each query's "What to look for" guidance.
- **Workflow 4 (sandbox build)** in the Prevent skill — parses `profiles.yml`, classifies the active database as personal/dev/shared-dev/prod/unknown, detects hard-coded `database:` kwargs in model `{{ config() }}` blocks, and runs `dbt build --select <model>`. Hard-stops against shared prod. Skipped automatically for YAML-only diffs.
- **Workflow 5 (execute validation)** in the Prevent skill — substitutes `<YOUR_DEV_DATABASE>` with the user-confirmed value, shows the full execution plan (including any literal prod databases referenced for parity checks), enforces read-only before execution, runs each query via Snowflake MCP, and produces ✅/⚠️/🔴 per-query verdicts plus a consolidated summary. All execution-time scratch output lives under `validation/run/`.
- **Five new sandbox helper scripts** under `skills/prevent/scripts/sandbox/`: `parse_profiles.py`, `classify_sandbox.py`, `detect_hardcoded_db.py`, `substitute_placeholders.py`, `readonly_check.py`. All independently tested and composable via CLI-emitted JSON.
- **Session markers** `MC_BUILD_RAN` and `MC_VALIDATE_RAN` for hook coordination across the new workflows.

### Changed

- Workflow 3 (generate validation queries) now always ends by offering `/mc-validate run` as the next step, regardless of how it was triggered.

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
