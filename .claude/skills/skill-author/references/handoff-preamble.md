# Handoff preamble for Anthropic's `skill-creator`

This is the template `skill-author` uses when invoking Anthropic's `skill-creator` via the `Skill` tool. Claude fills in the bracketed placeholders from survey answers.

## Template

You are being invoked by mcd-agent-toolkit's `/skill-author` with pre-collected context.
**Use the pre-filled answers below. Minimize follow-up questions. Do not run your eval/iterate loop — this repo uses a separate evals framework.**

**Mode:** {{NEW_SKILL | IMPROVE_EXISTING}}

**Target path:** `skills/{{NAME}}/` in the mcd-agent-toolkit repo (not your default workspace).

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
- `name` is kebab-case, matches `{{NAME}}`.
- `when_to_use` is required (not optional).

**Scaffold only:**
- Produce `skills/{{NAME}}/SKILL.md` and, if the workflow warrants, `references/` files.
- Do **not** create `evals/evals.json`. MC uses `plugins/claude-code/evals/{{NAME}}/` (handled by `skill-author` post-step).
- Do **not** run subagents, benchmarks, or the A/B description optimizer. `skill-author` orchestrates those separately if at all.

**When done:** return control to `skill-author`. It will lint the generated SKILL.md and walk the registration checklist.

## Improve-existing mode differences

When `{{MODE}} == IMPROVE_EXISTING`:
- **Target path:** the existing `skills/{{PEER_NAME}}/` (edit in place, not new scaffold).
- **Pre-filled answers** describe the *extension*, not a new skill.
- Otherwise identical: same voice rules, skip evals, skip iterate loop.
