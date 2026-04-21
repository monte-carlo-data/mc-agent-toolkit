# Handoff preamble for Anthropic's `skill-creator`

This is the template `skill-author` uses when invoking Anthropic's `skill-creator` via the `Skill` tool. Claude fills in the bracketed placeholders from survey answers.

## Template

You are being invoked by mc-agent-toolkit's `/skill-author` with pre-collected context.
**Use the pre-filled answers below to skip your initial interview. Then run your full workflow — test cases, iterate loop, and description optimizer — using the answers as the starting draft. If the contributor tells you mid-flow to skip iteration ("just vibe with me"), honor that.**

**Mode:** {{NEW_SKILL | IMPROVE_EXISTING}}

**Target path:** `skills/{{NAME}}/` in the mc-agent-toolkit repo (not your default workspace).

**Pre-filled answers:**
- What should this skill enable Claude to do? {{PURPOSE}}
- When should this skill trigger? {{PHRASINGS as bullet list}}
- Expected output format: {{OUTPUT}}

**Body context (inform the SKILL.md body, do NOT copy verbatim into frontmatter):**
- Persona / workflow: {{PERSONA_WORKFLOW}}
- Disambiguation from nearest peer `{{PEER_NAME}}`: {{DISAMBIGUATION}}

**MC-specific voice and length rules (override your defaults):**
- `description` ≤ 1,024 characters.
- Combined `description` + `when_to_use` ≤ 1,400 characters (headroom under the 1,536 truncation ceiling).
- Third-person voice. Describe what the skill does, not what "this skill" does.
- Do **not** open with "This skill…" or "Use this skill when…".
- Do **not** use the "pushy" voice pattern ("Make sure to use this skill whenever…"); use concrete triggers instead.
- `name` is `monte-carlo-{{NAME}}` (the canonical prefixed form; `{{NAME}}` is the directory name).
- `when_to_use` is required (not optional).

**Eval artifacts are scratch, not shipped:**
- Your `skills/{{NAME}}/evals/evals.json` and sibling `skills/{{NAME}}-workspace/` drive the iteration loop but are not the repo's eval format. `skill-author` will delete them after you return.
- mc-agent-toolkit's real evals live at `plugins/claude-code/evals/{{NAME}}/` with a different schema (trace-based: `must_call`, `must_not_call`, `judge_rubric`). Authoring those is handled by `skill-author` as a separate registration step — don't attempt to write that format yourself.

**When done:** return control to `skill-author`. It will lint the generated SKILL.md, clean up scratch artifacts, and walk the registration checklist.

## Improve-existing mode differences

When `{{MODE}} == IMPROVE_EXISTING`:
- **Target path:** the existing `skills/{{PEER_NAME}}/` (edit in place, not new scaffold).
- **Pre-filled answers** describe the *extension*, not a new skill.
- Otherwise identical: same voice rules, same full workflow, same scratch-artifact cleanup.
