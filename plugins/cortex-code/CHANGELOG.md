# Changelog

All notable changes to the Monte Carlo Agent Toolkit plugin for Snowflake Cortex Code will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.16.0] - 2026-07-21

### Added

- monitoring-advisor: Performance pillar baseline monitor set in the agent-metric-monitor reference — p50+p95 latency anomaly, p50+p95 token anomaly, daily token SUM, status_code error-level anomaly, and a measured-p95 latency SLO threshold, with per-backend gating and shared defaults (daily schedule, agent tag, draft-capable) (AI-646)
- monitoring-advisor: documented `tags` and `is_draft` (un-draft-on-edit footgun) on create_or_update_agent_metric_monitor; routing rows for performance-coverage asks

## [1.15.2] - 2026-07-20

### Changed

- monitoring-advisor: conversation-grain evaluation guidance updated for the AI-636 backend change — Snowflake Cortex and Databricks Genie agents now support `is_agent_conversation_aggregation` (Databricks MLflow agents remain span-only); added Genie no-token/model caveats to the metric guidance and a `backend_class` capability note to agent-monitor-creation

## [1.15.1] - 2026-07-20

### Changed

- troubleshoot-agent-traces: the direct (no-alert) path resolves the exact backend from `get_agent_metadata`'s new `backend_class` field instead of asking the user / splitting on `sourceType` (AI-635; a null `backend_class` — older server or unclassifiable agent — still falls back to asking)
- monitoring-advisor, troubleshoot-agent-traces, instrument-agent: `get_agent_metadata` field docs gain `backend_class`

## [1.15.0] - 2026-07-19

### Added

- New `troubleshoot-agent-traces` skill (`/monte-carlo-troubleshoot-agent-traces`): investigates AI-agent alerts (evaluation, metric, trajectory, validation) and agent traces/conversations. Kicks off the trace troubleshooting agent in parallel (`run_troubleshooting_agent`), identifies the agent's backend exclusively from the new `get_alert_agent_classification` tool (server-side classification — never name/MCON heuristics), and routes to per-alert-type and per-backend investigation playbooks (ClickHouse OTel, Snowflake Cortex, Databricks Genie, customer OTel trace table, Databricks MLflow SDK, MLflow Knowledge Assistant).

### Changed

- analyze-root-cause, incident-response, and context-detection route agent-monitor alerts to the new skill; monitoring-advisor's "investigating agent traces" trigger moved there (it keeps monitor creation).

## [1.14.0] - 2026-07-03

### Changed

- Refresh agent monitor references to match the current tool contract: single `agent` reference source (no `dw_id`/`data_source`), required `warehouse` for metric/evaluation/validation, `schedule_type` limited to `fixed`/`manual` with per-type interval floors, and `agent_span_filters` capped at one filter object.
- Agent monitor warehouse is now sourced from `get_agent_metadata`'s `warehouse_uuid`/`warehouse_name` (show the name, pass the uuid; fall back to `get_warehouses` only when both are null).
- Evaluation reference: correct predefined transform functions (`output_length`, `json_validity`, `keywords`), typed custom transforms (`custom_prompt`/`custom_sql` with camelCase `outputType`/`sqlExpression`), boolean-output alerting via `TRUE_RATE`/`FALSE_RATE`, and removal of unsupported `classification`/`sentiment`.
- Metric reference: full agent metric catalog, `NEQ` operator, operator/threshold rules, `ROW_COUNT_CHANGE` and trace-aggregation constraints.
- Validation reference: `negated`-flag negation (no `not_equal`/`not_null`), UNARY `value` vs BINARY `left`/`right`, numeric `status_code`.
- Trajectory reference: `SPAN_OCCURRENCE` and `SPAN_RELATION` conditions, OR-only combination, occurrence count floors, `spanField` hierarchy, and the negated-relation pattern for a missing step.
- Span-field reference: add `parent_span_id`, `model_name`, `status_code`, `is_tool_call`, `is_llm_call`, `has_prompts`, `has_completions` and the platform-vs-OpenTelemetry availability caveat.

## [1.13.3] - 2026-06-23

### Changed

- Authenticated Monte Carlo MCP requests now carry the toolkit's anonymous install id (`x-mcd-toolkit-install-id`) and version (`x-mcd-toolkit-version`) as HTTP headers, so the anonymous usage-beacon stream can be joined to authenticated MCP activity server-side — no new user- or account-level identifier is introduced. Headers are injected by whatever mechanism each editor supports: a runtime headers helper in Claude Code and Cortex Code (which also send a per-session `x-mcd-toolkit-session-id`), and install-time MCP registration for Cursor, Codex, Copilot, and OpenCode. Fail-open and honors `MC_AGENT_TOOLKIT_TELEMETRY_DISABLED=1`.

## [1.13.2] - 2026-06-19

### Changed

- Skills now route Monte Carlo MCP tool calls explicitly to the plugin-bundled server. Every skill that uses Monte Carlo MCP tools carries a standard routing rule directing the model to the fully-qualified `mcp__plugin_mc-agent-toolkit_monte-carlo-mcp__<tool>` names, so a separately-configured server of the same name can no longer shadow the bundled one. Soft (model-compliance) enforcement, with the canonical rule documented as the single source of truth in `.claude/rules/skills.md`.

### Fixed

- Corrected the MCP pre-approval grant in Claude Code and Cortex Code `settings.json` (`…_monte-carlo__*` → `…_monte-carlo-mcp__*`) so it matches the bundled server's actual tool namespace and suppresses permission prompts as intended.
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
- Skill-usage telemetry stores its install/session IDs under Cortex Code's own config home (`~/.snowflake/cortex/mc-agent-toolkit`) rather than `~/.claude` — a toolkit install in Cortex Code is a distinct installation from one in Claude Code, so each editor keeps its own identity. The beacon payload now also carries a `harness` field (`cortex-code`) so the telemetry sink can tell editors apart.
