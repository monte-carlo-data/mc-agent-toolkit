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

## Route Monte Carlo MCP calls to the plugin-bundled server

The toolkit bundles an MCP server named `monte-carlo-mcp`. When loaded through the plugin, its tools are namespaced **`mcp__plugin_mc-agent-toolkit_monte-carlo-mcp__<tool>`** (the general form is `mcp__plugin_<plugin-name>_<server-name>__<tool>`). If a user has independently configured *another* MCP server also named `monte-carlo-mcp` (or any server exposing same-named tools), both namespaces coexist in the session and a bare tool name like `get_alerts` becomes ambiguous — the model could route to the user's server (different endpoint and credentials) instead of the plugin's.

This cannot be hard-blocked per skill: `allowed-tools` frontmatter only *pre-approves* tools (suppresses prompts) — it does **not** restrict which tools are callable, so listing only the plugin tool does not block a same-named server. Soft enforcement via skill prose is the realistic ceiling.

**Rule:** Every `SKILL.md` that calls Monte Carlo MCP tools must include the routing block below **verbatim**, placed near the top of the router (right after the intro paragraph, or as a note under the "MCP Tools Used" heading). This file is the single source of truth for both the block text and the namespace string.

```markdown
> **Monte Carlo tool routing (required):** Always call Monte Carlo MCP tools through this plugin's
> bundled server, whose fully-qualified tool names are
> `mcp__plugin_mc-agent-toolkit_monte-carlo-mcp__<tool>` (e.g.
> `mcp__plugin_mc-agent-toolkit_monte-carlo-mcp__get_alerts`). Bare tool names used in this skill
> (`get_alerts`, `search`, `get_table`, …) refer to that bundled server. If the session also has a
> separately-configured `monte-carlo-mcp` server, do **not** route to it — it may point at a
> different endpoint or credentials.
```

When the plugin name or server name changes, update the prefix **here and in every skill carrying the block in the same change**. To find them: `grep -rl 'Monte Carlo tool routing (required)' skills/*/SKILL.md`.

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

## Cross-skill hand-offs: the `## Next` convention

When an atomic skill finishes its primary job, it may hand off to the logical next skill so the user
keeps moving through a workflow. This is the toolkit's core value — chaining tools into guided flows —
but it must never nag, loop, or fire into an empty or destructive next step.

**What `## Next` is.** A short, optional section at the **end** of an atomic skill's `SKILL.md`. It is a
*terminal* hand-off — the current skill's work is done and it points to what comes next. This is
**distinct from** the way orchestrators (`incident-response`, `proactive-monitoring`) embed
`**Skill:** Read and follow ../<name>/SKILL.md` *mid-workflow* to sequence steps. Orchestrators are not
changed by this convention and do not get a `## Next`.

**The authoritative chain map lives in [`skills/CHAINING.md`](../../skills/CHAINING.md)** — one row per
skill (`From · Condition · To · Mode`). That file is the single source of truth;
`scripts/validate-next-steps.py` validates every `## Next` section against it (and runs in CI) — the
target must resolve to a real skill, exist in the map, and carry a **mode tag that matches the map**
(a missing or mismatched `**[mode]**` tag is a CI failure, so the confirm gate can't be dropped by
omitting the tag). Update the map there when you add or change a hand-off.

### The three modes

| Mode | Use when | What the `## Next` does |
|------|----------|-------------------------|
| **immediate** | the next skill's inputs are available right now | `Read and follow ../<skill>/SKILL.md` — proceed directly |
| **deferred** | an async/latency dependency must complete first (ingestion landing, trace baselines, a long job) | **State the readiness condition** and point — do **not** auto-invoke: *"Once X appears in `<tool>`, run `<skill>`."* |
| **confirm** | the next skill (or its next phase) **mutates state** (`manage-mac` apply, `remediation`, `tune-monitor` apply, `update_alert`) | Present a summary of the proposed change and **require explicit user approval** before invoking the write. Never auto-execute a mutation. |

Decision order: does it mutate state? → **confirm**. Else, are inputs ready now? → **immediate**, otherwise **deferred**.

### Rules

- **One high-confidence next step**, conditional on the result, plus at most one alternative. **No menus**
  for cross-skill hand-offs. (Intra-skill "what next" menus — iterating on the skill's own output, e.g.
  `automated-triage` refine/test/schedule — are still allowed; just don't duplicate the same target across
  both a menu and a `## Next`.)
- **Data-driven.** Only offer the step the result implies (alerts present → triage; healthy + well-covered →
  nothing). Never a generic "you could also…".
- **Loop-free.** No A→B→A. The validator enforces this against the chain map.
- **Terminal is a valid, correct outcome.** Setup generators, hubs, and a clean/healthy result legitimately
  have no `## Next`. Forcing a step there is the nagging this convention forbids.
- **Findings vs. hand-off (diagnosis vs. disposition).** Many skills already emit a findings /
  recommendations / diagnosis section — that is *diagnosis* (what's wrong, why, including actions outside
  the toolkit like "fix the upstream dbt job"). `## Next` is *disposition* — the single toolkit skill to
  continue into. So `## Next` must **reference** the findings, not **restate** them ("Based on the staleness
  above, run analyze-root-cause?" — not a second copy of the recommendation list), and it is **terminal when
  no recommendation maps to a toolkit skill**. Never present the same proposed action twice (once in the
  findings, once in `## Next`).
- **Conditional on the result — no unconditional hand-offs.** Every `## Next` bullet must name the specific
  result-state that triggers it. Failure, in-progress/troubleshooting, no-findings, and
  not-ready-yet states are **explicit `(terminal)`** lines, not silent omissions. A single bullet that fires
  regardless of outcome (e.g. "after this, run X") is a bug — it will fire on the failure path too.

### Format (so the validator can parse it)

In a `## Next` section, reference each target skill as a relative path — `../<skill-name>/SKILL.md` —
exactly as orchestrators do, and tag the mode in bold. Example:

```markdown
## Next

- If active alerts were found → **[immediate]** investigate them: read and follow `../incident-response/SKILL.md`.
- If the table is under-monitored → **[immediate]** close the gap: read and follow `../monitoring-advisor/SKILL.md`.
- If the table is healthy and well-covered → nothing to do. (terminal)
```
