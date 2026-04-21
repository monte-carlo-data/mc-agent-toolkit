---
name: skill-author
description: Authors or extends a skill in mc-agent-toolkit. Interviews the contributor, applies CONTRIBUTING's extend-or-split rules, then edits a peer skill or hands off to Anthropic's skill-creator and walks the registration checklist.
when_to_use: |
  Invoked explicitly as /skill-author when a contributor wants to add, extend, or draft a new skill for mc-agent-toolkit. Not auto-routed. Requires Anthropic's skills-creator plugin to be installed.
---

# skill-author

## Pre-load

Before anything else, run the prereq check. Abort immediately on non-zero exit — do not proceed to the survey if prereqs fail.

```bash
!bash .claude/skills/skill-author/scripts/check-prereqs.sh
```

Then load authoritative rules:

```bash
!cat CONTRIBUTING.md
!ls skills/
```

Load the Claude-facing decision algorithm and handoff template:
- @.claude/skills/skill-author/references/decision-rules.md
- @.claude/skills/skill-author/references/handoff-preamble.md
- @.claude/skills/skill-author/references/registration-checklist.md

## Phase 1 — Decision survey

Ask the contributor these four questions **one at a time**. Wait for each answer before asking the next.

**Q1. Capability bucket.** Offer: Trust / Incident Response / Monitoring / Prevent / Optimize / Setup. Do not offer "Agent-routing" — those skills are owned by the toolkit core team per CONTRIBUTING and are not authored here.

**Q2. Primary MCP surface or data input.** E.g. Monte Carlo GraphQL API, BigQuery INFORMATION_SCHEMA, Sentry issues, user-provided files. One or two items at most.

**Q3. One-line purpose.** Plain language; do not front-load routing keywords here — that's Q4's job.

**Q4. 2–3 example user prompts** that should route to this skill. Quote them literally, e.g. `"why is this failing"`, `"tune this monitor"`.

Then run peer search with the collected inputs:

```bash
!bash .claude/skills/skill-author/scripts/find-peers.sh \
  --skills-dir skills \
  --bucket "<Q1 answer>" \
  --keywords "<2-5 keywords extracted from Q2, Q3, Q4>"
```

## Decision

Apply the 4-step test from `decision-rules.md` to each peer returned. Stop at the first step that decides.

Present the verdict to the user with:
- The verdict (`EXTEND <peer>` or `NEW SKILL`).
- The step that decided and why (cite the rule).
- An explicit ask: "Proceed with this verdict, or override?"

If the user overrides, capture their reason verbatim (it becomes part of the PR description per CONTRIBUTING).

## Phase 2a — Extend

Reached only when verdict is EXTEND.

### Edit-scope sub-survey

Ask: *Is this extension trivial or material?*
- **Trivial** — one bullet added to `when_to_use`, or a single-line `description` tweak.
- **Material** — new `references/` file, body restructure, expanded activation surface.

### Trivial path

1. Draft the edit based on survey answers (use phrasings from Q4 verbatim in `when_to_use`).
2. Show the unified diff against the peer's current `SKILL.md`.
3. Wait for user confirmation.
4. Apply the edit with `Edit` tool.
5. **Proposed bump:** `patch`. Escalate to `minor` if the edit touches activation surface (phrasings in `description` or `when_to_use`, or any routing-relevant field). Surface the proposed level and reasoning to the user.

### Material path

Invoke Anthropic's `skill-creator` via the `Skill` tool in **improve-existing mode**, passing the handoff preamble from `references/handoff-preamble.md` with:
- `MODE = IMPROVE_EXISTING`
- `NAME = <peer name>`
- `PEER_NAME = <peer name>`
- Purpose/output/persona/disambiguation filled from survey answers.

When `skill-creator` returns, the peer's `skills/<peer>/SKILL.md` has been updated in place.

**Proposed bump:** `minor`.

### Partial registration review

Walk the partial checklist from `references/registration-checklist.md`. Use TodoWrite to track each:
- Signal-definitions update — only if phrasings shifted.
- `/mc` catalog update — only if user-facing surface changed.
- Eval entry update — only if activation surface expanded.

Continue to the shared version-bump step.

## Phase 2b — New skill

Reached only when verdict is NEW SKILL.

### Extended survey

Ask one at a time:
- **Q5.** Output artifact — what the skill produces (file type, notebook, diff, etc.).
- **Q6.** Persona / workflow — who invokes this and during what task.
- **Q7.** Disambiguation from nearest peer — how it differs from the closest-but-not-routing-colliding skill (even if no peer forced a split, pick the nearest by bucket).

### Propose name

Suggest 2–3 kebab-case, verb- or noun-phrase candidates based on purpose and phrasings. Short is better. Check each for collision:

```bash
!ls skills/ | grep -i "<candidate>"
```

Wait for user to pick one.

### Handoff to Anthropic's skill-creator

Invoke `skill-creator` via the `Skill` tool using the handoff preamble from `references/handoff-preamble.md` with:
- `MODE = NEW_SKILL`
- `NAME = <chosen name>`
- `PURPOSE, PHRASINGS, OUTPUT` from Q3, Q4, Q5.
- `PERSONA_WORKFLOW` from Q6.
- `PEER_NAME, DISAMBIGUATION` from Q7.

`skill-creator` will scaffold `skills/<name>/SKILL.md` (and possibly `references/` files). It should skip evals and minimize follow-up questions per preamble.

### Lint generated SKILL.md

After `skill-creator` returns, validate against CONTRIBUTING rules:

```bash
!bash -c '
  sm="skills/$1/SKILL.md"
  desc_len=$(awk "/^description:/,/^[a-z_]+:/" "$sm" | head -n -1 | wc -c)
  wtu_len=$(awk "/^when_to_use:/,/^---/" "$sm" | head -n -1 | wc -c)
  combined=$((desc_len + wtu_len))
  echo "description bytes: $desc_len"
  echo "when_to_use bytes: $wtu_len"
  echo "combined: $combined (limit 1400)"
  grep -q "^when_to_use:" "$sm" || echo "MISSING: when_to_use"
  grep -iE "^description:.*(this skill|use this skill)" "$sm" && echo "VIOLATION: first-person opening" || true
  [ "$combined" -le 1400 ] && echo "OK: length" || echo "VIOLATION: combined length >1400"
' _ <NAME>
```

If any violation is printed, surface it and wait for user to fix (either manually or by asking `skill-creator` to regenerate with stricter constraints) before proceeding.

### Full registration checklist

Walk the full checklist from `references/registration-checklist.md`. Use TodoWrite with one item per step. For each:
1. Read the relevant existing file (e.g., `signal-definitions.md`, `mc.md`) to understand format.
2. Draft the addition.
3. Show diff and confirm.
4. Apply with `Edit` or create new file with `Write`.

If Q1 answer was Setup, confirm with user:
> Setup skills are exempt from signal-definitions and `/mc` catalog registration per CONTRIBUTING. Skip those two steps? [Y/n]

If Y, mark those TodoWrite items as N/A.

**Proposed bump:** `minor`.

Continue to the shared version-bump step.

## Shared — version bump

Both Phase 2a and Phase 2b converge here.

1. Present the proposed bump level (`patch` or `minor`) with a one-line reason:
   - "New skill: MINOR per CONTRIBUTING § Version bumping."
   - "Material extend: MINOR per CONTRIBUTING."
   - "Trivial extend: PATCH per CONTRIBUTING."
   - "Trivial extend that changed activation surface: MINOR (escalated)."
2. Ask: "Proceed with this level, or override?" Valid overrides: `patch`, `minor`, `major`.
3. Run:
   ```bash
   !./scripts/bump-version.sh <level>
   ```
   The script opens `$EDITOR` for changelog entry. It updates all 5 plugin config files and all 5 `CHANGELOG.md` files.

## Done

All edits are staged, not committed. Tell the user:

> All changes are staged. Review with `git status` / `git diff --staged`, then commit and run `/ship` to open the PR.

Do **not** auto-commit or push.
