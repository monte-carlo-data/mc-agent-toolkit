# Monte Carlo Evaluate Skill

Scaffold and iterate on evaluation suites for AI agents — from an empty folder to a reviewable set of test cases, without leaving your editor.

## What this does

Eval Agent is Monte Carlo's eval engine for AI agents. This skill is the local-development entry point: it sets up the directory structure, drafts a config, bootstraps initial test cases from the agent's source and existing tests, and lets you promote approved cases into a committed suite.

The current POC scope (slice 1) covers **scaffolding only**:

1. **Init** — question-driven flow that writes `tests/eval/eval-config.yaml` and a stub `tests/eval/invoke.py` under the agent's root.
2. **Bootstrap** — synthesizes candidate test cases from the agent's source (system prompts, tool definitions) and extracts cases from existing tests, docstrings, and examples. Candidates land in `tests/eval/cases/_draft/` for review.
3. **Promote** — moves approved cases from `_draft/` to `tests/eval/cases/`, which is the committed, runnable suite.

Later slices add the eval runtime, baseline comparison, and regression diagnosis. None of those are available yet.

## Design

See `SPEC.md` in this directory for the authoritative product specification — architecture, case schema, config schema, slice boundaries, and open questions. The `SKILL.md` is the router: when the skill engages, SKILL.md decides the flow and dispatches to `references/<flow>.md` for the detailed procedure.

## Activation

The skill activates in two modes:

- **Config exists** — `tests/eval/eval-config.yaml` is present at or above your working directory. The skill handles bootstrap, promote, and (in later slices) run / diagnose / baseline.
- **Setup intent** — you explicitly ask to set up, init, scaffold, or bootstrap evals for an agent. The skill runs the init flow.

The skill does nothing in non-agent repos (dbt projects, infra, etc.) unless you explicitly invoke setup. See SKILL.md for the full activation logic.

## Prerequisites

- Claude Code, Cursor, VS Code, or any editor with skill support
- Python-based agent you can invoke via a simple function call (slice 1 supports Python agents only)

No Monte Carlo account or MCP server is required for slice 1 — the skill is entirely local.

## Setup

### Via the mc-agent-toolkit plugin (recommended)

Install the plugin for your editor — it bundles the skill. See the [main README](../../README.md#installing-the-plugin-recommended) for editor-specific instructions.

### Standalone

```bash
npx skills add monte-carlo-data/mc-agent-toolkit --skill evaluate
```

Or copy directly:

```bash
cp -r skills/evaluate ~/.claude/skills/monte-carlo-evaluate
```

## How to use it

From inside an agent's working directory (or anywhere under it, once the config exists), prompt your editor with:

```
"Set up evals for this agent"

"Bootstrap test cases for the chat agent"

"Promote the partial-refund and p1-outage cases"

"Review the draft cases in tests/eval/cases/_draft/"
```

The skill will confirm the agent's scope (especially in monorepos), ask about source and reference paths, and write files to `tests/eval/` under the agent root. Nothing is written without confirmation.
