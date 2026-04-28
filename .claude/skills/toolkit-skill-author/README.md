# toolkit-skill-author

A meta-skill for **authoring or extending skills in `mc-agent-toolkit`**. Run it from the repo root via `/toolkit-skill-author`. It interviews you, applies the extend-or-split rules from `CONTRIBUTING.md`, hands off to Anthropic's `skill-creator` for the actual SKILL.md generation, and walks the registration checklist that keeps the orchestration layer, `/mc` catalog, evals, and version manifest in sync.

This skill is for **toolkit contributors**, not end users of mc-agent-toolkit.

## Why this exists

Adding a skill to `mc-agent-toolkit` is more than dropping a `SKILL.md` into `skills/`. A new skill must be:

1. **Justified** against the extend-or-split decision rules so we don't grow a soup of overlapping skills.
2. **Named** without colliding with existing skills (exact or near-match).
3. **Registered** in the orchestration layer (`signal-definitions`, `/mc` catalog) so context detection can find it.
4. **Eval'd** so activation is measurable.
5. **Symlinked** into all five editor plugins (`claude-code`, `cursor`, `codex`, `copilot`, `opencode`).
6. **Versioned** via `scripts/bump-version.sh` so the marketplace ships the change.

Doing all of that by hand is error-prone. This skill enforces the workflow and gates against the common mistakes (forbidden buckets, name collisions, skipping registration steps).

## When to use it

Run `/toolkit-skill-author` when you want to:

- **Add a new skill** to the toolkit.
- **Extend an existing skill** with new capabilities, phrasings, or references.

Do **not** use it for:

- **Editing skill internals that aren't activation-surface changes** (typo fixes, minor rewording). Just edit the file and run a `patch` bump.

## Prerequisites

- Run from the **`mc-agent-toolkit` repo**.
- Anthropic's `skill-creator` plugin must be installed and enabled in the current session:
  ```
  /plugin install skill-creator@claude-plugins-official
  ```
  Restart the session after install. The skill aborts if `skill-creator` isn't available — the handoff is core to the workflow, and there is no manual fallback.
- Clean working tree recommended (the skill stages changes but does not commit).

## How it works

```
/toolkit-skill-author
  │
  ├── Pre-load: verify repo + skill-creator availability,
  │             dump CONTRIBUTING.md and existing skill peers
  │
  ├── Phase 0 — Parse intent + apply gates
  │     ├── Gate A: forbidden bucket (Agent-routing) → halt
  │     ├── Gate B: name collision (exact or token-overlap) → ask before proceeding
  │     └── Gate C: clear extend → fast-path to Phase 2a
  │
  ├── Phase 1 — Decision survey (4 questions, one at a time)
  │     bucket · MCP surface · purpose · example prompts
  │
  ├── Decision — apply 4-step test from decision-rules.md
  │     verdict: EXTEND <peer>  or  NEW SKILL
  │
  ├── Phase 2a — Extend                   Phase 2b — New skill
  │     hand off to skill-creator           extended survey + name proposal
  │     in IMPROVE_EXISTING mode            hand off to skill-creator NEW_SKILL
  │     run lint-skill.py                   run lint-skill.py
  │     partial registration checklist     full registration checklist
  │
  └── Shared — version bump
        propose patch/minor/major per CONTRIBUTING § Version bumping
        run scripts/bump-version.sh
```

## What's in this directory

| Path | Purpose |
| --- | --- |
| `SKILL.md` | The skill itself — the workflow router. |
| `references/decision-rules.md` | Source-of-truth for the 4-step extend-or-split test. Linked from `CONTRIBUTING.md`. |
| `references/handoff-preamble.md` | Template the skill passes to `skill-creator` so the generated SKILL.md matches toolkit conventions. |
| `references/registration-checklist.md` | Post-handoff steps (signal-definitions, `/mc` catalog, evals, symlinks). |
| `scripts/find-peers.sh` | Dumps name + description + when_to_use for every existing skill — the candidate set the decision tree reasons over. |
| `scripts/check-prereqs.sh` | Pre-flight check used by the pre-load. |
| `scripts/lint-skill.py` | Validates frontmatter (name, description ≤250 chars, prefix) after `skill-creator` returns. |
| `scripts/tests/` | Fixture tests for the helper scripts. |
| `evals/` | Activation evals for this skill. |

## Notes for SPEDD reviewers

- The skill is **read-only** through Phase 1 — no files are touched until after the decision verdict is confirmed.
- The skill **never auto-commits**. Every modification is staged for explicit review.
- Forbidden-bucket and name-collision gates run **before** any survey questions, so a refusal is fast and unambiguous.
- The four-step decision-rules test is documented in `references/decision-rules.md` and referenced by `CONTRIBUTING.md`. If the rule needs to change, update both.
- `lint-skill.py` enforces the constraints from `.claude/rules/skills.md` (description length, name prefix). Failures block the registration checklist.
- Version bumps go through `scripts/bump-version.sh`, which updates all five plugin manifests + changelogs in lockstep — no partial-bump risk.

## Troubleshooting

| Symptom | Cause / fix |
| --- | --- |
| `skill-creator plugin is required` | Install `skill-creator@claude-plugins-official`, enable it, restart the session. |
| `CONTRIBUTING.md missing — run from repo root` | You're not at the repo root. `cd` to `mc-agent-toolkit/`. |
| Gate B fires unexpectedly on a name | Token-overlap is intentional — pick a more distinct name, or switch to extend. |
| Lint ERROR after handoff | Either fix manually or ask `skill-creator` to regenerate the offending field. The registration checklist will not proceed until lint is clean. |
