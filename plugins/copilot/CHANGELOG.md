# Changelog

All notable changes to the Monte Carlo Agent Toolkit plugin for Copilot CLI will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.6.1] - 2026-04-17

### Changed

- d8f0509 chore(automated-triage): bump version to 1.1.1
- 580ece7 feat(automated-triage): add mark_event_as_normal guidance and scope interactive triage by domain/audience
- 5d75040 Add Connection Auth Rules skill (#51)
- 48f1322 feat(automated-triage): add interactive triage mode and action guard (AI-192) (#54)

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

## [1.0.0] - 2026-04-06

Initial release of the Monte Carlo Agent Toolkit plugin for GitHub Copilot CLI.

### Features

- **MC Prevent** — change impact assessment gate, edit tracking, pre-commit validation prompt, and cache state management at agent stop
- Hook-based enforcement using Copilot CLI's `preToolUse`, `postToolUse`, and `agentStop` events
- Monte Carlo MCP server bundled via `.mcp.json`
- Native Copilot CLI plugin format (`plugin.json`, `hooks.json` with `version: 1`)
- Skills discovered automatically by Copilot CLI
