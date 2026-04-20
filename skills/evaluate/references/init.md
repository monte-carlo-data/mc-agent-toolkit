# Init Flow

Skill-native, question-driven. Writes `tests/eval/eval-config.yaml`, a stub `tests/eval/invoke.py`, and creates an empty `tests/eval/cases/` directory under the agent's root.

> **SLICE 2 REFACTOR.** Init is a fully deterministic, one-shot operation per agent repo. SPEC.md §13 locates `montecarlo eval init` in slice 2. When that CLI command ships, **this file must shrink to a thin wrapper**: the skill collects answers (and proposes candidate paths using LLM inference — that part stays in the skill, not the CLI), then invokes `montecarlo eval init --name <...> --source-paths <...> --reference-paths <...> --output-type <...> --dimensions <...>` and surfaces the CLI's output. The native file-writing logic below is slice 1 only; do not port it past the slice 2 boundary.

---

## Preconditions

Before starting the flow:

1. **Agent scope is confirmed.** The SKILL.md §Agent scope confirmation logic must have run. You know which agent is being scaffolded and its `agent_root` directory.
2. **The user is in Mode B** (no `eval-config.yaml` exists at or above cwd under that agent_root), or has explicitly asked for re-init.
3. **The agent_root exists and is writable.** If not, stop and surface the error — do not attempt to create it; that's outside the skill's scope.

---

## Question flow (5 questions, sequential — one per turn)

**Ask one question at a time.** Present the question with detected candidates, wait for the user's answer or edit, confirm, then move to the next question. Do NOT present all five as a batch proposal — the user should have the chance to think about and edit each field on its own turn. A "yes, that's right" or equivalent to one question is the signal to move to the next.

After all five answers are confirmed, present the consolidated summary (see "Confirm the plan before writing" below) and get a final approval before any file is written.

The order matters: earlier answers inform later defaults (question 5's dimensions depend on question 4's output type).

### 1. Agent name

- **Ask:** "What should we name this agent?"
- **Default:** the basename of `agent_root` (e.g., `chat` for `ai-agent/ai_agent/chat/`).
- **Validate:** lowercase letters, digits, and underscores only. If the user's input violates this, suggest a normalized form and confirm.

### 2. Source paths

Used by the bootstrap **synthesis** pass (step 5). These files describe how the agent should behave — system prompts, tool definitions, routing logic.

- **Detect candidates.** Scan `agent_root` one level deep using `Glob`. Propose paths matching:
  - `*.md` at the root or under `prompts/` (system prompts)
  - `tools.py`, `tools/*.py` (tool definitions)
  - `prompts.py` (prompt templates encoded in Python)
  - `routing.py`, `graph.py` (behavior orchestration — include only if present and named that way)
  - `guidance/**/*.md` (nested prompt guidance, e.g., `chat/guidance/`)
- **Exclude from candidates:**
  - Test files (those belong in `reference_paths`)
  - `__init__.py`, `conftest.py`
  - The agent's own `README.md` and per-agent `CLAUDE.md` — these are engineer-facing docs, not LLM system prompts. If the user explicitly wants them, move to `reference_paths`.
- **Ask:** "These files look like agent source. Confirm, add, or remove: [list]"
- **Paths are relative to `agent_root`.**
- **Validate:** every path the user confirms must exist. Relative escapes (`../`) are allowed (see SPEC §6) but flag them back to the user for confirmation ("this escapes the agent directory — intentional?").

### 3. Reference paths

Used by the bootstrap **extraction** pass (step 4). These files contain examples of expected agent behavior — existing tests, docstrings with examples, README usage snippets.

- **Detect candidates.** Walk outward from `agent_root` to find test and example trees. Search broadly — multiple test trees may coexist in one repo:
  - `tests/` inside `agent_root` if present
  - Any directory matching `tests*/<agent_name>/` or `tests*/<parent>/<agent_name>/` in ancestor directories (e.g., `../../tests/ai_agent/<agent_name>/`, `../../tests_evals/ai_agent/<agent_name>/`). The `tests*` glob catches sibling conventions like `tests_evals/`, `tests_integration/`, `tests_e2e/` — include every match.
  - `README.md` inside `agent_root`
  - `CLAUDE.md` inside `agent_root` (engineer-facing docs often contain usage examples)
  - `docs/`, `examples/` if present
- **Don't assume a convention.** In messy monorepos the test tree may not mirror the source tree, and there may be multiple parallel test trees. If nothing obvious turns up, ask the user to point to the test files directly rather than guessing.
- **Ask:** "These files look like existing examples of the agent's behavior. Confirm, add, or remove: [list]"
- **Paths are relative to `agent_root`** and may traverse outward (per SPEC §6).

### 4. Output type

- **Ask:** "What does this agent output? (text / action / mixed)"
  - **text:** agent produces a text response (summarization, chat, Q&A)
  - **action:** agent calls tools to take actions (triage, routing, classification)
  - **mixed:** both (agent responds in text AND calls tools)
- **Default if you can reasonably infer:** scan `source_paths` for tool definitions. If `tools.py` or `tools/*.py` exists with any function definitions, lean toward **mixed** or **action**; absent, lean toward **text**. Always confirm with the user — do not auto-select.
- **Validate:** must be one of `text`, `action`, `mixed`.

### 5. Bundled dimensions

- **Derive defaults from the `output_type` answer:**
  - `text` → `answer_relevance`, `task_completion`, `semantic_similarity`, `prompt_adherence`
  - `action` → `tool_use_correctness`
  - `mixed` → all five above
- **Ask:** "For a `<output_type>` agent, we'll enable these dimensions by default: [list]. Keep as-is, add, or remove?"
- **Note to user:** dimensions are *configured* in slice 1 but *executed* in slice 2. Tell them directly: "These won't actually run until the slice-2 eval runner ships — the config is being written now so it's ready."

---

## Confirm the plan before writing

After all five answers are in, present a summary:

```
I'll write:
  <agent_root>/tests/eval/eval-config.yaml
  <agent_root>/tests/eval/invoke.py   (stub — you'll fill in the body)
  <agent_root>/tests/eval/cases/      (empty, ready for bootstrap)

agent.name:             <name>
agent.source_paths:     <list>
agent.reference_paths:  <list>
agent.output_type:      <type>
dimensions:             <list of dimension names>

Proceed?
```

Wait for a "yes" or equivalent. If the user edits anything, loop back and confirm again.

---

## Non-destructive check

Before each `Write` call:

- If the target file already exists and has non-empty content, **stop**. Show the current contents (short head) and ask: "This file already exists. Overwrite, merge, or abort?"
- If the user says abort: exit the flow without writing any of the three artifacts (all-or-nothing).
- If the user says merge: this is out of scope for slice 1 — tell them to resolve manually and re-run init.
- If the user says overwrite: proceed.

An empty file or a zero-byte stub counts as "not existing" for this check — overwrite freely.

---

## File: `tests/eval/eval-config.yaml`

Write with keys in this exact order for readability and merge-friendliness:

```yaml
# Eval Agent configuration — generated by monte-carlo-evaluate skill (slice 1).
# Dimensions listed below are configured but not yet executed; the slice-2
# eval runner (`montecarlo eval run`) will pick them up when it ships.

agent:
  name: <name>
  source_paths:
    - <path1>
    - <path2>
  reference_paths:
    - <path1>
    - <path2>
  output_type: <text|action|mixed>

dimensions:
  - template: <name1>
  - template: <name2>
  # ... one per selected dimension

regression:
  default_threshold: 0.05
```

**Rules:**

- Always emit the top comment verbatim — it tells the next reader why uncommented dimensions don't execute yet.
- Preserve list order in `source_paths` / `reference_paths` as the user confirmed them — do not re-sort.
- Leave `dimensions[].samples`, `dimensions[].judge_model`, `dimensions[].match` **unset** in slice 1. Defaults apply in slice 2; committing per-dimension config before the runner exists risks divergence from what slice 2 actually supports.
- Emit `regression.default_threshold: 0.05` as a reasonable starting point (matches SPEC §8 example). Do not emit `per_dimension:` — the user can add that in slice 3 when they know their noise floor.

## File: `tests/eval/invoke.py`

Framework-agnostic stub. Signature and docstring must match SPEC §10 verbatim:

```python
"""Eval Agent invocation contract — see SPEC.md §10.

The monte-carlo-evaluate skill generated this file. Fill in the body.
"""


def invoke(input: str) -> dict:
    """
    Called once per case by `montecarlo eval run`.

    Args:
        input: the string from the case's `input:` field,
               or the contents of the file at `input_file:`.

    Returns:
        dict with optional 'text' and 'actions' keys:
        {
          "text": "response string",
          "actions": [
            {"tool": "tool_name", "args": {...}},
            ...
          ],
        }
    """
    # TODO: wire up your agent here. Engineers own this function —
    # imports, setup (auth, DB, deps, fixtures), and the single-case
    # invocation itself. Keep it side-effect-free per case; the runner
    # batches, `invoke` handles one at a time. Exceptions mark the case
    # `errored: true` and the run continues.
    raise NotImplementedError("Wire up the agent invocation here.")
```

## Directory: `tests/eval/cases/`

Create as an empty directory. Do NOT add a `.gitkeep` file — slice 1 bootstrap (step 4) will populate it with `_draft/` content immediately, so the empty-directory window is transient. If the user aborts before bootstrap, the empty directory is harmless.

---

## Post-init handoff

After successful writes:

1. Confirm what landed: "Wrote `tests/eval/eval-config.yaml`, `tests/eval/invoke.py` (stub), and `tests/eval/cases/`."
2. Flag the two next actions the engineer needs to take:
   - **Fill in `invoke.py`** — the stub raises `NotImplementedError` until they wire up their agent. This is real work on their end, not the skill's.
   - **Optionally, run bootstrap** to populate `tests/eval/cases/_draft/` with synthesized and extracted candidate cases. Offer: "Want me to bootstrap initial test cases now?" — if yes, hand off to `references/bootstrap.md`.
3. Do NOT auto-run bootstrap without explicit confirmation. Init and bootstrap are distinct steps.
