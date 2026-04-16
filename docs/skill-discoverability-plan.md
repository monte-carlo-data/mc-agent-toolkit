# Skill Discoverability & Proactive Routing for mc-agent-toolkit

## Background & Problem Statement

The mc-agent-toolkit plugin bundles 12 Monte Carlo data observability skills for AI coding agents. The plugin was originally designed around the `prevent` skill, which uses editor hooks (pre-edit, post-edit, pre-commit, turn-end) to proactively enforce impact assessment workflows before dbt model changes. This works well for `prevent` because its nature is to gate dangerous actions.

The remaining 11 skills are passive — they only activate if the agent happens to load their SKILL.md. Each skill defines "When to activate" trigger phrases, but the agent must already know the skill exists to check those triggers. There is no plugin-level routing layer, no catalog command, and only 4 of 12 skills have slash commands.

As Monte Carlo moves more functionality from the traditional webapp into coding sessions, the number of skills will grow. Users need a way to:
1. **Discover** what skills are available
2. **Get routed** to the right skill based on their context and question
3. **Follow natural workflows** that chain related skills together

### What we studied

We researched [claude-buddy](https://github.com/rsts-dev/claude-buddy-marketplace), a Claude Code plugin that uses a purely prompt-driven architecture (no hooks, no executable code) to orchestrate development workflows through "personas" and "domains." Key takeaways:

- **Thin commands → Skills → Workflows**: Commands are 2-line markdown entry points. Skills handle routing. Workflows contain step-by-step instructions. This three-layer separation works well.
- **Domain detection**: claude-buddy auto-detects the project's tech stack (React, JHipster, etc.) using confidence-scored rules, then customizes all behavior accordingly. We can adapt this as "context detection" for data observability scenarios.
- **Workflow-driven orchestration**: claude-buddy's 7 commands follow a sequential pipeline (spec → plan → implement → commit). Our skills are more situational than sequential, but some skills DO form natural workflows (e.g., triage → root-cause → remediation).
- **100% prompt-driven**: claude-buddy achieves sophisticated routing entirely through markdown instructions. This validates using a CLAUDE.md routing table + skill files rather than building hook-based suggest mechanisms.

### Design decisions made

- **Not all skills need to be in a workflow cluster.** Some are standalone tools (generate-validation-notebook, push-ingestion) or self-managing (prevent with its hooks).
- **Workflow clusters should be workflow-driven** with orchestration logic, not just categorization. Each workflow is itself a skill (a SKILL.md file) that knows the sequence and transitions.
- **Context detection should be a dedicated skill**, referenced by CLAUDE.md, that probes the environment and suggests the right workflow or standalone skill.
- **Orchestration is prompt-driven (light prescription)** — no hooks or state tracking for workflows. Hooks remain exclusive to `prevent`.
- **A turn-end "suggest" hook was considered and deferred.** The current hook architecture only supports `block` semantics (forces the agent to keep working). A non-blocking suggestion would require platform changes. The prompt-driven context detection achieves the same goal without this limitation.

---

## Guardrail: Protect `prevent` Skill's Hook-Based Proactivity

The `prevent` skill is the single most important skill in the toolkit. Its hook-based enforcement (pre-edit gating, post-edit tracking, pre-commit blocking, turn-end validation reminders) is a critical safety mechanism that prevents engineers from making unassessed changes to dbt models.

**Nothing in this plan may regress or interfere with `prevent`'s hooks.** Specifically:

1. **Do not modify `hooks/prevent/hooks.json` or any file in `plugins/shared/prevent/lib/`.** The hook registration and shared logic are off-limits.
2. **The new `CLAUDE.md` must not override or conflict with `prevent`'s SKILL.md instructions.** The routing table should direct dbt-model-edit scenarios to `prevent` and explicitly note that `prevent` auto-activates via hooks — no manual invocation needed.
3. **Context detection must defer to `prevent` for dbt change scenarios.** If the context detection skill detects a dbt project and the user is editing models, it should say "the `prevent` skill will automatically activate via hooks" — not try to route to a workflow.
4. **Workflow skills must not re-orchestrate `prevent`'s workflows.** The incident-response and proactive-monitoring workflows reference `monitor-creation` as a terminal step, but they must never attempt to replicate or replace `prevent`'s Workflow 2 (monitor generation) or Workflow 4 (change impact assessment).
5. **Test `prevent` end-to-end after every change.** Verification must include: (a) editing a dbt model triggers the pre-edit hook and blocks until impact assessment runs, (b) `git commit` with modified dbt models triggers the pre-commit hook, (c) turn-end hook injects validation reminders for edited models. If any of these regress, the change must be reverted.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│  CLAUDE.md  (auto-loaded on session start)              │
│  - References context-detection skill                   │
│  - Compact routing table (intent → skill/workflow)      │
│  - Lists all /mc-* commands                             │
└──────────────┬──────────────────────────────────────────┘
               │ "When user's request relates to data
               │  observability, activate context detection"
               ▼
┌─────────────────────────────────────────────────────────┐
│  Context Detection Skill                                │
│  skills/context-detection/SKILL.md                      │
│  - Inspects workspace (dbt_project.yml, file types)     │
│  - Probes MC API (active alerts, coverage gaps)         │
│  - Maps signals → workflow or standalone skill           │
│  - SUGGESTS, does not auto-activate                     │
└──────┬──────────────────┬───────────────────────────────┘
       │                  │
       ▼                  ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────────┐
│  Workflow:   │   │  Workflow:   │   │  Standalone       │
│  Incident    │   │  Proactive   │   │  Skills:          │
│  Response    │   │  Monitoring  │   │  - prevent        │
│              │   │              │   │  - gen-val-nb     │
│  triage →    │   │  health →    │   │  - push-ingestion │
│  root-cause →│   │  advisor →   │   │  - storage-cost   │
│  remediation │   │  monitor-    │   │  - perf-diagnosis │
│  → monitor   │   │  creation    │   │  - agent-monitor  │
└──────────────┘   └──────────────┘   └──────────────────┘

All skills remain individually invokable via /mc-* commands.
```

---

## Skill Classification

### Workflow-orchestrated skills

These skills form natural sequential workflows. They remain individually invokable, but also participate in a coordinated workflow when entered through the workflow skill.

**Incident Response Workflow** (`skills/incident-response/SKILL.md`):
```
Alert or data issue detected
  → automated-triage    (classify severity, identify affected assets)
  → analyze-root-cause  (investigate why — lineage, ETL, query changes)
  → remediation         (fix the issue or escalate with context)
  → monitor-creation    (add monitoring to prevent recurrence)
```

**Proactive Monitoring Workflow** (`skills/proactive-monitoring/SKILL.md`):
```
User wants to improve monitoring coverage
  → asset-health        (assess current state of key tables)
  → monitoring-advisor  (identify gaps across the estate)
  → monitor-creation    (create monitors for identified gaps)
```

Note: `monitor-creation` is the terminal step of both workflows. It is also standalone-invokable for users who already know what monitor they want to create.

### Standalone skills

These skills are individually triggered and don't participate in a workflow cluster:

| Skill | Why standalone |
|---|---|
| `prevent` | Self-managing via editor hooks. Auto-activates on dbt model edits. |
| `generate-validation-notebook` | Isolated utility — user triggers directly when they need validation SQL. |
| `push-ingestion` | Isolated utility — user triggers when setting up data collection scripts. |
| `storage-cost-analysis` | Investigative — user triggers when exploring cost optimization. |
| `performance-diagnosis` | Investigative — user triggers when diagnosing slow pipelines. |
| `agent-monitoring` | Specialized — user triggers for AI agent observability. |

---

## Implementation Plan

### Part 1: Plugin-level CLAUDE.md with routing table

**What:** Create a `CLAUDE.md` at the claude-code plugin root that is auto-loaded on every session. It acts as the agent's "knowledge base" of what the toolkit can do.

**File:** `plugins/claude-code/CLAUDE.md`

**Content structure (keep under ~80 lines to minimize context overhead):**

```markdown
# Monte Carlo Agent Toolkit

This plugin provides data observability skills powered by Monte Carlo.

## Context Detection

When a user's request relates to data quality, monitoring, incidents, alerts,
pipeline issues, or Monte Carlo — activate the context-detection skill at
`skills/context-detection/SKILL.md` to determine which skill or workflow to
recommend.

## Quick Routing Table

| User intent | Route to |
|---|---|
| Alert firing, data broken, incident | **Incident Response workflow** (`skills/incident-response/SKILL.md`) |
| "What should I monitor?", coverage gaps | **Proactive Monitoring workflow** (`skills/proactive-monitoring/SKILL.md`) |
| Create a specific monitor | `monitor-creation` skill |
| Editing a dbt model or SQL file | `prevent` skill (auto-activates via hooks) |
| "Check health of table X" | `asset-health` skill |
| Generate validation SQL | `generate-validation-notebook` skill |
| Set up data collection / push ingestion | `push-ingestion` skill |
| Storage costs, unused tables | `storage-cost-analysis` skill |
| Slow pipeline, expensive queries | `performance-diagnosis` skill |
| AI agent monitoring | `agent-monitoring` skill |

## Available Commands

Users can invoke any skill directly:
- `/mc` — List all skills and workflows
- `/mc-incident` — Start incident response workflow
- `/mc-monitoring` — Start proactive monitoring workflow
- `/mc-health` — Check table health
- `/mc-triage` — Set up automated triage
- `/mc-root-cause` — Investigate a data incident
- `/mc-remediate` — Fix a data quality alert
- `/mc-monitor` — Create a monitor
- `/monitoring-advisor` — Analyze coverage gaps
- `/mc-validate` — Generate validation queries
- `/mc-notebook` — Generate validation notebook
- `/mc-storage` — Analyze storage costs
- `/mc-perf` — Diagnose pipeline performance
- `/mc-agent-monitor` — AI agent observability
- `/mc-build-*` — Push ingestion commands (existing)
```

**Cross-editor equivalents:**
- `plugins/cursor/.cursorrules` — Same content, adapted for Cursor's format
- Other editors (Copilot, Codex, OpenCode) — Reference from their config if they support an instructions mechanism. If not, the context-detection skill alone still provides routing.

### Part 2: Context Detection Skill

**What:** A new skill that inspects the environment and conversation to recommend the right skill or workflow. This is what makes the toolkit proactive without hooks.

**File:** `skills/context-detection/SKILL.md`

**Key design: the skill SUGGESTS, it does not auto-activate other skills.** It produces a recommendation that the agent presents to the user. This keeps the user in control while making the toolkit smart.

**Trigger conditions (in SKILL.md "When to activate"):**
- The CLAUDE.md routing table directs the agent here when a request relates to data observability
- User mentions Monte Carlo, data quality, monitoring, alerts, or related topics
- User opens a project with `dbt_project.yml` or MC configuration

**Detection logic (three signal tiers):**

**Tier 1 — Workspace signals (high reliability, deterministic):**
- `dbt_project.yml` exists → suggest `prevent` skill is available for dbt model changes
- `.sql` files in working directory → note SQL-centric project
- Monte Carlo config files present → note MC integration

**Tier 2 — MC API signals (high reliability, requires auth):**
- Call `get_alerts` for recent alerts → if active alerts exist, suggest **Incident Response workflow**
- Call a lightweight coverage check → if significant gaps, suggest **Proactive Monitoring workflow**
- If MC MCP is not authenticated, skip this tier gracefully and note that auth is needed

**Tier 3 — Conversation signals (medium reliability, intent inference):**
- User mentions "alert", "incident", "broken", "stale", "failing" → suggest **Incident Response workflow**
- User mentions "monitor", "coverage", "gaps", "what should I watch" → suggest **Proactive Monitoring workflow**
- User mentions specific table + "health", "status", "check" → suggest `asset-health`
- User mentions "cost", "storage", "unused tables" → suggest `storage-cost-analysis`
- User mentions "slow", "performance", "expensive query" → suggest `performance-diagnosis`

**Output format:** The skill produces a brief recommendation:
```
Based on [signals detected], I recommend:
- [Primary recommendation]: [workflow or skill name] — [why]
- [Optional secondary]: [skill name] — [why]

You can also run /mc to see all available skills.
```

**Accuracy safeguards:**
- Tier 1+2 signals take precedence over Tier 3 conversation signals
- When confidence is low (only Tier 3 signals, ambiguous intent), present options rather than a single recommendation
- Never auto-run a workflow — always present the recommendation and let the user confirm
- If no signals match, show the `/mc` catalog rather than guessing

**Reference file:** `skills/context-detection/references/signal-definitions.md` — Documents each signal, its source, reliability tier, and what it maps to. This is the file future skill developers update when adding a new skill.

### Part 3: Workflow Skills

Two new skills that orchestrate related skills into sequential workflows.

#### 3a. Incident Response Workflow

**File:** `skills/incident-response/SKILL.md`

**When to activate:**
- Context detection routes here based on active alerts or incident-related conversation
- User invokes `/mc-incident`
- User explicitly asks to "respond to an incident", "handle this alert", "triage and fix"

**Trigger conditions (for context detection to use):**
- MC API: `get_alerts` returns alerts with status != resolved in last 24h
- Conversation: user mentions alert ID, incident, "data is broken/stale/wrong", "pipeline failed"
- Workspace: user is in a repo with dbt models AND has active MC alerts (combined signal)

**Orchestration logic (prompt-driven):**

```markdown
## Workflow Steps

### Step 1: Triage (automated-triage skill)
Read and activate `../automated-triage/SKILL.md`.
Goal: Classify the alert(s) by severity and identify affected assets.
Move to Step 2 when: severity and affected assets are identified.
Skip this step when: user already knows the specific alert/table they want to investigate.

### Step 2: Root Cause Analysis (analyze-root-cause skill)
Read and activate `../analyze-root-cause/SKILL.md`.
Goal: Investigate why the issue occurred — lineage, ETL changes, query changes, data profiling.
Move to Step 3 when: root cause is identified or investigation reaches its limit.
Skip this step when: user already knows the root cause and wants to jump to remediation.

### Step 3: Remediation (remediation skill)
Read and activate `../remediation/SKILL.md`.
Goal: Fix the issue using available tools, or escalate with full context if uncertain.
Move to Step 4 when: fix is applied and verified, OR escalation is documented.

### Step 4: Prevent Recurrence (monitor-creation skill)
Read and activate `../monitor-creation/SKILL.md`.
Goal: Add or update monitors to detect this class of issue in the future.
This step is optional — offer it, but don't force it.

## Entry Points
Users can enter at any step. Ask which step to start from if the context is ambiguous.
If the user already has an alert ID, skip triage and start at Step 2.
If the user says "fix this", start at Step 3 if root cause is already known.
```

#### 3b. Proactive Monitoring Workflow

**File:** `skills/proactive-monitoring/SKILL.md`

**When to activate:**
- Context detection routes here based on coverage gaps or monitoring-related conversation
- User invokes `/mc-monitoring`
- User asks "what should I monitor?", "where are my gaps?", "improve coverage"

**Trigger conditions (for context detection to use):**
- MC API: coverage analysis shows significant unmonitored critical tables
- Conversation: user mentions "coverage", "gaps", "what should I monitor", "unmonitored"
- Workspace: new dbt project with no MC monitors configured yet

**Orchestration logic (prompt-driven):**

```markdown
## Workflow Steps

### Step 1: Assess Current State (asset-health skill)
Read and activate `../asset-health/SKILL.md`.
Goal: Check health of key tables the user cares about. Surface freshness, alerts, existing coverage.
Move to Step 2 when: user wants a broader view beyond individual tables.
Skip this step when: user already wants estate-wide coverage analysis.

### Step 2: Identify Gaps (monitoring-advisor skill)
Read and activate `../monitoring-advisor/SKILL.md`.
Goal: Analyze coverage across warehouses/use cases, identify what's unmonitored, prioritize by importance.
Move to Step 3 when: gaps are identified and user wants to create monitors.

### Step 3: Create Monitors (monitor-creation skill)
Read and activate `../monitor-creation/SKILL.md`.
Goal: Create monitors-as-code YAML for the identified gaps.

## Entry Points
Users can enter at any step.
If the user asks about a specific table, start at Step 1.
If the user asks about overall coverage, start at Step 2.
If the user already knows what monitors to create, start at Step 3.
```

### Part 4: Slash Commands for All Skills

Create slash commands for all skills and workflows so users get autocomplete-based discovery when typing `/mc-`.

**New command files to create** (in `plugins/claude-code/commands/`):

| Command | File | Body |
|---|---|---|
| `/mc` | `commands/catalog/mc.md` | Full skill catalog with descriptions and example trigger phrases |
| `/mc-incident` | `commands/incident-response/mc-incident.md` | "Read and execute the Incident Response workflow at `skills/incident-response/SKILL.md`" |
| `/mc-monitoring` | `commands/proactive-monitoring/mc-monitoring.md` | "Read and execute the Proactive Monitoring workflow at `skills/proactive-monitoring/SKILL.md`" |
| `/mc-health` | `commands/asset-health/mc-health.md` | "Read and execute the Asset Health skill at `skills/asset-health/SKILL.md`" |
| `/mc-root-cause` | `commands/analyze-root-cause/mc-root-cause.md` | "Read and execute the Root Cause Analysis skill at `skills/analyze-root-cause/SKILL.md`" |
| `/mc-remediate` | `commands/remediation/mc-remediate.md` | "Read and execute the Remediation skill at `skills/remediation/SKILL.md`" |
| `/mc-monitor` | `commands/monitor-creation/mc-monitor.md` | "Read and execute the Monitor Creation skill at `skills/monitor-creation/SKILL.md`" |
| `/mc-notebook` | `commands/generate-validation-notebook/mc-notebook.md` | "Read and execute the Generate Validation Notebook skill at `skills/generate-validation-notebook/SKILL.md`" |
| `/mc-storage` | `commands/storage-cost-analysis/mc-storage.md` | "Read and execute the Storage Cost Analysis skill at `skills/storage-cost-analysis/SKILL.md`" |
| `/mc-perf` | `commands/performance-diagnosis/mc-perf.md` | "Read and execute the Performance Diagnosis skill at `skills/performance-diagnosis/SKILL.md`" |
| `/mc-agent-monitor` | `commands/agent-monitoring/mc-agent-monitor.md` | "Read and execute the Agent Monitoring skill at `skills/agent-monitoring/SKILL.md`" |

**Existing commands to keep as-is:**
- `/mc-validate` (prevent)
- `/monitoring-advisor` (monitoring-advisor) — consider aliasing to `/mc-advisor` for consistency
- `/mc-triage` (automated-triage)
- `/mc-build-*` (push-ingestion family)

**Command file format** (follows existing pattern, e.g., `commands/prevent/mc-validate.md`):
```markdown
---
description: One-line description for autocomplete UI
---

Read and execute the [Skill Name] skill at `skills/<name>/SKILL.md`.
**User provided input**: $ARGUMENTS
```

**Update `plugin.json`:** Add all new command directories to the `commands` array.

### Part 5: Skill Chaining (Recommended Follow-ups)

Add a `## Recommended follow-ups` section to each existing skill's SKILL.md. This creates a workflow graph that users learn through use, and helps the agent suggest the next step after completing a skill.

**Additions per skill:**

| Skill | Follow-up recommendations |
|---|---|
| `asset-health` | "If coverage gaps found → `monitoring-advisor` or `monitor-creation`. If active alerts → `analyze-root-cause`." |
| `monitoring-advisor` | "To create recommended monitors → `monitor-creation`." |
| `monitor-creation` | (Terminal skill — no follow-up needed) |
| `automated-triage` | "To investigate root cause → `analyze-root-cause`. To fix → `remediation`." |
| `analyze-root-cause` | "To fix the identified issue → `remediation`. To add monitoring → `monitor-creation`." |
| `remediation` | "To prevent recurrence → `monitor-creation`." |
| `prevent` | "After changes → `generate-validation-notebook` for broader validation." |
| `storage-cost-analysis` | "To monitor tables marked for cleanup → `monitor-creation`." |
| `performance-diagnosis` | "To monitor identified bottlenecks → `monitor-creation`." |

### Part 6: Maintenance Rules

Update `.claude/rules/skills.md` to add rules for future skill developers:

```markdown
## Update routing when adding a skill

When adding a new skill:
1. Decide: does this skill belong in an existing workflow cluster, or is it standalone?
2. If workflow-clustered: update the relevant workflow SKILL.md orchestration logic
3. Update `plugins/claude-code/CLAUDE.md` routing table with the new skill
4. Update `skills/context-detection/references/signal-definitions.md` with trigger signals
5. Create a slash command in `plugins/claude-code/commands/<skill>/mc-<name>.md`
6. Update the `/mc` catalog command to include the new skill
7. Add `## Recommended follow-ups` to the new skill's SKILL.md
```

---

## New Files Summary

```
skills/
  context-detection/
    SKILL.md                          # Context detection skill
    references/
      signal-definitions.md           # Signal → skill/workflow mapping
  incident-response/
    SKILL.md                          # Incident response workflow orchestration
  proactive-monitoring/
    SKILL.md                          # Proactive monitoring workflow orchestration

plugins/claude-code/
  CLAUDE.md                           # Plugin-level routing instructions (auto-loaded)
  commands/
    catalog/mc.md                     # /mc catalog command
    incident-response/mc-incident.md  # /mc-incident
    proactive-monitoring/mc-monitoring.md  # /mc-monitoring
    asset-health/mc-health.md         # /mc-health
    analyze-root-cause/mc-root-cause.md   # /mc-root-cause
    remediation/mc-remediate.md       # /mc-remediate
    monitor-creation/mc-monitor.md    # /mc-monitor
    generate-validation-notebook/mc-notebook.md  # /mc-notebook
    storage-cost-analysis/mc-storage.md   # /mc-storage
    performance-diagnosis/mc-perf.md  # /mc-perf
    agent-monitoring/mc-agent-monitor.md  # /mc-agent-monitor
```

## Modified Files Summary

```
plugins/claude-code/.claude-plugin/plugin.json   # Add new command dirs to commands array
skills/asset-health/SKILL.md                     # Add ## Recommended follow-ups
skills/monitoring-advisor/SKILL.md               # Add ## Recommended follow-ups
skills/automated-triage/SKILL.md                 # Add ## Recommended follow-ups
skills/analyze-root-cause/SKILL.md               # Add ## Recommended follow-ups
skills/remediation/SKILL.md                      # Add ## Recommended follow-ups
skills/prevent/SKILL.md                          # Add ## Recommended follow-ups
skills/storage-cost-analysis/SKILL.md            # Add ## Recommended follow-ups
skills/performance-diagnosis/SKILL.md            # Add ## Recommended follow-ups
.claude/rules/skills.md                          # Add routing update rules
```

Don't forget: new skills (`context-detection`, `incident-response`, `proactive-monitoring`) need symlinks in ALL 5 editor plugin `skills/` directories per existing rules in `.claude/rules/skills.md`.

---

## Verification Plan

1. **CLAUDE.md loads on session start:** Install the plugin locally, start a new Claude Code session, verify CLAUDE.md content appears in the agent's context.

2. **`/mc` catalog works:** Type `/mc`, verify it lists all skills and workflows with descriptions.

3. **Autocomplete discovery:** Type `/mc-` and verify all skill commands appear in autocomplete.

4. **Context detection — workspace signals:** Open a dbt project with `dbt_project.yml`, start a session, ask a vague data quality question. Verify the agent activates context detection and recommends relevant skills.

5. **Context detection — API signals:** With MC MCP authenticated and active alerts present, start a session and ask "what's going on with my data?" Verify the agent suggests the Incident Response workflow.

6. **Context detection — conversation signals:** Without any workspace or API signals, say "I want to improve my monitoring coverage." Verify the agent suggests the Proactive Monitoring workflow.

7. **Workflow orchestration:** Run `/mc-incident`, verify it walks through triage → root-cause → remediation → monitor-creation in sequence with appropriate transition prompts.

8. **Entry at any step:** Run `/mc-incident` and say "I already know the root cause, the ETL job failed." Verify it skips to remediation (Step 3).

9. **Skill chaining:** Run `/mc-health` for a table, verify the output includes "Recommended follow-ups" suggesting monitoring-advisor or analyze-root-cause based on findings.

10. **Cross-editor:** Repeat key checks (1, 2, 3) for the Cursor plugin.

---

## Implementation Order

Recommended sequence for the implementing engineer:

1. **Part 4 first (slash commands)** — Lowest risk, immediate value. Creates the `/mc-*` commands and `/mc` catalog. This is independently shippable.

2. **Part 5 (skill chaining)** — Add `## Recommended follow-ups` to existing SKILL.md files. Also independently shippable.

3. **Part 1 (CLAUDE.md)** — Create the plugin-level routing instructions. Shippable with Parts 1+4 together for best effect.

4. **Part 3 (workflow skills)** — Create the two workflow skills. Depends on understanding the existing skills well. Test orchestration thoroughly.

5. **Part 2 (context detection)** — The most nuanced piece. Depends on workflow skills existing. Requires testing against real MC environments with active alerts, coverage gaps, etc. to validate accuracy.

6. **Part 6 (maintenance rules)** — Update `.claude/rules/skills.md`. Do this alongside or after Part 2.
