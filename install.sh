#!/usr/bin/env bash
# install.sh - Monte Carlo Claude plugin installer
#
# TODO: Implement the following steps:
#   1. Initialize the mcd-skills git submodule
#      git submodule update --init --recursive
#
#   2. Copy SKILL.md files to the editor's skills directory
#      mkdir -p ~/.claude/skills/monte-carlo
#      cp skills/monte-carlo/safe-change/SKILL.md ~/.claude/skills/monte-carlo/safe-change.md
#      cp skills/monte-carlo/generate-validation-notebook/SKILL.md ~/.claude/skills/monte-carlo/generate-validation-notebook.md
#
#   3. Set up MCP config
#      cp .mcp.json.example <project-dir>/.mcp.json
#      (prompt user for KEY_ID and KEY_SECRET to substitute)
#
#   4. Install Python dependencies
#      pip install pyyaml
#
set -euo pipefail

echo "Monte Carlo Claude plugin installer — not yet implemented"
echo "See README.md for manual setup instructions."
