# Changelog

All notable changes to the Monte Carlo Agent Toolkit plugin for Snowflake Cortex Code will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.13.0] - 2026-06-15

### Added

- Snowflake Cortex Code plugin (`plugins/cortex-code/`) — the 6th supported editor. Cortex Code wraps Claude Code, so it ships all 17 skills, the full prevent hook lifecycle, slash commands, and the Monte Carlo MCP server; install via `plugins/cortex-code/scripts/install.sh`.

### Changed

- Hardened the prevent impact-check gate: the pre-edit deny reason no longer contains a string that satisfies its own marker scanner, closing a latent self-unlock on harnesses that persist hook output back into the scanned transcript. Added `table_name` path sanitization for the `/tmp` cache, an unknown-transcript-format fail-closed guard, and tolerance for stray bytes when scanning Cortex's `.history.jsonl`. These shared-lib changes apply to all editor plugins.
- Skill-usage telemetry stores its install/session IDs under Cortex Code's own config home (`~/.snowflake/cortex/mc-agent-toolkit`) rather than `~/.claude` — a toolkit install in Cortex Code is a distinct installation from one in Claude Code, so each editor keeps its own identity. The beacon payload now also carries a `harness` field (`cortex-code`) so the telemetry sink can tell editors apart.
