# Changelog

All notable changes to the Monte Carlo Agent Toolkit plugin for Codex will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
This project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.5.1] - 2026-04-15

### Changed

- Add ctp-config skill for building CTP (Credential Transform Pipeline) configs


## [1.5.0] - 2026-04-15

### Changed

- Add asset-health skill (#33)
- Add AI agent monitoring to monitoring-advisor skill (#48)

## [1.0.0] - 2026-04-02

- Initial Codex plugin for Monte Carlo Agent Toolkit
- Shared core library with thin Codex adapters
- Hook support: PreToolUse (Edit|Write, Bash), PostToolUse (Edit|Write), Stop
- Note: Edit|Write matchers are wired for forward compatibility (Codex currently only emits PreToolUse/PostToolUse for Bash)
