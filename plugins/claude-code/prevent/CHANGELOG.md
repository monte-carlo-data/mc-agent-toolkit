# Changelog

All notable changes to the Monte Carlo Prevent plugin will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-04-01

### Changed

- Rename plugin from `mc-safe-change` to `mc-prevent`
- Rename skill from `monte-carlo-safe-change` to `monte-carlo-prevent`
- Reset version to 1.0.0 as a fresh identity

---

*Entries below predate the rename from `mc-safe-change` to `mc-prevent`.*

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

## [1.0.0] - 2026-03-22

- Initial plugin shell with skill file and manifest
