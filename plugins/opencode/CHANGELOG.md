# Changelog

All notable changes to the Monte Carlo Prevent plugin for OpenCode will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-04-02

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
