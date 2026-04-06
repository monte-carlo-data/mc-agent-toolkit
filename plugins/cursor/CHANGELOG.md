# Changelog

All notable changes to the Monte Carlo Agent Toolkit plugin for Cursor will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-04-06

### Changed

- Restructure from per-skill `mc-prevent` plugin to unified `mc-agent-toolkit` plugin
- Plugin directory is now `plugins/cursor/` (was `plugins/cursor/prevent/`)
- Hooks namespaced under `hooks/prevent/` for multi-skill support
- Shared hook logic moved to `plugins/shared/prevent/lib/`

### Upgrade instructions

Existing users should re-run the install script to pick up the new structure:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/monte-carlo-data/mcd-agent-toolkit/main/plugins/cursor/scripts/install.sh)
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
