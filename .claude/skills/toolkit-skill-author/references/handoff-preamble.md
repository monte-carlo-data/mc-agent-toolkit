# Handoff preamble for Anthropic's `skill-creator`

This is the template `toolkit-skill-author` uses when invoking Anthropic's `skill-creator` via the `Skill` tool. Claude fills in the bracketed placeholders from survey answers.

## Template

You are being invoked by mc-agent-toolkit's `/toolkit-skill-author` with pre-collected context.
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
- Bucket: {{BUCKET}} (also emitted as the `bucket` frontmatter field — see below)

**MC-specific voice and length rules (override your defaults):**
- `description` ≤ 1,024 characters.
- Combined `description` + `when_to_use` ≤ 1,400 characters (headroom under the 1,536 truncation ceiling).
- Third-person voice. Describe what the skill does, not what "this skill" does.
- Do **not** open with "This skill…" or "Use this skill when…".
- Do **not** use the "pushy" voice pattern ("Make sure to use this skill whenever…"); use concrete triggers instead.

**Required frontmatter fields (and fields NOT to emit):**
- `name`: `monte-carlo-{{NAME}}` — canonical prefixed form; `{{NAME}}` is the directory name.
- `description`: per the length rule above.
- `when_to_use`: required (not optional).
- `bucket`: `{{BUCKET}}` — one of Trust / Incident Response / Monitoring / Prevent / Optimize / Setup. Tracks which capability bucket the skill belongs to in the public docs.
- Do **not** emit a `version` field. Versions live in the plugin manifests (`plugins/*/.*-plugin/plugin.json`), not in SKILL.md. `toolkit-skill-author` will bump them separately via `scripts/bump-version.sh` after you return.

**Eval artifacts are scratch, not shipped:**
- Your `skills/{{NAME}}/evals/evals.json` and sibling `skills/{{NAME}}-workspace/` drive the iteration loop but are not the repo's eval format. `toolkit-skill-author` will delete them after you return.
- mc-agent-toolkit's real evals live at `plugins/claude-code/evals/{{NAME}}/live-evals-dev.yaml` — a YAML schema with `cases: [{ id, turns: [{ prompt, criteria: { must_call, must_not_call } }], criteria: { judge_rubric } }]`. Authoring that file is handled by `toolkit-skill-author` in the registration checklist — don't attempt to write it yourself, and don't produce a `trigger-evals.json` or any JSON variant.

**When done:** return control to `toolkit-skill-author`. It will lint the generated SKILL.md, clean up scratch artifacts, and walk the registration checklist.

## Improve-existing mode differences

When `{{MODE}} == IMPROVE_EXISTING`:
- **Target path:** the existing `skills/{{PEER_NAME}}/` (edit in place, not new scaffold).
- **Pre-filled answers** describe the *extension*, not a new skill.
- Otherwise identical: same voice rules, same full workflow, same scratch-artifact cleanup.
