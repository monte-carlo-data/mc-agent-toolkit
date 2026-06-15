# Changelog

All notable changes to the Monte Carlo Agent Toolkit plugin for Snowflake Cortex Code will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.12.0] - 2026-06-15

### Added

- Initial Monte Carlo Agent Toolkit plugin for Snowflake Cortex Code (Cortex Code CLI). Cortex Code wraps Claude Code, so the plugin ships the same skills, slash commands, and the `monte-carlo-mcp` server, installable via `cortex plugin install`.
- All 17 data-observability skills (asset health, incident response, monitoring advisor, prevent, push ingestion, storage cost analysis, and more).
- Prevent enforcement hooks ported to Cortex's full hook lifecycle, including a Cortex-specific transcript reader that scans the `<id>.history.jsonl` session log for impact-assessment markers.
