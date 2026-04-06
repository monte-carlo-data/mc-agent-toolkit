# Changelog

## 1.0.0 — 2026-04-06

Initial release of the Monte Carlo Agent Toolkit plugin for VS Code / GitHub Copilot.

### Features

- **MC Prevent** — change impact assessment gate, edit tracking, pre-commit validation prompt, and turn-end validation reminder
- Hook-based enforcement using VS Code Copilot's `PreToolUse`, `PostToolUse`, and `Stop` events
- Monte Carlo MCP server bundled via `.mcp.json`
- Native Copilot agent plugin format (`plugin.json`, `hooks.json` at root)
- Skills discovered automatically by Copilot
