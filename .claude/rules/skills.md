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

## SKILL.md frontmatter must be valid YAML

Hosts parse the frontmatter with YAML parsers; a strict one drops a skill it can't parse. Quote a one-line value that contains `: ` or ` #`, or starts with a YAML indicator (a quote, `[`, `{`, `>`, `|`, `*`, `&`, `!`, `%`, `@`, a backtick):

```yaml
description: "Connect warehouses with API v2 tools: show what exists, then create connections."
```

Unquoted, the first `: ` is a parse error and ` #` silently cuts the value short. CI runs `python3 scripts/check_skill_frontmatter.py` (PyYAML), which also requires `name` and `description`; run it before committing.

## MCP tool names in skill docs must use snake_case

When referencing Monte Carlo MCP tools in skill files (SKILL.md, references/*.md, patterns), always use snake_case matching the actual tool names — not camelCase.

**Correct:**
```
get_alerts(...)
run_troubleshooting_agent(...)
get_asset_lineage(...)
get_asset(...)
get_monitors(...)
get_queries(...)
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

Each client adds its own prefix to an MCP tool's name (Claude Code `mcp__<server>__<tool>`, CoCo Desktop `mcp_<server label cut to 13 characters>_<tool>`, opencode `<server>_<tool>`), but the operation name is always snake_case. Name operations bare in skill files; never write a client's prefixed form (see the routing section below). Using camelCase causes the agent to hallucinate tool names that don't exist.

## Route Monte Carlo MCP calls

Skills under `skills/` are read by every editor plugin, by standalone installs (`npx skills add`, a copied directory) and by anything that copies a skill into a prompt, such as the MCP server's prompt renderer and MC Companion. Each client names the same Monte Carlo tool differently, so a skill that names one client's tool-ID format sends every other client looking for a tool that doesn't exist. Not every reader has a toolkit-provided connection either: Copilot's installer registers the server in user config, and standalone users configure their own `monte-carlo-mcp` at `/mcp`.

A session can also hold more than one Monte Carlo connection, for example the plugin's and one the user configured, possibly for a different account or with different credentials. This cannot be hard-blocked per skill: `allowed-tools` frontmatter only *pre-approves* tools (suppresses prompts) — it does **not** restrict which tools are callable. Soft enforcement via skill prose is the realistic ceiling.

**Portable skills:** Keep host-specific routing in the plugin command adapter, outside the shared skill and references. The onboarding skill uses this arrangement; its shared content verifies the intended account and uses operation names without host prefixes.

**Rule for legacy plugin-specific skills:** Every `SKILL.md` that calls Monte Carlo MCP tools must include the routing block below, placed near the top of the router (right after the intro paragraph, or as a note under the "MCP Tools Used" heading). The first paragraph applies to every reader and stays outside the markers. The second applies only with the toolkit plugin or its installer and stays inside them. This file is the single source of truth for the block text.

```markdown
> **Monte Carlo tool routing (required):** For Monte Carlo operations such as `get_alerts`, `search`
> and `get_asset`, use the tool ID your client exposes on the connection for the intended account.
> Proceed when there is one suitable connection and no evidence of an account or source mismatch. If
> the choice is ambiguous, ask which connection to use before making a Monte Carlo call; if you can't
> get an answer, leave the call pending. Use the selected connection throughout. If it is unavailable
> or lacks the operation, follow this skill's fallback where it has one, or report what is missing.

<!-- plugin-only:start -->
> **With the Agent Toolkit plugin:** When using the toolkit plugin or its installer, prefer the
> connection it provides or configures (normally named `monte-carlo-mcp`) when it is suitable for the
> intended account. If you know that connection is missing, confirm the intended alternative before
> using another one.
<!-- plugin-only:end -->
```

The example operations (`` `get_alerts`, `search` and `get_asset` ``) may be replaced with operations the skill calls, so a skill never offers one it must not use; everything else stays verbatim (line breaks may differ). `scripts/tests/test_skill_tool_routing.py` enforces the block, lists the skills that must carry it, and fails on any client-specific tool ID anywhere under `skills/`. When adding a skill that calls Monte Carlo MCP tools, add the block and the skill to that test's `ROUTED_SKILLS`.

## Mark plugin-only sections with portability markers

Slash commands, hook behaviour and "use the Read tool on `references/…`" instructions only work inside an editor plugin. A renderer that turns `SKILL.md` into a prompt for clients without the plugin drops marked passages, so wrap those passages in a line-anchored, non-nesting HTML comment pair. Raw readers (standalone installs, MC Companion) still see marked text, so word it to be harmless without the plugin:

```markdown
<!-- plugin-only:start -->
…plugin-only text…
<!-- plugin-only:end -->
```

Text outside the markers must stand alone: bare MCP tool names, no slash commands, reference files mentioned by relative path (the renderer inlines those mentioned outside the markers). Full contract: `CONTRIBUTING.md § Portability markers for plugin-only sections`.

## Create symlinks in all editor plugins when adding a skill

Every skill in `skills/` must have a corresponding symlink in **every** editor plugin's `skills/` directory:

- `plugins/claude-code/skills/<name> → ../../../skills/<name>`
- `plugins/cursor/skills/<name> → ../../../skills/<name>`
- `plugins/codex/skills/<name> → ../../../skills/<name>`
- `plugins/copilot/skills/<name> → ../../../skills/<name>`
- `plugins/opencode/skills/<name> → ../../../skills/<name>`
- `plugins/cortex-code/skills/<name> → ../../../skills/<name>`

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
