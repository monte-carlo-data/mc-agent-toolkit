---
description: Rules for authoring agent skills in mc-agent-toolkit
paths:
  - "skills/**"
---

# Skill Authoring Rules

## SKILL.md description must be ≤250 characters

The `description` field in a skill's SKILL.md frontmatter must be a single line of 250 characters or fewer. This field is used as a skill selector in editor UIs and MCP registries — long descriptions get truncated or rejected.

**Good:**
```yaml
description: Investigate and remediate data quality alerts using Monte Carlo MCP tools. Runs root cause analysis, assesses blast radius, discovers available tools, proposes and executes fixes.
```

**Bad (multi-line or >250 chars):**
```yaml
description: |
  Activates when a user asks to remediate, fix, or respond to a data quality alert
  or incident. Investigates the alert using Monte Carlo MCP tools...
```

Always count characters before committing. A quick check: `echo -n "your description" | wc -c`.

## MCP tool names in skill docs must use snake_case

When referencing Monte Carlo MCP tools in skill files (SKILL.md, references/*.md, patterns), always use snake_case matching the actual tool names — not camelCase.

**Correct:**
```
get_alerts(...)
run_troubleshooting_agent(...)
get_asset_lineage(...)
get_table(...)
get_monitors(...)
get_queries_for_table(...)
get_troubleshooting_agent_results(...)
create_or_update_alert_comment(...)
update_alert(...)
set_alert_owner(...)
```

**Wrong:**
```
getAlerts(...)
runTroubleshootingAgent(...)
getAssetLineage(...)
```

The actual MCP tool names follow the `mcp__<server>__<tool_name>` convention where `tool_name` is always snake_case. Using camelCase causes the agent to hallucinate tool names that don't exist.

## Create symlinks in all editor plugins when adding a skill

Every skill in `skills/` must have a corresponding symlink in **every** editor plugin's `skills/` directory:

- `plugins/claude-code/skills/<name> → ../../../skills/<name>`
- `plugins/cursor/skills/<name> → ../../../skills/<name>`
- `plugins/codex/skills/<name> → ../../../skills/<name>`
- `plugins/copilot/skills/<name> → ../../../skills/<name>`
- `plugins/opencode/skills/<name> → ../../../skills/<name>`

Without these symlinks, the skill won't be discovered by the editor plugin — even if it exists in `skills/` and is listed in the READMEs.

**Verify after adding:** count the directories in `skills/` (excluding `README.md`) and confirm each editor plugin's `skills/` directory has the same count of symlinks.

## Use the 3-tier instruction style for skill content

Skill content follows a 3-tier voice/style convention. Each tier serves a different purpose and reads differently:

- **Tier 1 — SKILL.md (router/workflow):** Procedural and workflow-heavy. Guides the LLM through decision-making ("what kind of request is this?") and high-level flows. Softer recommendations, focus on routing and sequencing. No per-parameter DO/DON'T rules here.
- **Tier 2 — creation procedure references (e.g. `data-monitor-creation.md`):** Procedural but domain-specific. Keeps the investigation/creation flow (steps, phases) in a readable sequence. Does NOT embed per-type constraints — those live in Tier 3.
- **Tier 3 — per-type references (e.g. `data-metric-monitor.md`):** Constraint-heavy with `NEVER`, `CRITICAL`, and `IMPORTANT` callouts. "Common mistakes" sections. All logical DO/DON'T rules live here because one wrong parameter means a broken monitor. Being explicit about what NOT to do matters most at this level.

When adding new reference content, place constraints at the right tier. A rule about "never guess column names" belongs in a Tier 3 per-type file, not in the Tier 1 router.

## Keep READMEs in sync when adding or renaming skills

When adding a new skill or renaming an existing one, update the skill tables in **both**:

1. `README.md` (root) — the Features table
2. `skills/README.md` — the Available Skills table

These are the two places users discover skills. A skill that exists but isn't listed in both READMEs is effectively invisible.
