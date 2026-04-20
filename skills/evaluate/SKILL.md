---
name: monte-carlo-evaluate
description: Scaffold evaluation suites for AI agents — init configs, bootstrap test cases by synthesizing from agent source and extracting from existing tests, promote approved cases. Later slices add eval runs and regression detection.
when_to_use: |
  Activate whenever tests/eval/eval-config.yaml exists at or above the
  current working directory, OR when the user explicitly asks to set up,
  init, scaffold, or bootstrap evals for an AI agent (trigger phrases:
  "set up eval agent", "init eval agent", "add evals to this agent",
  "scaffold evals for <agent>", "create a test suite for this agent",
  "bootstrap test cases"). Also activate when the user asks to evaluate
  an agent's behavior, run golden cases or test cases, or (slice 3+)
  diagnose why a case regressed. Do NOT activate for non-agent repos —
  dbt projects, infra repos, ad-hoc SQL — even if the user says
  "help me evaluate this" or "let's run some tests". If
  tests/eval/eval-config.yaml is absent and no setup phrasing is
  present, do nothing.
version: 1.0.0
---

# Monte Carlo Evaluate Skill

This skill scaffolds per-agent evaluation suites for AI agents. It sets up the directory layout, writes an `eval-config.yaml` and an `invoke.py` stub, bootstraps an initial set of test cases by synthesizing from the agent's source and extracting from existing tests, and supports promoting approved cases from a draft area into the committed suite.

The product's full design — schema, architecture, slice boundaries — lives in `SPEC.md` (next to this file). This `SKILL.md` is the router: it decides when to engage and dispatches to workflow-specific reference files.

Reference files live next to this file. **Use the Read tool** (not MCP resources) to access them:

- Init flow (question-driven config creation): `references/init.md`
- Bootstrap flow (synthesize from source + extract from tests): `references/bootstrap.md`
- Promote flow (`_draft/` → `cases/`): `references/promote.md`
- Case YAML schema and validation rules: `references/schema.md`

Slice-2 (run, diagnose) and slice-3 (baseline) references are not present yet.

---

## When to activate this skill

Two distinct activation modes. The `when_to_use` frontmatter field captures the triggers; this section describes what to do in each mode once triggered.

### Mode A — normal operation (config exists)

If `tests/eval/eval-config.yaml` exists at or above the current working directory, the user's agent repo already has Eval Agent set up. This mode covers bootstrap, review, promote, and (in later slices) run, diagnose, and baseline operations.

Before acting, run **Agent scope confirmation** below. Never assume which agent is in scope from cwd alone.

### Mode B — setup (config does not exist)

If the user's intent is unmistakably to set up Eval Agent for an agent that does not yet have a config, engage the init flow (`references/init.md`).

Trigger phrases include:

- "set up eval agent"
- "init eval agent"
- "add evals to this agent"
- "scaffold evals for <agent>"
- "create a test suite for this agent"
- "bootstrap test cases for <agent>"

In Mode B, confirm the target agent and the `source_paths` / `reference_paths` before writing any files. Init is not destructive but must not guess.

---

## When NOT to activate this skill

Do not activate for:

- Non-agent repos (dbt projects, infra repos, ad-hoc SQL). Engineers use this toolkit across many repo types; most are not AI agents. "Evaluate this query" in a dbt repo or "run the tests" in an infra repo is NOT a trigger.
- Ambiguous phrasings in any repo that lacks `tests/eval/eval-config.yaml` (e.g., "help me evaluate this", "let's run some tests") — unless paired with explicit setup language from Mode B above.
- Agent repos with an existing config where the user is editing unrelated files. Wait for the user to invoke the skill, or for the user's request to name an eval-related action (run, bootstrap, diagnose, baseline).

When in doubt, stay silent. A non-activation is cheap; a wrong activation that writes files into someone's repo is not.

---

## Agent scope confirmation

Monorepos (like Monte Carlo's `ai-agent` repo) contain multiple agents side-by-side with inconsistent directory structures. Always confirm which agent is in scope before any operation — read, synthesize, write, or run.

### Confirmation rules (in order)

1. **If the user specifies an agent explicitly** ("set up evals for `chat`", "run the bootstrap for `pr_agent`"), use that.
2. **Else, walk up from cwd to find `tests/eval/eval-config.yaml`.** If found, the agent whose root contains that config is the scope. The agent root is the directory that contains `tests/eval/`, not `tests/eval/` itself.
3. **If multiple configs exist at or below cwd**, list them and ask which one.
4. **If no config exists at or above cwd but configs exist elsewhere in the repo**, list those candidates and ask. This is the common footgun in `ai-agent`: an engineer working in `ai-agent/tests/ai_agent/chat/` (the existing test tree) walks up and never hits the eval config, which lives in a parallel tree at `ai-agent/ai_agent/chat/tests/eval/eval-config.yaml`. Surface the right config rather than concluding "no setup."

### Before writing

For Mode B (setup), also confirm `source_paths` and `reference_paths` with the user before writing config. Do not infer from repo structure alone. Detected candidates are starting points for discussion, not defaults.

**Rule of thumb: when in doubt, ask.** A wrong-agent scaffold is worse than a slightly slower conversation.

---

## Behaviors index

Each behavior below maps to a reference file with the detailed procedure. Reference files for deferred slices are not yet present — do not attempt to run those behaviors.

| Behavior                  | Slice | Reference                  |
| :------------------------ | :---- | :------------------------- |
| Setup / init flow         | 1     | `references/init.md`       |
| Bootstrap (synthesize + extract → `_draft/`) | 1     | `references/bootstrap.md`  |
| Promote (`_draft/` → `cases/`) | 1 | `references/promote.md`    |
| Schema validation of case YAMLs | 1 | `references/schema.md`    |
| Run evals                 | 2     | (deferred)                 |
| Diagnose regressions      | 3     | (deferred)                 |
| Baseline show / set       | 3     | (deferred)                 |

---

## Scope of bootstrap operations

Bootstrap is a hard-constrained operation. It reads ONLY the files declared in `eval-config.yaml`:

- `source_paths` — agent source (system prompts, tool definitions) used for synthesis.
- `reference_paths` — existing tests, docstrings, README examples used for extraction.

Bootstrap does **not** scan the rest of the repo. It does **not** follow imports. It does **not** traverse arbitrary files. In a messy monorepo, wide scanning produces garbage cases.

`source_paths` and `reference_paths` are relative to the agent root but may traverse outside it (e.g., `../../../tests/ai_agent/<agent>/test_foo.py`) to accommodate repos where agent source and tests live in different trees. Honor those escapes without second-guessing.

---

## Synthesis warning (required)

After every bootstrap synthesis pass, present this warning to the user verbatim — not paraphrased, not omitted even for small case counts:

> These are a starting point. Synthesized cases cover what your code *says* the agent does — they miss the weird failures that actually break agents. Expand the suite as you discover real failure modes.

This is a requirement, not a nicety. Users who skip past synthesized cases will conclude "the tests pass" means more than it does.

---

## Explicitly deferred

These capabilities are intentionally out of scope. Do not synthesize them on the fly:

- **Proactive triggering on agent file changes.** The skill does not volunteer "I noticed you modified `prompts/chat_system.md` — want to re-run bootstrap?" Engineers invoke explicitly.
- **Pre-commit / pre-push hooks.** Evals are slow, non-deterministic, and cost real money. They are not a commit gate.
- **Production trace ingestion.** Eval Agent's flywheel (production failures → candidate cases) is gated on Agent Monitoring maturity and is a post-POC concern. See SPEC.md §15.

For the full deferred list and the slice boundaries, read `SPEC.md` in this directory.
