# Monte Carlo Agent Toolkit — Codex

Preliminary support for OpenAI Codex. Currently provides skills only — no hooks or enforcement.

## What's available

- **MC Prevent** skill — surfaces Monte Carlo context (lineage, alerts, blast radius) when working with dbt models

## Status

Codex support is preliminary. The skill is available via symlink but there are no hooks, MCP server configuration, or slash commands. Codex relies on the skill instructions alone to guide behavior.

## Setup

Copy the skill into your Codex project:

```bash
cp -r plugins/codex/skills/prevent/ .codex/skills/prevent/
```

Or reference it via `AGENTS.md` in your project.

## Architecture

See the [plugins README](../README.md) for the overall plugin architecture.
