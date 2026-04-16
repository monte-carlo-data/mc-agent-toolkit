---
name: monte-carlo-incident-response
description: Orchestrate incident response — triage, root cause, remediate, prevent recurrence. USE WHEN active alerts, data broken, stale, pipeline failure, or investigate and fix a data incident.
version: 1.0.0
---

# Monte Carlo Incident Response Workflow

This workflow orchestrates the full lifecycle of a data incident by sequencing
existing Monte Carlo skills. It does not contain investigation or remediation
logic itself — each step loads the relevant skill's SKILL.md which has the
actual instructions.

## When to activate this workflow

Activate when:

- Context detection routes here (active alerts detected + incident intent)
- User invokes `/mc-incident-response`
- User asks to "respond to an incident", "handle this alert", "triage and fix"
- User describes a data quality problem: "data is broken", "table is stale", "alert firing"

## When NOT to activate this workflow

- User wants to create monitors or check coverage without an active incident — use proactive monitoring workflow
- User is editing a dbt model — defer to `prevent` skill (auto-activates via hooks)
- User wants to check table health without an incident context — use `asset-health` directly
- A skill is already active and handling the user's request

---

## Workflow Steps

```
Step 1 (conditional): Triage — when user has multiple/unknown alerts
Step 2: Root Cause Analysis — the core investigation
Step 3: Remediation — fix or escalate
Step 4 (optional): Prevent Recurrence — add monitoring
```

### Determine entry point

Before starting, determine which step to enter based on the user's context:

- **User has no specific alert** ("I have alerts firing", "what's going on?") → Start at **Step 1: Triage**
- **User has a specific alert ID or table** ("alert ABC-123", "stg_payments is stale") → Skip to **Step 2: Root Cause Analysis**
- **User knows the root cause** ("the ETL job failed, help me fix it") → Skip to **Step 3: Remediation**
- **Ambiguous** → Ask: "Do you have a specific alert or table you want to investigate, or should I check your recent alerts first?"

---

### Step 1: Triage (conditional)

**Skill:** Read and follow `../automated-triage/SKILL.md`

**Goal:** Fetch recent alerts, score them by confidence and impact, identify which ones need investigation.

**When to run:** Only when the user doesn't already have a specific alert or incident to investigate. This step helps narrow down "I have alerts" into "these specific alerts need attention."

**Transition to Step 2:** Once high-priority alert(s) are identified, tell the user:

> "I've identified [N] high-priority alerts. Let me investigate the root cause of [specific alert/table]. Moving to root cause analysis."

Then proceed to Step 2 with the identified alert context.

---

### Step 2: Root Cause Analysis

**Skill:** Read and follow `../analyze-root-cause/SKILL.md`

**Goal:** Investigate why the issue occurred — trace lineage, check ETL changes, analyze query modifications, profile data.

**This is the core step.** Most workflow entries start here.

**Transition to Step 3:** When the root cause is identified (or the investigation reaches its limit), summarize findings and tell the user:

> "Root cause identified: [summary]. Would you like me to help remediate this, or is the investigation sufficient?"

If the user wants to proceed, move to Step 3. If they say "that's enough", stop.

---

### Step 3: Remediation

**Skill:** Read and follow `../remediation/SKILL.md`

**Goal:** Fix the issue using available tools, or escalate with full context if the fix requires actions outside the agent's capability.

**Transition to Step 4:** After remediation is complete (fix applied or escalation documented), offer prevention:

> "The issue has been [fixed/escalated]. The root cause was [X]. Want me to help add a monitor to detect this type of issue earlier next time?"

If the user says yes, move to Step 4. If no, the workflow is complete.

---

### Step 4: Prevent Recurrence (optional)

**Skill:** Read and follow `../monitoring-advisor/SKILL.md`

When loading monitoring-advisor for this step, frame the request as direct monitor creation — not coverage analysis. The user already knows what they want to monitor (the thing that just broke). Example framing:

> "Based on the incident, I recommend adding a [freshness/volume/validation] monitor on [table]. Let me create the monitor configuration."

**Goal:** Add or update a monitor to catch this class of issue in the future.

**Do not force this step.** It is optional — offer it after remediation, and respect if the user declines.

---

## Orchestration Rules

- **Users can enter at any step.** The entry point section above determines where to start.
- **Each step loads the actual skill's SKILL.md** via relative path. This workflow does not replicate skill logic — it sequences it.
- **Context carries forward** through conversation naturally. Alert IDs, table names, root cause findings from earlier steps are available to later steps without explicit state passing.
- **No state tracking or hooks.** This is purely prompt-driven sequencing.
- **User can exit anytime.** If they say "that's enough" or "stop", respect it immediately.
- **Do not skip back.** The workflow moves forward. If the user wants to re-investigate after remediation, they can start a new workflow or invoke a skill directly.
