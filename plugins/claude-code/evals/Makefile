# Skill Evals Makefile
#
# Parameters:
#   SKILL     (required)  Skill directory name (e.g. monitoring-advisor, prevent)
#   ENV       (optional)  MCP environment for live evals: dev|prod (default: dev)
#   PARALLEL  (optional)  Number of concurrent workers for live evals (default: 1)
#
# Examples:
#   make trigger-evals SKILL=monitoring-advisor
#   make live-evals SKILL=monitoring-advisor
#   make live-evals SKILL=monitoring-advisor ENV=prod PARALLEL=5
#   make dry-run SKILL=monitoring-advisor
#   make evals SKILL=monitoring-advisor

ENV ?= dev
PARALLEL ?= 1

ifndef SKILL
$(error SKILL is required. Usage: make <target> SKILL=<skill-name>)
endif

# -- Trigger evals -----------------------------------------------
# Validates skill trigger accuracy against realistic prompts
trigger-evals:
	uv run python run_evals.py --skill $(SKILL)

# -- Live evals --------------------------------------------------
# Runs prompts through claude-agent-sdk, scores with deterministic checks + LLM judge
live-evals:
	uv run python run_live_evals.py --skill $(SKILL) --env $(ENV) --parallel $(PARALLEL)

# -- Combined ----------------------------------------------------
evals: trigger-evals live-evals

# -- Utilities ----------------------------------------------------
# Validate eval cases without calling any APIs
dry-run:
	uv run python run_evals.py --skill $(SKILL) --dry-run
	uv run python run_live_evals.py --skill $(SKILL) --dry-run

# Install/sync dependencies
sync:
	uv sync

.PHONY: trigger-evals live-evals evals dry-run sync
