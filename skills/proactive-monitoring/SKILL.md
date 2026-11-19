---
name: monte-carlo-proactive-monitoring
description: Guide users from coverage analysis to monitor creation. USE WHEN user asks what should I monitor, where are my gaps, improve coverage, or wants a systematic approach to monitoring across their data estate.
when_to_use: |
  Invoke when the user wants to IMPROVE monitoring coverage across their data estate — identify gaps, prioritize what to monitor, or take a systematic approach to observability.
  Example triggers: "what should I monitor?", "where are my coverage gaps?", "improve monitoring across my warehouse", "help me prioritize which tables to monitor", "audit my coverage".

  Covers: warehouse/use-case discovery → gap analysis → monitor prioritization → handoff to monitoring-advisor for actual monitor creation.

  Do NOT invoke when the user has a specific incident to investigate (use incident-response) or wants to create a single known monitor on a known table (use monitoring-advisor directly).
bucket: Agent-routing
version: 1.0.0
---

# Monte Carlo Proactive Monitoring Workflow

This workflow guides users through improving their monitoring coverage by
sequencing existing Monte Carlo skills. It does not contain coverage analysis
or monitor creation logic itself — each step loads the relevant skill's
SKILL.md which has the actual instructions.

## When to activate this workflow

Activate when:

- Context detection routes here (coverage intent + data project detected)
- User invokes `/mc-proactive-monitoring`
- User asks "what should I monitor?", "where are my gaps?", "improve coverage"
- User wants a systematic approach to monitoring — not just creating one specific monitor

## When NOT to activate this workflow

- User already knows exactly what monitor to create (e.g., "create a freshness monitor on X") — route to `monitoring-advisor` directly
- User is responding to an active incident — use incident response workflow
- User is editing a dbt model — defer to `prevent` skill (auto-activates via hooks)
- A skill is already active and handling the user's request

---

## Workflow Steps

```
Step 1 (conditional): Assess current state — when user has specific tables in mind
Step 2: Identify gaps — the core of this workflow
Step 3: Create monitors — act on identified gaps
```

### Determine entry point

Before starting, determine which step to enter based on the user's context:

- **User mentions specific tables** ("what monitoring do I have on stg_payments?", "check my orders tables") → Start at **Step 1: Assess Current State**
- **User has a model file open** with a specific table → Start at **Step 1: Assess Current State**
- **User wants estate-wide coverage** ("where are my gaps?", "what should I monitor?") → Skip to **Step 2: Identify Gaps**
- **Ambiguous** → Ask: "Would you like to check specific tables first, or look at coverage across your estate?"

---

### Step 1: Assess Current State (conditional)

**Skill:** Read and follow `../asset-health/SKILL.md`

**Goal:** Check health of the specific tables the user cares about — freshness, alerts, existing monitoring coverage, importance score, upstream dependencies.

**When to run:** Only when the user has specific tables in mind or a model file open. Provides table-level context before the broader coverage analysis.

**Transition to Step 2:** After the health report, offer the broader view:

> "[Table] has [summary of health and existing monitors]. Want me to analyze monitoring coverage more broadly — across your warehouse or use cases — to find where the gaps are?"

If the user says yes, proceed to Step 2. If they're satisfied with the table-level view, stop.

---

### Step 2: Identify Gaps

**Skill:** Read and follow `../monitoring-advisor/SKILL.md`

When loading monitoring-advisor for this step, frame the request as **coverage analysis** — not direct monitor creation. The monitoring-advisor skill has two flows; this step uses the coverage analysis flow:
- Warehouse discovery → use-case exploration → coverage analysis → gap identification

**Goal:** Analyze coverage across warehouses and use cases, identify unmonitored tables, prioritize by importance and anomaly activity.

**This is the core step.** Most workflow entries start here.

**Transition to Step 3:** When gaps are identified and the user wants to act:

> "I've identified [N] monitoring gaps, prioritized by importance. Ready to create monitors for the top priorities?"

If yes, proceed to Step 3 (which stays within monitoring-advisor). If no, stop.

---

### Step 3: Create Monitors

**Skill:** Continues within `../monitoring-advisor/SKILL.md` — transitions from coverage analysis flow to direct monitor creation flow.

This step does NOT load a separate skill. The monitoring-advisor skill handles both gap identification (Step 2) and monitor creation (Step 3). The workflow just signals the transition from "analysis" to "creation."

**Goal:** Create monitors-as-code YAML for the identified gaps. For each gap:
1. Determine the appropriate monitor type (freshness, volume, validation, custom SQL, comparison)
2. Generate the monitor configuration
3. Output as monitors-as-code YAML

**The user can create monitors for all identified gaps or select specific ones.**

---

## Orchestration Rules

- **Users can enter at any step.** The entry point section above determines where to start.
- **Each step loads the actual skill's SKILL.md** via relative path. This workflow does not replicate skill logic — it sequences it.
- **Context carries forward** through conversation naturally.
- **No state tracking or hooks.** This is purely prompt-driven sequencing.
- **User can exit anytime.**
- **If the user already knows what monitor to create** (skipping Steps 1 and 2), they should not be in this workflow — context detection routes them to monitoring-advisor directly.
