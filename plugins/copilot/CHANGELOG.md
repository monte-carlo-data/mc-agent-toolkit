# Changelog

All notable changes to the Monte Carlo Agent Toolkit plugin for Copilot CLI will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
