---
name: monte-carlo-context-detection
description: Route data-related requests to the right Monte Carlo skill or workflow. USE WHEN alerts, incidents, data broken, stale, coverage gaps, data quality, or any ambiguous data observability request.
version: 1.0.0
---

# Monte Carlo Context Detection

This skill determines which Monte Carlo skill or workflow best fits the user's current context. It operates in two modes:

1. **Session-start welcome** — On the first response in a session, check for workspace signals and briefly mention available capabilities.
2. **Reactive routing** — When activated by the CLAUDE.md routing table for ambiguous or multi-step data-related messages, gather signals and route to the right skill or workflow.

Reference file for signal definitions: `references/signal-definitions.md` (relative to this file). Read it before routing.

## When to activate this skill

This skill is activated by the CLAUDE.md routing table when:

- The user's message relates to data quality, alerts, incidents, coverage, or Monte Carlo — but doesn't clearly match a single skill in the routing table
- The user's intent is ambiguous or could span multiple skills
- The user asks a broad question like "help me with my data" or "what's going on?"

## When NOT to activate this skill

- A skill or workflow is already active in the conversation — the active skill owns the conversation, do not intercept
- The user's message clearly matches a single skill in the CLAUDE.md routing table — route directly, no need for context detection
- The user is editing a dbt model — defer to the `prevent` skill which auto-activates via hooks
- The user's message is not data-related at all

---

## Mode 1: Session-Start Welcome

**When:** First response in a session (infer from empty conversation history).

**Action:**
1. Glob for `dbt_project.yml` and `montecarlo.yml` in the workspace root
2. If either exists, append this brief note to your response:

> "I see this is a dbt project with Monte Carlo. If you run into data issues, I can help triage alerts, investigate root causes, and set up monitoring. I'll also flag impact when you edit models. Ask me anything or type `/mc` to see what's available."

**Rules:**
- Brief, natural language — do not list skill names
- Once per session, appended to whatever you're responding about
- Workspace glob only — no API calls
- Silent if neither file is found

---

## Mode 2: Reactive Routing

When activated for an ambiguous or multi-step data-related message, follow these steps in order.

### Step 1: Categorize intent

Read `references/signal-definitions.md` for the full signal catalog. Determine which category the user's message falls into:

| Category | Signals | Example messages |
|----------|---------|-----------------|
| **Specific asset** | User mentions a table name, or has a `.sql` model file open in their IDE | "what's wrong with stg_payments?", "check this table" |
| **Active incident** | Keywords: alert, broken, stale, failing, incident, triage, wrong data | "I have alerts firing", "data looks wrong", "something broke" |
| **Coverage/monitoring** | Keywords: monitor, coverage, gaps, unmonitored, what should I watch | "what should I monitor?", "where are my gaps?" |
| **General/exploratory** | No clear category, broad question | "help me with data quality", "what can Monte Carlo do?" |

### Step 2: Gather scope (only if needed)

- **Specific asset known** (from file context or user mention) → proceed to Step 3
- **Active incident, no scope** → ask: "Want me to check recent alerts? Any specific time range or severity?"
- **Coverage/monitoring, no scope** → ask: "Which warehouse should I look at, or should I check across all?"
- **General/exploratory** → present the categories: "I can help with: (1) investigating active alerts or data issues, (2) analyzing monitoring coverage and creating monitors, or (3) checking the health of specific tables. What are you looking for?"

### Step 3: Scoped API probe (when scope is available)

Only make API calls when you have enough context to scope them:

- **Specific asset** → call `get_alerts` with the table's MCON or name filter, and `get_monitors` for that table
- **Active incident with scope** → call `get_alerts` with the user's time range / severity filters
- **Coverage/monitoring** → skip API probe, route directly to proactive monitoring workflow (it handles its own API calls)
- **If MCP tool calls fail** (auth not configured) → skip API, fall back to conversation intent alone

### Step 4: Route

Based on the combined signals from Steps 1-3:

| Combined signals | Confidence | Action |
|-----------------|------------|--------|
| Active alerts found + incident intent | High | **Auto-activate** incident response workflow: read and follow `../incident-response/SKILL.md` |
| Coverage intent + data project detected | High | **Auto-activate** proactive monitoring workflow: read and follow `../proactive-monitoring/SKILL.md` |
| User asks to create a specific monitor (type + table known) | High | **Auto-activate** monitoring-advisor: read and follow `../monitoring-advisor/SKILL.md` |
| Table mentioned + "health" / "status" / "check" intent | High | **Auto-activate** asset-health: read and follow `../asset-health/SKILL.md` |
| Ambiguous or conflicting signals | Low | **Suggest** options and wait for user to choose |

**High confidence = auto-activate.** Load the target skill's SKILL.md and begin executing it immediately. Do not ask for confirmation.

**Low confidence = suggest.** Present 2-3 options with brief descriptions and let the user choose. Example:

> "Based on what you've described, I can:
> 1. **Investigate alerts** — triage and fix active data issues (incident response workflow)
> 2. **Improve monitoring** — find coverage gaps and create monitors (proactive monitoring workflow)
>
> Which would be most helpful?"

### Prevent guardrail

If the user is **actively editing** a dbt model file (making code changes, not just viewing or asking about it) and the `prevent` skill's hooks are active, do NOT route to any other skill. Instead respond:

> "The prevent skill will automatically handle impact assessment for dbt model changes via its pre-edit hooks. No additional routing needed."
