#!/usr/bin/env bash
# Verify skill-author prerequisites. Sourced by SKILL.md pre-load.
# Env overrides (for tests): HOME, MC_TOOLKIT_ROOT
set -euo pipefail

PLUGIN_DIR="${HOME}/.claude/plugins/marketplaces/claude-plugins-official/plugins/skill-creator"
if [ ! -d "$PLUGIN_DIR" ]; then
  cat >&2 <<EOF
Anthropic's skill-creator plugin is not installed.
Install it from a terminal: /plugin install skill-creator@claude-plugins-official
Then re-run /skill-author.
EOF
  exit 1
fi

REPO_ROOT="${MC_TOOLKIT_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || true)}"
if [ -z "$REPO_ROOT" ]; then
  echo "Not inside a git repo. Run /skill-author from inside mc-agent-toolkit." >&2
  exit 2
fi

REMOTE="$(cd "$REPO_ROOT" && git remote get-url origin 2>/dev/null || true)"
if [[ "$REMOTE" != *"agent-toolkit"* ]] && [[ "$(basename "$REPO_ROOT")" != *"agent-toolkit"* ]]; then
  echo "Current repo is not mc-agent-toolkit (remote: $REMOTE). Run /skill-author from inside mc-agent-toolkit." >&2
  exit 3
fi

if [ ! -f "$REPO_ROOT/CONTRIBUTING.md" ]; then
  echo "CONTRIBUTING.md missing at repo root — can't operate without authoring rules." >&2
  exit 4
fi

echo "OK: prereqs met. REPO_ROOT=$REPO_ROOT"
