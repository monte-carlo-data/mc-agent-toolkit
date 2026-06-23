# Changelog

All notable changes to the Monte Carlo Agent Toolkit plugin for Snowflake Cortex Code will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.13.3] - 2026-06-23

### Changed

- efef342 feat(copilot): bake toolkit headers via `copilot mcp add` (un-defer Copilot)
- 5705a06 fix(codex): installer owns the monte-carlo-mcp block (migrate url on reinstall)
- aef03e6 fix(codex): read toolkit version from source manifest when baking headers
- ac121c0 fix(opencode): inject MCP headers via config hook instead of {file:} (fail-open)
- 532c473 feat(cursor): bake toolkit install id + version into mcp.json at install
- da46291 feat(codex): bake toolkit install id + version into config.toml http_headers
- 8d873cb feat(telemetry): add shared toolkit-ids.sh for consistent install_id generation
- 6bb5543 feat(opencode): attach toolkit install id + version headers via {file:} substitution
- bd632f5 feat(opencode): persist toolkit_version for {file:} header substitution
- 6cb838c feat(cortex-code): stamp toolkit headers on authed MCP traffic via headersHelper
- 0bc26e6 feat(claude-code): stamp toolkit headers on authed MCP traffic via headersHelper
- 5003aa0 feat(cortex-code): ensure-toolkit-ids writes version + seeds MCP headers helper
- 3768ea9 feat(claude-code): ensure-toolkit-ids writes version + seeds MCP headers helper
- 66f8de8 feat(telemetry): add mcp-headers-helper.py for MCP header injection

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
