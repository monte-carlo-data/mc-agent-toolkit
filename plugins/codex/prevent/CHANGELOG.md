# Changelog — mc-prevent (Codex)

## v1.0.0 (2026-04-02)

- Initial Codex plugin for Monte Carlo Prevent
- Shared core library with thin Codex adapters
- Hook support: PreToolUse (Edit|Write, Bash), PostToolUse (Edit|Write), Stop
- Note: Edit|Write matchers are wired for forward compatibility (Codex currently only emits PreToolUse/PostToolUse for Bash)
