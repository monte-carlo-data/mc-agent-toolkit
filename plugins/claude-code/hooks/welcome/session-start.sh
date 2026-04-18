#!/usr/bin/env bash
# SessionStart hook: inject a brief welcome only when a dbt/Monte Carlo
# workspace is detected. Non-MC sessions get zero additional context.

set -euo pipefail

if find . -maxdepth 4 \( -name "dbt_project.yml" -o -name "montecarlo.yml" \) -print -quit 2>/dev/null | grep -q .; then
  cat <<'EOF'
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "This workspace contains a dbt project with Monte Carlo. On your FIRST response of the session only, append one brief paragraph: \"I see this is a dbt project with Monte Carlo. If you run into data issues, I can help triage alerts, investigate root causes, and set up monitoring. Type /mc to see what's available.\" Do not repeat on subsequent turns."
  }
}
EOF
else
  echo '{}'
fi
