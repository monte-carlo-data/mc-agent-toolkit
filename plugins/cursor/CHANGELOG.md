# Changelog

All notable changes to the Monte Carlo Agent Toolkit plugin for Cursor will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.11.0] - 2026-05-07

### Added

- **`instrument-agent` skill (AO-427)** — walks an MC Agent Observability customer through instrumenting a new AI agent in their Python codebase. Detects AI libraries (LangChain/LangGraph, OpenAI, Anthropic, CrewAI, Bedrock, SageMaker, Vertex AI, plus the long tail of SDK-supported instrumentors via live PyPI fetch), classifies the runtime as serverless or long-running, and proposes the appropriate `mc.setup()` template (with `SimpleSpanProcessor` for Lambda) plus `@trace_with_workflow` / `@trace_with_task` decorator placements. Always asks before editing any file (deps, source, env). Includes:
  - The skill itself, mounted via the editor's standard skill discovery.
  - Seven Tier-3 references — workflow, library detection, setup template, decorator placement, verify traces, redaction, troubleshooting.
  - Three helper scripts — `detect_libraries.py` (parse deps, detect serverless, detect existing setup), `fetch_sdk_docs.py` (live-fetch from GitHub README + PyPI metadata, fall back to local snapshot), and `instrumentor_map.json` (snapshotted last-known-compatible pins with stale-data warnings).
  - 21 trigger evals (11 should + 10 should-not, including 3 lifted verbatim from monitoring-advisor for bidirectional routing) and 6 live-behavior evals covering silent-edit guardrails, endpoint normalization, serverless detection, and before/after `get_agent_metadata` verification.
  - 57 helper-script smoke tests against 11 fixtures (real LangGraph agent + Lambda variant).
- **Bidirectional routing contract with `monitoring-advisor`** — three new should-not cases in `monitoring-advisor/trigger-evals.json` lock the boundary: `instrument-agent` PRODUCES traces, `monitoring-advisor` CONSUMES them.
- **`Agent instrumentation` Conversation Signal** in `context-detection/references/signal-definitions.md` routes prompts like *"instrument my agent"* / *"set up Monte Carlo tracing"* / *"setting up an agent"* to the new skill.
- **Upstream `montecarlo-opentelemetry` README contributions** ([#22](https://github.com/monte-carlo-data/montecarlo-opentelemetry/pull/22), [#23](https://github.com/monte-carlo-data/montecarlo-opentelemetry/pull/23)) documenting `mc.setup(span_processor=...)` for serverless / suspendable runtimes and the `MCD_DEFAULT_*` auth-header behavior with custom span processors. The `instrument-agent` skill cites the upstream README as source of truth for the kwarg contract instead of carrying SDK knowledge in-skill.

### Fixed

- `instrument-agent`: dedupe shared instrumentor packages in `suggested_instrumentors` so projects with both `langchain` and `langgraph` (which share `opentelemetry-instrumentation-langchain`) don't propose the same package twice in the install set or wire the same instrumentor twice in `mc.setup()`.
- `instrument-agent` serverless template: pass `MCD_DEFAULT_*` headers explicitly to `OTLPSpanExporter` when using a custom `span_processor`. `mc.setup()` only auto-injects those headers when it constructs the default exporter; with a custom `span_processor`, the customer builds the exporter and is responsible for headers. Surfaced by upstream README review on `montecarlo-opentelemetry#22`.
- `instrument-agent`: propose pinned versions in the dependency diff. `detect_libraries.py`'s `suggested_instrumentors` output now passes through `version_constraint` and a new `additional_pins` field; the workflow's step-6 deps proposal applies both. `instrumentor_map.json` declares `wrapt<2` as a transitive pin for the OpenLLMetry instrumentors at `<=0.53.4` (they pass `module=` to `wrap_function_wrapper`, which `wrapt` 2.x renamed to `target=` — without the pin, `mc.setup()` raises `TypeError` at import time). Surfaced by e2e testing.
- `instrument-agent` `existing_setup` detection: tighten `_detect_existing_setup` to require both an SDK import AND an actual `mc.setup(...)` / `montecarlo_opentelemetry.setup(...)` call in the same file. Previously, files that import `montecarlo_opentelemetry as mc` only to use `@mc.trace_with_workflow` (i.e. handlers, not setup files) were false-positives.
- `instrument-agent` `fetch_sdk_docs.py`: rephrase the GitHub README 404 warning to clarify that PyPI fallback will be used and to hint at `GITHUB_TOKEN` when the SDK repo is private. The previous "Live fetch failed" wording suggested a terminal failure when it's a graceful fallback.
- `instrument-agent` `verify-traces.md`: document local verification with `otel-desktop-viewer` (or any local OTLP receiver) as an optional pre-MC sanity check, with a note that the published Docker image's JSON-RPC API may lag the repo's `main` branch.
- `instrument-agent` setup templates: enforce the privacy-default-off promise in code. The OpenLLMetry instrumentors at `<=0.53.4` read `TRACELOOP_TRACE_CONTENT` (default `"true"`, content captured) — the env var name `OTEL_INSTRUMENTATION_LANGCHAIN_TRACE_PROMPTS` previously documented in the templates and `redaction.md` does not exist in those instrumentors. Templates now set `os.environ.setdefault("TRACELOOP_TRACE_CONTENT", "false")` before the instrumentor imports, so the privacy default is a code guarantee. Customers opt in by exporting `TRACELOOP_TRACE_CONTENT=true`. Surfaced empirically: the e2e test trace included `gen_ai.prompt.0.content` and `gen_ai.completion.0.content` despite the template's "prompts disabled" comment.

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
