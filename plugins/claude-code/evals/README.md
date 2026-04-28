# Skill Evals

Trigger accuracy and live behavior evals for mc-agent-toolkit skills.

- **Trigger evals** verify a skill's description correctly activates (or not) for realistic prompts
- **Live evals** run prompts through the real Claude Code harness via `claude-agent-sdk`, then score with deterministic checks and an LLM judge

## Setup

```bash
# 1. Install dependencies
uv sync

# 2. Set env vars — copy the example and fill it in
cp .env.example .env
# edit .env with your keys
```

### Prerequisites

- `claude` CLI installed and on PATH
- Python >= 3.11
- `uv` package manager
- `ANTHROPIC_API_KEY` — for both agent and judge
- `MCD_ID_DEV`, `MCD_TOKEN_DEV` — Monte Carlo API credentials for dev (live evals)
- `MCD_ID`, `MCD_TOKEN` — Monte Carlo API credentials for prod (live evals)

## Running evals

```bash
make trigger-evals SKILL=monitoring-advisor
make live-evals SKILL=monitoring-advisor
make live-evals SKILL=monitoring-advisor ENV=prod PARALLEL=5
make dry-run SKILL=monitoring-advisor
make evals SKILL=monitoring-advisor
make sync
```

See `Makefile` for all targets and options.

### MCP isolation

Live evals run with `--strict-mcp-config`, so only the MCP servers declared in
`constants.py` are loaded. Globally-installed MCP servers (e.g. `mc-data-mcp`)
do not leak into the eval environment, keeping runs reproducible across
machines.

### Baseline runs for new skills

When bootstrapping a new skill, you may want to run the eval suite before
`SKILL.md` exists to generate a baseline. Pass `--skip-missing-skill` and the
runner will warn and proceed with empty skill content:

```bash
uv run python run_live_evals.py --skill my-new-skill --skip-missing-skill
```

## Adding eval cases

### Trigger evals

Edit `<skill>/trigger-evals.json`:

```json
{
  "id": "should-16",
  "prompt": "...",
  "expected": "trigger",
  "rationale": "Why this should trigger"
}
```

### Live evals

**Peer skills.** If your skill delegates to other skills via the `Skill` tool
(e.g. `monte-carlo-prevent` → `monte-carlo-asset-health`), declare them at
the top of the YAML so the runner loads their SKILL.md alongside the main
skill's content. Without this, peer skills' instructions never apply during
evals because the eval harness only loads the target skill by default.

```yaml
peer_skills:
  - asset-health
  - monitoring-advisor
cases:
  - id: live-01-...
```

Peer skill SKILL.md files come first in the system prompt; the main skill's
content comes last (so its instructions are most salient). A typo in a peer
name is a hard error.

Edit `<skill>/live-evals-<env>.yaml`. All cases use the `turns` format:

```yaml
# Single-turn
- id: live-06-example
  turns:
    - prompt: "Your prompt here"
      criteria:
        must_call: [get_warehouses]
        must_not_call: [create_table_monitor_mac]
        output_must_not_contain: ["MCON++"]
  criteria:
    judge_rubric: |
      Describe what good output looks like.

# Multi-turn
- id: live-07-multi-turn
  turns:
    - prompt: "First message"
      criteria:
        must_call: [get_warehouses]
    - prompt: "Follow-up"
      criteria:
        must_call: [get_use_cases]
  criteria:
    judge_rubric: |
      Overall rubric for the full conversation.
```

### Scoring

Each case is scored in two layers:

1. **Deterministic checks** (pass/fail): `must_call`, `must_not_call`, `output_must_not_contain`
2. **LLM judge** (0.0-1.0): Scores against the `judge_rubric`

A case passes if all deterministic checks pass AND judge score >= 0.7. Tool names in YAML use short names (e.g. `get_warehouses`); the runner matches via substring against full MCP tool names.

## Adding evals for a new skill

1. Create `<skill-name>/live-evals-dev.yaml` following the format above
2. Run `make dry-run SKILL=<skill-name>` to validate
3. Run `make live-evals SKILL=<skill-name>` to confirm pass rate meets threshold
