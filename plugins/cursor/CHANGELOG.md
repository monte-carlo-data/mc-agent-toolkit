# Changelog

All notable changes to the Monte Carlo Prevent plugin for Cursor will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-04-02

### Added

- Initial Cursor adapter for Monte Carlo Prevent
- Hook-based enforcement for dbt model edits (pre-edit gate, post-edit accumulator, turn-end validation prompt, commit gate)
- `/mc-validate` command for explicit validation
- Monte Carlo MCP server wiring
- Shared platform-agnostic hook logic via `hooks/prevent/lib/`
