# Eval Agent — Slice 1: Scaffolding (CLAUDE.md)

**Read `SPEC.md` in this directory first.** This brief covers only slice 1 of the Eval Agent POC. `SPEC.md` is the authoritative reference for product decisions, schemas, and cross-slice context.

---

## Mission

Build the scaffolding layer of Eval Agent:
1. The `monte-carlo-evaluate` Claude Code skill in `mcd-agent-toolkit` (folder: `skills/evaluate/`)
2. The init flow (skill-driven, writes `eval-config.yaml` + stub `invoke.py`)
3. The bootstrap flow (skill-native, synthesizes + extracts test cases into `_draft/`)
4. A working promote workflow (skill-assisted or manual file move)
5. End-to-end validation on one real MC agent in the `ai-agent` repo

No CLI work in this slice. No eval runtime, no baseline, no regression detection. Those come in slices 2 and 3.

---

## Scope

### In scope

- Create `monte-carlo-evaluate` skill in `mcd-agent-toolkit/skills/evaluate/`
- Skill activation guard: only engage when `tests/eval/eval-config.yaml` exists at or above cwd (exception: explicit setup requests)
- Skill agent-scope confirmation logic for monorepos
- Init flow: ask engineer questions, write `eval-config.yaml` and stub `invoke.py`
- Bootstrap flow: read agent source + reference artifacts, synthesize + extract candidate cases, write to `tests/eval/cases/_draft/`
- Promote flow: skill moves `_draft/*.yaml` to `cases/*.yaml` on user request; manual `mv` also supported
- Dogfood: pick one MC agent in `ai-agent`, run the full scaffold flow end-to-end
- Schema validation (runtime check on case YAMLs, even though we can't evaluate them yet)

### Explicitly NOT in scope (deferred to later slices)

- Any `montecarlo eval` CLI commands (slice 2)
- Eval runtime — no LLM judge calls, no deterministic scorers (slice 2)
- Template library port (slice 2)
- `baseline.json` and regression detection (slice 3)
- Diagnosis flow ("why did this regress?") (slice 3)
- Scoped runs via `git diff` (slice 2+)
- CLI-native init or bootstrap (post-POC)

If you find yourself reaching for a feature in the "not in scope" list to make slice 1 work, stop and flag it — the slice boundary is intentional.

---

## Prerequisites

### Use Anthropic's `skill-creator` skill

Use Anthropic's `skill-creator` skill to create the `monte-carlo-evaluate` skill. If `skill-creator` is not installed in your Claude Code environment, install it first. Follow `skill-creator`'s conventions for skill structure.

**Critical:** populate the `when_to_use` field of the skill with explicit triggering conditions. Activation is a hard requirement — see "Skill activation guard" below.

### Repos you'll touch

- `mc-agent-toolkit` — all skill code lives here
- `ai-agent` — dogfood target; you'll add files under `tests/eval/` for one agent only

Do **not** modify the `cli` repo in this slice.

---

## Critical behaviors

### Skill activation guard

The skill installs alongside other skills in `mcd-agent-toolkit` (safe-change, pr-review, etc.). It must not fire indiscriminately — engineers use this toolkit across many repo types (dbt, infra, etc.), and most of those aren't agent repos.

Two distinct activation modes:

**Mode A — normal operation (config exists).** Skill engages when `tests/eval/eval-config.yaml` exists at or above the engineer's current working directory. This covers bootstrap, review, promote, and (in later slices) run / diagnose / baseline.

**Mode B — setup (config does not exist).** Skill engages when the user's intent is unmistakably to set up Eval Agent for the first time. Triggering phrases include: "set up eval agent", "init eval agent", "add evals to this agent", "scaffold evals for \<agent\>", "create a test suite for this agent".

In Mode B, the skill should still confirm before doing anything destructive — ask which agent, confirm paths, then write files. The init flow itself is covered in build step 3.

**Non-activation cases:**

- Non-agent repo, no setup intent → do nothing. Don't silently offer setup; let the user ask.
- Non-agent repo, ambiguous phrasing like "help me evaluate this" or "let's run some tests" → do nothing or politely clarify. Do not assume Eval Agent is what the user means.
- Agent repo with existing config, but user is editing unrelated files → do nothing until the user invokes the skill.

**Implementation:** encode both modes in `when_to_use` with clear triggering language. The skill's system prompt should reinforce the scoping — explicitly note that phrases like "evaluate this query" in a dbt repo or "run the tests" in an infra repo are NOT triggers.

### Agent scope confirmation (**IMPORTANT for MC's `ai-agent` repo**)

MC's `ai-agent` repo contains multiple agents in a monorepo, with inconsistent directory structures across agents. Bootstrap must not scan the entire repo or guess which agent the user means.

**Confirmation logic:**

1. If the user specifies an agent explicitly ("set up evals for refund_handler"), use that.
2. Else, walk up from cwd to find the nearest `tests/eval/eval-config.yaml`. If found, that's the agent.
3. If multiple configs exist at or below cwd, list them and ask.
4. If no config exists and the user is initiating setup, ask which agent they want to scaffold. List candidate agent directories if they can be detected, but do not silently pick.
5. Confirm `source_paths` and `reference_paths` with the user before writing config. Do not infer from repo structure alone.

**Rule of thumb: when in doubt, ask.** A wrong-agent scaffold is worse than a slightly slower conversation.

### Scope of bootstrap operations

Bootstrap reads only the files declared in `eval-config.yaml`'s `source_paths` and `reference_paths`. It does not scan the whole repo, does not follow imports, does not traverse arbitrary files. This is a deliberate constraint — in a messy monorepo, wide scanning produces garbage cases.

If paths in config point outside the agent's own directory, honor them (some agents may share prompts with a sibling). Paths are relative to agent root.

---

## Build order

### Step 1: Create skill scaffold

Use `skill-creator`.

- **Skill name** (in SKILL.md `name:` field): `monte-carlo-evaluate`
- **Folder**: `mcd-agent-toolkit/skills/evaluate/`
- **Toolkit reference** (once installed via plugin): `/mc-agent-toolkit:evaluate`

The `monte-carlo-` prefix matches the convention used by the existing `monte-carlo-prevent` skill — individually distributable skills carry the prefix; within the toolkit plugin they are referenced by short name.

Populate `when_to_use` with triggering conditions covering:
- User asks to set up, init, or scaffold evals for an agent
- User asks to evaluate an agent's behavior, run test cases, or run evals
- User asks about the test suite or golden cases for an agent
- User asks to bootstrap, generate, or synthesize test cases
- User asks why a case regressed (slice 3, but good to declare intent now)

Include an explicit non-activation condition: skill does NOT activate when `tests/eval/eval-config.yaml` is not present at or above cwd, unless the user is explicitly requesting setup.

### Step 2: Pick the dogfood target

Survey `ai-agent`. Select one agent to scaffold against using these criteria:

- **Has some test scaffolding to extract from.** Existing unit tests, docstrings with examples, or README examples reduce cold-start friction and let the extraction path have real input.
- **Invocation is relatively clean.** Doesn't require elaborate auth, external database stand-up, or complex fixtures to call once. Agents with a `run(input)` or similar simple entry point are preferred.
- **Under active development.** Dead or rarely-touched agents don't exercise the iteration loop; pick something someone will actually re-run evals against.
- **Output type preference: text or mixed over pure-action.** Testing the LLM-judge path is more valuable for slice validation than only testing deterministic action matching (action matching comes in slice 2).

Confirm your selection with the user before proceeding to step 3. Explain why this agent fits the criteria.

**About `ai-agent`'s structure:**

Relevant layout:
```
ai-agent/
├── ai_agent/
│   ├── pr_agent/          # agent source lives here
│   ├── triage_agent/
│   ├── summarizer/
│   └── ... (not every subfolder is an agent)
└── tests/
    └── ai_agent/
        ├── pr_agent/       # existing tests live here (separate dir)
        └── ...
```

For scaffolding, **follow the canonical layout in SPEC.md §6**: place `tests/eval/` under the agent's own source directory. For example, for `pr_agent`:

- `agent_root`: `ai-agent/ai_agent/pr_agent/`
- Eval scaffold written to: `ai-agent/ai_agent/pr_agent/tests/eval/`
- `source_paths` in config (relative to agent root): `prompts/...`, `tools.py`, etc.
- `reference_paths` can traverse outward to existing tests: `../../../tests/ai_agent/pr_agent/test_foo.py`, etc.

This creates intentional inconsistency with `ai-agent`'s existing test convention (eval tests under agent source, other tests under top-level `tests/`). Accept the inconsistency — consistency across Eval Agent-managed scaffolding matters more than matching the existing repo's layout, and the `reference_paths` escape hatch keeps existing tests reachable.

**Footgun to watch:** if the engineer is working from `ai-agent/tests/ai_agent/pr_agent/` when they invoke the skill, walking up from cwd won't find `tests/eval/eval-config.yaml` (which lives under `ai_agent/pr_agent/`). The skill's "list other configs in the repo" logic (see Agent scope confirmation above, rule 4) handles this — make sure that logic works correctly and surfaces the right config.

### Step 3: Implement init flow

Skill-driven question flow. Asks in order:
1. Agent name (default: directory name)
2. Source paths (for synthesis — system prompts, tool definitions). Prompt with detected candidates; require user confirmation.
3. Reference paths (for extraction — tests, docstrings, README). Same pattern.
4. Output type (text / action / mixed)
5. Which bundled dimensions to enable (stub list for now — real list comes in slice 2)

Writes:
- `<agent_root>/tests/eval/eval-config.yaml` per the schema in SPEC.md §8
- `<agent_root>/tests/eval/invoke.py` — stub with a TODO comment and a docstring matching the invocation contract in SPEC.md §10. Do not attempt to fill it out for the engineer; they own it.
- Creates empty `<agent_root>/tests/eval/cases/` directory

Init is not destructive. If files already exist, ask before overwriting.

### Step 4: Implement bootstrap — extraction pass

Read files in `reference_paths`. For each:
- Unit / integration tests → look for input-output pairs in test assertions
- Docstrings → look for example invocations with expected outputs
- README / docs → look for usage examples

For each extracted case, generate a YAML file in `tests/eval/cases/_draft/` with:
- Filename: slug generated from the case content (e.g., `partial-refund-with-loyalty-discount.yaml`)
- `source: extracted:<file>:<line>` or `extracted:<file>` if line not available
- `input:` or `input_file:` as appropriate (inline if small, `input_file:` if large)
- `reference_output:` populated from the extracted expectation
- `tags:` inferred from context if reasonable; else empty

Extraction should be conservative. If a test's expectation is unclear or the pattern doesn't match, skip it. A few good cases beat many bad ones.

### Step 5: Implement bootstrap — synthesis pass

Read files in `source_paths` (system prompts, tool definitions). Generate ~6–10 candidate cases covering:
- Happy path for stated capabilities
- A couple of edge cases implied by the prompt's constraints
- One or two off-domain inputs (to test refusal / routing behavior)

Each synthesized case:
- Filename: slug from case content
- `source: synthesized:from_system_prompt` or `synthesized:from_tool_definitions` as appropriate
- `reference_output:` may be partial or absent if synthesis isn't confident — don't fabricate confident wrong answers
- `tags:` where clearly applicable

**Warning message required:** after synthesis finishes, the skill must tell the user explicitly:
> "These are a starting point. Synthesized cases cover what your code *says* the agent does — they miss the weird failures that actually break agents. Expand the suite as you discover real failure modes."

This is a requirement, not a nicety. Users who skip it will conclude "the tests pass" means more than it does.

### Step 6: Implement promote flow

Two paths, both supported:

**Skill-driven:** user says "promote the partial-refund and p1-outage cases" or "promote everything" → skill `mv`s those YAMLs from `_draft/` to `cases/`. Skill confirms what moved and what remains in `_draft/`.

**Manual:** user moves files themselves in their editor. Skill doesn't need to know. `cases/*.yaml` is the only glob `montecarlo eval run` (slice 2) will look at; `_draft/` is ignored.

Neither path requires a new CLI command.

### Step 7: End-to-end dogfood run

In the selected `ai-agent` agent:
1. Invoke the skill to set up evals → init flow runs → `eval-config.yaml` and `invoke.py` stub written
2. Skill offers bootstrap → extraction + synthesis populate `_draft/`
3. User reviews cases in `_draft/`, edits as needed
4. Skill promotes approved cases to `cases/`
5. Engineer fills in `invoke.py` (this is real work, not part of the skill — flag it to the user)

End state: a real MC agent has `tests/eval/eval-config.yaml`, `tests/eval/invoke.py` (filled in), and N cases in `tests/eval/cases/` ready for slice 2's runtime.

---

## Acceptance criteria

Slice 1 is done when all of these are true:

- [ ] `monte-carlo-evaluate` skill exists in `mcd-agent-toolkit/skills/evaluate/`, created via `skill-creator`
- [ ] Skill's `when_to_use` and activation guard are explicit and correct
- [ ] Skill does nothing in a non-agent repo without explicit setup invocation
- [ ] In monorepos, skill confirms agent scope before any operation
- [ ] Init writes valid `eval-config.yaml` and a clean stub `invoke.py`
- [ ] Bootstrap produces at least a few extracted cases and ~6–10 synthesized cases for the dogfood target
- [ ] Synthesis warning is shown after every synthesis pass
- [ ] Promote moves files from `_draft/` to `cases/` correctly, in batch and individually
- [ ] Case YAML files pass a schema validator (format defined in SPEC.md §7)
- [ ] The dogfood target has a fully scaffolded `tests/eval/` directory suitable for slice 2 to pick up

---

## Notes on execution

### Iterate on real content, not mocks

The extraction and synthesis logic is where slice 1 earns or fails to earn its keep. Don't test these on toy examples. Run against the real dogfood target early and often. If the cases you're generating look useless, the logic needs work — that's more important than additional skill polish.

### Don't build ahead

If you find yourself implementing something that'd only pay off in slice 2 (e.g., template lookup, LLM-judge invocation, baseline I/O), stop. Slice 1 produces scaffolding artifacts. Slice 2 produces a working eval runner.

### Surgical diffs over rewrites

Once the skill structure is in place, resist the urge to restructure it. Small, focused changes. Update `SPEC.md` if a decision changes; don't silently drift from it.

### Questions for check-in

After slice 1 ships and before slice 2 starts, bring these back to claude.ai for design review:
- Did the activation guard work correctly in MC's multi-repo setup?
- How did extraction perform against real MC agent tests? What patterns worked / failed?
- How did synthesis quality feel to the engineer? Too generic? Missing obvious cases?
- Did the `_draft/` → `cases/` review flow match how engineers actually want to review?
- Any schema gaps surfaced during scaffolding? Fields that should have been in V1?

Take these findings into slice 2 planning.
