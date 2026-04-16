#!/bin/bash
# Injects Monte Carlo routing instructions into the session context.
# This runs on SessionStart and outputs additionalContext that the LLM receives.

cat << 'ROUTING_EOF'
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "## Monte Carlo Agent Toolkit — Routing Instructions\n\nThis session has Monte Carlo data observability skills available.\n\n### Session Start\nOn your first response (when conversation history is empty), check if dbt_project.yml or montecarlo.yml exists in the workspace. If found, briefly mention: \"I see this is a dbt project with Monte Carlo. If you run into data issues, I can help triage alerts, investigate root causes, and set up monitoring. I'll also flag impact when you edit models. Ask me anything or type /mc to see what's available.\"\n\n### Routing Table\nWhen a user sends a data-related message and NO skill is currently active, route based on intent:\n- Actively editing a dbt model → prevent skill auto-activates via hooks, no routing needed\n- Create a specific monitor → use monitoring-advisor skill\n- Check health of a specific table → use asset-health skill\n- Mentions alerts, incidents, data broken/stale, or data issues → use context-detection skill\n- Mentions coverage gaps, what to monitor → use context-detection skill\n- Storage costs, unused tables → use storage-cost-analysis skill\n- Slow pipelines, expensive queries → use performance-diagnosis skill\n- Ambiguous or multi-step data request → use context-detection skill\n\nIMPORTANT: For ambiguous data-related messages, ALWAYS use the context-detection skill first. Do not skip it and go directly to individual skills like analyze-root-cause or asset-health unless the user's intent clearly matches a single skill."
  }
}
ROUTING_EOF
