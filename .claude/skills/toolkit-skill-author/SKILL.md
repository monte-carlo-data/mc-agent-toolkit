---
name: toolkit-skill-author
description: Authors or extends a skill in mc-agent-toolkit. Gates for forbidden buckets and name collisions, applies CONTRIBUTING's extend-or-split rules, then edits a peer skill or hands off to Anthropic's skill-creator and walks the registration checklist.
disable-model-invocation: true
when_to_use: |
  Invoked explicitly as /toolkit-skill-author when a contributor wants to add, extend, or draft a new skill for mc-agent-toolkit. Not auto-routed. Requires Anthropic's skill-creator plugin.
---

# toolkit-skill-author

## Pre-load

```bash
!test -f CONTRIBUTING.md || (echo "CONTRIBUTING.md missing — run from repo root." && exit 1)
```

**Verify `skill-creator` is callable in this session.** Scan the available-skills list for a skill named `skill-creator` (bare or namespaced, e.g. `skill-creator:skill-creator`). If absent, abort with **exactly this message**:

> `skill-creator` plugin is required. Run `/plugin install skill-creator@claude-plugins-official`, enable it, then restart this session and re-run `/toolkit-skill-author`.

Do **not** fall back to manually scaffolding SKILL.md — the handoff is core to the workflow.

Load authoritative context:

```bash
!cat CONTRIBUTING.md
!bash .claude/skills/toolkit-skill-author/scripts/find-peers.sh skills
```

- @.claude/skills/toolkit-skill-author/references/decision-rules.md
- @.claude/skills/toolkit-skill-author/references/handoff-preamble.md
- @.claude/skills/toolkit-skill-author/references/registration-checklist.md

## Phase 0 — Parse intent and apply gates

From the contributor's initial prompt, extract (without asking yet):

- **`target_name`** — did they name a specific skill (e.g., *"extend `monitoring-advisor`"*, *"create a skill called `foo-bar`"*)?
- **`action`** — `extend`, `new`, or `unknown`.
- **`bucket`** — did they state a capability bucket?

Apply the gates below **before** any survey question. Each gate halts when it fires.

### Gate A — Forbidden bucket

If `bucket` is `Agent-routing` (or a synonym like "agent routing", "routing skill"), refuse:

> Agent-routing skills are owned by the toolkit core team per `CONTRIBUTING § Capability buckets` — not authored via `/toolkit-skill-author`. Halting.

Do not proceed. If `bucket` is unstated, this gate re-applies after Q1.

### Gate B — Name collision (new-skill intent)

If `action` is `new` and `target_name` is given, lowercase both `target_name` and each existing skill directory name, then check:

- **Exact match** (equal strings): refuse with *"`<target_name>` already exists in `skills/`. Pick a different name, or switch to extend."* Do not proceed.
- **Near match.** Split both names on `-` into token lists. Fire if either (a) the two lists share any token, or (b) any token in one list is a substring of any token in the other list. Example: `monitor-advisor` ↔ `monitoring-advisor` fires via (a) shared `advisor` and (b) `monitor` ⊂ `monitoring`. When fired, surface the overlap and ask: *"`<target_name>` overlaps with existing `<existing>`. Did you mean to extend `<existing>`, or proceed with a new name?"* Wait for an answer before continuing.

### Gate C — Fast-path for clear extend

If `action` is `extend` and `target_name` names an existing skill:
- **Re-check the bucket.** If `target_name` is one of the agent-routing skills (`context-detection`, `incident-response`, `proactive-monitoring`), fire Gate A's refusal — those are owned by the core team and cannot be extended via `/toolkit-skill-author` either.
- Otherwise: skip the Phase 1 survey, use the initial prompt as the extension description, and jump directly to **Phase 2a — Extend**. If the prompt is missing fields the handoff preamble needs (purpose, phrasings, output artifact), ask only for those specific fields — do not re-run the full Q1–Q4 survey.

Otherwise, continue to Phase 1. **New-skill requests always run the decision tree** — the gate against hidden collisions is the tree itself.

## Phase 1 — Decision survey

Ask these four questions **one at a time**, waiting for each answer.

1. **Capability bucket.** Trust / Incident Response / Monitoring / Prevent / Optimize / Setup. Agent-routing is not offered. If the contributor writes in `Agent-routing`, fire Gate A and halt.
2. **Primary MCP surface or data input.** E.g. Monte Carlo GraphQL, BigQuery INFORMATION_SCHEMA, Sentry issues. One or two items.
3. **One-line purpose.** Plain language — no pushy triggers.
4. **2–3 example user prompts.** Quote them literally.

## Decision

Apply the 4-step test from `decision-rules.md` against the peers dumped by `find-peers.sh`. The dump shows every skill's name + description + when_to_use; reason directly about which skills could plausibly activate on the Q4 prompts.

Filter agent-routing skills out of the candidate set — contributors can't author those, so they can't be extension targets. Current list: `context-detection`, `incident-response`, `proactive-monitoring`. If the toolkit adds new routing skills, update both this list and Gate C's list to match.

Present the verdict:
- `EXTEND <peer>` or `NEW SKILL`.
- The step that decided, and why.
- "Proceed with this verdict, or override?"

If the user overrides, capture their reason verbatim — it becomes part of the PR description per `CONTRIBUTING`.

## Phase 2a — Extend

Invoke `skill-creator` via the `Skill` tool in **improve-existing mode**, passing the handoff preamble from `references/handoff-preamble.md` with `MODE=IMPROVE_EXISTING`, `PEER_NAME=<peer>`, and the survey answers (or the initial prompt for the fast-path case).

`skill-creator` runs its full loop; if the contributor wants a lighter-touch edit, they can tell it mid-flow to skip iteration.

When `skill-creator` returns:

```bash
!rm -rf skills/<peer>/evals/ skills/<peer>-workspace/
!python3 .claude/skills/toolkit-skill-author/scripts/lint-skill.py <peer>
```

Scratch-artifact cleanup removes skill-creator's iteration files (they drove the loop but aren't the repo's eval format). Lint surfaces any frontmatter violations.

Walk the **partial** checklist from `references/registration-checklist.md` via TodoWrite:
- Signal-definitions update — only if phrasings shifted.
- `/mc` catalog update — only if user-facing surface changed.
- Eval entry update — only if activation surface expanded.

Continue to the shared version-bump step.

## Phase 2b — New skill

### Extended survey (one at a time)

5. **Output artifact** — what the skill produces (file type, diff, notebook, text verdict).
6. **Persona / workflow** — who invokes this and during what task.
7. **Disambiguation** — how it differs from the nearest peer (by bucket), even if no peer forced a split.

### Propose name

Suggest 2–3 kebab-case **directory names**. Short is better. Re-run Gate B against each candidate:

- Exact match → drop the candidate.
- Near match (token-overlap with any existing skill) → drop or explicitly flag.

Only present candidates that survive Gate B. Wait for the contributor to pick one. Before handoff, re-verify `skills/<chosen>/` does not exist.

**Note the two-level naming:** the directory is `skills/<chosen>/`, but the `name` field inside the generated SKILL.md frontmatter should be `monte-carlo-<chosen>` — the canonical prefixed form. The handoff preamble passes both, and `lint-skill.py` verifies them after scaffold.

### Handoff to `skill-creator`

Invoke via the `Skill` tool with the handoff preamble from `references/handoff-preamble.md`, `MODE=NEW_SKILL`, and all survey answers.

When `skill-creator` returns:

```bash
!rm -rf skills/<name>/evals/ skills/<name>-workspace/
!python3 .claude/skills/toolkit-skill-author/scripts/lint-skill.py <name>
```

If lint prints ERROR lines, surface them and wait for the contributor to fix (manually or via a regenerate pass) before proceeding.

### Full registration checklist

Walk the full checklist from `references/registration-checklist.md` via TodoWrite, one item per step:
1. Read the relevant existing file.
2. Draft the addition.
3. Show the diff and confirm.
4. Apply with `Edit`, or create new files with `Write`.

If Q1 = Setup, confirm: *"Setup skills are exempt from signal-definitions and `/mc` catalog registration per CONTRIBUTING. Skip those two steps? [Y/n]"* — default Y.

## Shared — version bump

Both phases converge here.

1. Propose a level based on what actually changed:
   - New skill → **minor** per `CONTRIBUTING § Version bumping`.
   - Extend changed activation surface (phrasings in `description` or `when_to_use`) → **minor**.
   - Extend did not touch activation surface → **patch**.
2. *"Proceed with this level, or override?"* Valid overrides: `patch`, `minor`, `major`.
3. Run:
   ```bash
   !./scripts/bump-version.sh <level>
   ```
   The script opens `$EDITOR` for the changelog, then updates all 5 plugin configs and all 5 `CHANGELOG.md` files.

## Done

Tell the contributor:

> All changes are staged. Review with `git status` / `git diff --staged`, then commit and run `/ship` to open the PR.

Do **not** auto-commit or push.
