# Skill Trigger Evals

Trigger accuracy evals for mc-agent-toolkit skills. Each eval set verifies that a skill's description correctly causes it to activate (or not) for realistic user prompts.

## Setup

```bash
# 1. Install dependencies (creates .venv automatically)
uv sync

# 2. Set your API key — copy the example and fill it in
cp .env.example .env
# edit .env with your key

# 3. If using direnv, allow it (picks up .env + .venv automatically)
direnv allow
```

## Running evals

```bash
# Run a specific skill's evals
uv run python run_evals.py --skill monitoring-advisor
uv run python run_evals.py --skill prevent
uv run python run_evals.py --skill push-ingestion

# Dry-run (validate cases without calling the API)
uv run python run_evals.py --skill monitoring-advisor --dry-run

# Options
#   --model      Claude model to use as judge (default: claude-sonnet-4-6)
#   --threshold  Minimum pass rate to exit 0   (default: 0.85)
#   --evals      Path to eval cases JSON       (default: <skill>/trigger-evals.json)
```

## Adding eval cases

Edit `<skill>/trigger-evals.json` and add an entry to the `cases` array:

```json
{
  "id": "should-16",
  "prompt": "...",
  "expected": "trigger",
  "rationale": "Why this should trigger"
}
```

Use `should-XX` IDs for trigger cases and `should-not-XX` for no-trigger cases.

## Adding evals for a new skill

1. Create `<skill-name>/trigger-evals.json` following the schema in existing eval files
2. Run `uv run python run_evals.py --skill <skill-name> --dry-run` to validate
3. Run the full eval to confirm pass rate meets threshold
