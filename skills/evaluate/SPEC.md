# Eval Agent — Specification

Living specification. Updated as design evolves. Authoritative for implementation decisions.

---

## 1. Overview

**Eval Agent** is an eval engine for AI agents that plugs into multiple points in an AI engineer's workflow. The POC scope is limited to the local development loop — a Claude Code skill that helps engineers set up, bootstrap, and run evals on AI agents.

**Previously known as:** "Eval-Gated Deployment." Renamed to reflect a scope shift: the product is an eval engine with pluggable integration points, not primarily a deploy gate.

---

## 2. Product narrative

**POC / internal dogfooding (now):** "Fast local feedback for agent quality." Primitive-led. Honest about what ships. The pod uses it on MC agents. The test is whether iteration loops change.

**Product (roadmap):** "Your test suite grows from real production failures." Flywheel-led. This is where MC wins vs. Braintrust/LangSmith — they cannot build this without production observability. Not pitched externally until Agent Monitoring maturity backs it up.

**Architectural constraint:** the POC primitive must not paint us into a corner for the flywheel. Specifically, case schema must mechanically accept production traces; baseline format must match eventual backend API shape.

---

## 3. Scope

### POC scope

- Claude Code skill (`monte-carlo-evaluate` in `mcd-agent-toolkit`, folder `skills/evaluate/`)
- `montecarlo eval` CLI subcommand group for `init` and `run` (slice 2+)
- Text, action, and mixed agent support
- Local file-based baseline
- Bundled template library (ported from MC backend dimensions)
- Bootstrap (synthesize + extract) for cold-start repos

### Out of POC scope (deferred, not killed)

- PR-time / CI / pre-deploy / post-deploy integration
- Backend baseline storage
- Agent Monitoring / flywheel integration
- CLI-native bootstrap (requires its own LLM client)
- Multi-turn input (`conversation:` schema)
- Retrieval fixture support
- Proactive skill triggering on agent file changes

### Killed

- Statistical significance testing
- Parallelism architecture as a subsystem
- Multi-sample scoring as central feature (demoted to config knob)
- CI adapters / GitHub App integration
- Template library distribution service

---

## 4. Repositories

| Repo | Role in POC |
|---|---|
| `cli` | Monte Carlo CLI. Binary name: `montecarlo`. New `eval` subcommand group added here (slice 2+). |
| `mc-agent-toolkit` | Houses the `monte-carlo-evaluate` skill (folder: `skills/evaluate/`). Skill development and distribution. |
| `ai-agent` | Dogfooding target. No code changes to this repo — only scaffolding added under `tests/eval/`. |

---

## 5. Architecture

### Call chains

**Evaluation (slice 2+):**
```
Skill → montecarlo eval run → invoke.py subprocess (1×/case)
                           → LLM API (judge, user's API key)
                           → write .monte-carlo/eval/runs/<timestamp>/
                           → JSON output
Skill ← JSON ← CLI
Skill presents conversationally
```

**Bootstrap (slice 1):** Skill-native. Claude Code itself is the LLM doing synthesis. No CLI call, no external LLM API call. Reads agent source per `source_paths`, reads artifacts per `reference_paths`, writes candidates to `tests/eval/cases/_draft/`.

**Init (slice 1):** Skill-native. Deterministic, question-driven. Writes `eval-config.yaml` and stub `invoke.py`.

### Key principle: MC is the evaluator, not the runtime

MC does not invoke the agent. The engineer's `invoke.py` does. MC receives inputs + outputs and scores them. This is a commitment, not an implementation detail.

### Key principle: No backend at POC

Template library is bundled with the CLI package. LLM calls use the engineer's own API key. No MC server dependency for any POC operation.

---

## 6. File layout per agent

```
<agent_root>/
  tests/eval/
    eval-config.yaml         # committed
    invoke.py                # committed
    cases/
      <case-id>.yaml         # committed, one case per file
      _draft/                # committed or gitignored, engineer's choice; ignored by eval runner
        <candidate>.yaml
    inputs/                  # committed; for cases with input_file:
      <fixture>.txt
    templates/               # committed if ejected; else absent
      <dimension>.yaml
    baseline.json            # committed
  .monte-carlo/eval/
    runs/<timestamp>/        # gitignored
```

**`agent_root`** is wherever `tests/eval/eval-config.yaml` lives. In monorepos (like MC's `ai-agent`), each agent has its own config. One agent = one config. No inference.

**On monorepos with inconsistent test layouts:** the canonical layout above is the recommendation, not a hard requirement. `source_paths` and `reference_paths` in the eval config accept relative paths that may traverse outside the agent directory (e.g., `../../../tests/ai_agent/<agent>/test_foo.py`). This handles repos where agent source and existing tests live in different top-level directories. Engineers accepting this trade inconsistency with existing test conventions for consistency across Eval Agent-managed scaffolding.

---

## 7. Test case schema

One case per YAML file. File stem is the case ID (no `id:` field). Flat `cases/` directory at V1; subdirectories allowed but organizational only.

### Fields

```yaml
# Required (exactly one of):
input: "string literal"                    # small inputs
input_file: inputs/<relative-path>         # large / structured / file-based inputs

# Optional
reference_output:                          # include only the parts you want to score against
  text: "expected response text"
  actions:
    - tool: classify_issue
      args: { severity: "P1" }
    - tool: assign_issue
      args: { team: "infrastructure" }

tags: [triage, p1]                         # for filtering and grouping
source: synthesized:from_system_prompt     # human | synthesized:* | extracted:<path> | production:<trace_id>
```

### Rules

- `input:` and `input_file:` are mutually exclusive (exactly one, never both, never neither).
- `input_file:` paths are relative to agent root.
- `reference_output:` is optional entirely. Some dimensions score without a reference.
- `actions:` are ordered by default. Order-insensitive comparison is a dimension config concern, not a case field.
- Action fields at V1: `tool` and `args` only. No `id`, `order`, `forbidden`, or result assertions.
- `source:` is recorded at generation time. Never edited by user tooling.

### Three valid shapes

**Text-only:**
```yaml
input: "Summarize this article: [...]"
reference_output:
  text: "Expected summary points..."
tags: [summarization]
source: human
```

**Action-only:**
```yaml
input: "Database is down"
reference_output:
  actions:
    - tool: classify_issue
      args: { severity: P1 }
tags: [triage]
source: extracted:tests/test_triage.py
```

**Mixed:** both `text` and `actions` under `reference_output`.

### Large / structured input pattern

```yaml
# tests/eval/cases/n-plus-one-in-user-service.yaml
input_file: inputs/n-plus-one-in-user-service.diff
reference_output:
  text: |
    Concern: the loop at user.go:142 makes a DB call per user...
tags: [pr_review, performance]
source: extracted:tests/test_pr_agent.py
```

For structured inputs (multi-field), the file may be JSON. The eval runner reads the file and passes its contents as a string to `invoke.py`. The engineer's invoke function parses if needed. MC stays out of agent-specific structure.

---

## 8. Eval config schema

```yaml
# tests/eval/eval-config.yaml
agent:
  name: refund_handler
  source_paths:                    # relative to agent_root; scanned by bootstrap synthesis
    - prompts/refund_system.md
    - tools/refund_tools.py
  reference_paths:                 # relative to agent_root; scanned by bootstrap extraction
    - tests/test_refund.py
    - docs/examples.md
  output_type: mixed               # text | action | mixed

dimensions:
  - template: answer_relevance     # bundled name OR ./path/to/custom.yaml
    samples: 3
    judge_model: claude-sonnet-4   # optional, per-dimension override
  - template: tool_use_correctness # deterministic
    match: subset                  # exact | subset | order_insensitive
  - template: ./templates/custom-refund-tone.yaml
    samples: 5

regression:
  default_threshold: 0.05          # absolute score drop
  per_dimension:
    tool_use_correctness: 0.0      # zero tolerance; deterministic
    hallucination: 0.1             # looser; noisier judge
```

### Template reference resolution

- Bare string → bundled template by name (e.g., `answer_relevance`)
- Path starting with `./` or `/` → local file (typically in `tests/eval/templates/`)

Clean disambiguation. No registry lookup.

### Three-tier customization

1. **Use as-is:** reference bundled template by name. Nothing in repo.
2. **Eject + edit:** `montecarlo eval template eject <name>` copies bundled YAML to `tests/eval/templates/<name>.yaml` and updates config to point there. (Slice 2+.)
3. **Replace entirely:** engineer writes their own template YAML, references by path.

Init does not eject by default. Repos stay clean.

---

## 9. Baseline format

File: `tests/eval/baseline.json`. Committed. Machine-generated, machine-read, never hand-edited.

```json
{
  "schema_version": 1,
  "cli_version": "0.3.0a2",
  "updated_at": "2026-04-19T14:23:11Z",
  "updated_by": "yijia@montecarlodata.com",
  "cases": {
    "partial-refund-loyalty": {
      "answer_relevance": {"score": 0.86, "samples": 3},
      "tool_use_correctness": {"score": 1.0, "samples": 1},
      "hallucination": {"score": 0.94, "samples": 3}
    }
  }
}
```

### Rules

- Unit of record: `(case_id, dimension) → {score, samples}`.
- Keys sorted deterministically on write (minimize merge conflicts).
- `cli_version` stamped. Version mismatch produces a warning (not a block) on comparison runs.
- Promotion is explicit only: `montecarlo eval baseline set`. No run auto-updates baseline.
- Additive/replacement merge: `set` overwrites `(case, dim)` pairs in the run; leaves others alone.
- Missing baseline entry → case reported as "new" in run output (not regression, not pass).

### Regression thresholds

Live in `eval-config.yaml`, not in `baseline.json`. Thresholds are judgment calls about the agent; baseline only stores observations.

### Backend migration path

Baseline JSON shape matches future backend API response: `{cases: {case_id: {dimension: {score, samples}}}}`. Migration is a storage swap behind `baseline.source:` config field, not a schema rewrite.

---

## 10. Invocation contract

Engineer writes `tests/eval/invoke.py`:

```python
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
    # ...engineer owns setup: auth, DB, deps, fixtures.
    return {...}
```

### Rules

- Python-only at V1. TypeScript / Go deferred until a non-MC-agent user asks.
- Path is conventional (`tests/eval/invoke.py`) but overridable via `eval-config.yaml`.
- Single-case invocation. The CLI handles batching; `invoke.py` handles one case.
- Exceptions in `invoke.py` mark the case `errored: true`; the run continues.

---

## 11. Dimensions library

### Layout

```
mc_eval/
  templates/                         # LLM-judged, YAML
    answer_relevance.yaml
    helpfulness.yaml
    task_completion.yaml
    semantic_similarity.yaml
    prompt_adherence.yaml
  dimensions/                        # deterministic, Python
    tool_use_correctness.py
    action_sequence_match.py
    json_validity.py
    output_length.py
  judge_runner.py                    # shared LLM-judge executor
  registry.py                        # name → template/function dispatcher
```

### LLM-judged dimensions (YAML templates)

Ported from MC backend `transformations.yaml` with edits:
- Drop `sql:` and `sql_expression_map:` (warehouse-specific).
- Keep `prompt:`, `score_field:`, `output_type:`, `output_description:`, `rubric:`, `scoring_anchors:`, `bias_guardrail:`.
- Rename template variables from `{{prompts}}`/`{{completions}}` to `{{input}}`/`{{output}}`. Update prompts accordingly (drop "JSON arrays of role/message" language).

### Deterministic dimensions (Python functions)

```python
# mc_eval/dimensions/tool_use_correctness.py
def score(case, actual_output, config) -> dict:
    """Return {'score': float, 'reasoning': str}."""
```

Net-new for Eval Agent (not in MC backend): `tool_use_correctness`, `action_sequence_match`. Ported from MC (re-implemented in Python, not SQL): `json_validity`, `output_length`.

### POC dimension set (slice 2)

Start with: `answer_relevance`, `task_completion`, `semantic_similarity`, `prompt_adherence`, `tool_use_correctness`. Others deferred until requested.

### Cross-repo template synchronization

POC forks templates into CLI package. Long-term convergence with MC backend is TBD — flagged as an open architectural question. Without convergence, the flywheel's score semantics drift between Agent Monitoring and Eval Agent.

---

## 12. Skill behaviors

**Skill identity:**
- `name:` field in SKILL.md: `monte-carlo-evaluate` (individually distributable skill name)
- Folder: `mcd-agent-toolkit/skills/evaluate/`
- Referenced when installed via toolkit: `/mc-agent-toolkit:evaluate`

The `monte-carlo-` prefix on the skill name matches the convention used by the existing `monte-carlo-prevent` skill — skills distributed individually carry the prefix; within the toolkit plugin they are referenced by short name. "Eval Agent" remains the product name (spans skill + future CLI + future surfaces); the skill is one implementation artifact.

### Activation guard

Skill engages **only** when `tests/eval/eval-config.yaml` exists at or above the engineer's working directory. In non-agent repos (dbt, infra, etc.), the skill does nothing.

Exception: explicit "set up eval agent" requests activate the init flow even without config present.

### Agent scope confirmation

In monorepos with multiple agents (MC's `ai-agent` is the canonical example), the skill must confirm which agent before any operation. Detection:
1. If user specifies explicitly, use that.
2. Else, walk up from cwd to nearest `eval-config.yaml`.
3. If multiple configs exist at or below cwd (ambiguous), list them and ask.
4. If none exist at cwd but some exist elsewhere in repo, list them and ask.

Never assume scope in ambiguous cases.

### Behaviors

- **Setup:** runs init flow → optionally offers bootstrap
- **Bootstrap:** synthesize + extract → `_draft/` → review → promote (slice 1)
- **Run (slice 2):** filter by tag or case ID; present results; proactively offer to diagnose regressions
- **Diagnose (slice 3):** pull run artifacts, read diff, explain score shifts
- **Baseline (slice 3):** `show` / `set` via CLI passthrough

### Explicitly deferred

- Proactive triggering on agent file changes ("I noticed you modified `prompts/refund_handler.md`")
- Pre-commit / pre-push hooks (evals are slow, non-deterministic, cost real money)

---

## 13. CLI commands (slice 2+)

Subcommands under `montecarlo eval`:

| Command | Slice | Purpose |
|---|---|---|
| `montecarlo eval init` | 2 | Create `eval-config.yaml` and `invoke.py` stub. (Slice 1 does this via skill; slice 2 adds CLI-native version for non-Claude-Code users.) |
| `montecarlo eval run` | 2 | Run cases, write artifacts, print results. |
| `montecarlo eval baseline show\|set` | 3 | Inspect / promote baseline. |
| `montecarlo eval template eject <name>` | 2 | Copy bundled template to local repo for customization. |

### `run` flags

- `--agent <path>` — agent root (default: walk up from cwd to nearest `eval-config.yaml`)
- `--filter-tags <tag,tag>` — only cases with matching tags
- `--case <name>` — specific case by ID
- `--baseline <path>` — override default baseline path
- `--no-baseline` — skip baseline comparison
- `--samples <N>` — override config multi-sample count
- `--output json|text` — default text; skill always passes json

### Output

- Text mode: human-readable table with per-case, per-dimension scores and baseline deltas
- JSON mode: versioned top-level (`schema_version: 1`), per-case results, aggregate summary, pointer to `.monte-carlo/eval/runs/<timestamp>/` artifacts directory
- Run artifacts (gitignored): full JSON result, per-case judge reasoning, raw invocation outputs

---

## 14. Release and distribution

### CLI

Ship as a new subcommand group on the existing `montecarlo` CLI. Not a separate package. Internal pod usage via PyPI pre-release versions: `montecarlo==X.Y.Za1`. Install with `pip install --pre montecarlo`. Stable users never see preview features.

Cutover to stable: promote to next regular `montecarlo` minor version once POC validates. Flag `eval` subcommands as "preview" in help text until then.

### Skill

Distributed via `mcd-agent-toolkit` installer. Users who already have the toolkit installed pull the new skill on update.

---

## 15. Integration points roadmap (post-POC)

Listening target during POC determines priorities for next slice:

1. **POC** — local CLI + skill. Validates primitive. (current)
2. **CLI hardening** — non-Claude-Code users, GTM path.
3. **Backend baseline + PR-time reporting** — centralized baseline, PR comments, CI-compatible invocation.
4. **Pre-deploy gate mode** — config flip on step 3's infrastructure.
5. **Post-deploy + nightly** — different triggers, same runner.
6. **Flywheel** — production failures → candidate cases. Gated on Agent Monitoring maturity.

---

## 16. Open questions (revisit post-POC)

- **Template synchronization with MC backend.** Forked at POC; convergence strategy TBD.
- **Multi-turn input schema.** When a real agent requires it, introduce `conversation:` as alternative top-level field.
- **Retrieval fixture support.** For RAG agents where we want to isolate LLM behavior from retrieval variance.
- **Multi-engineer baseline merge.** `montecarlo eval baseline rebase` is V2+.
- **CLI-native bootstrap.** Requires CLI to own its own LLM client and API key. Scope once a non-Claude-Code user asks.
- **Structured input first-class support.** Currently punted to "use `input_file:` with JSON." Revisit when multiple agents need it.
