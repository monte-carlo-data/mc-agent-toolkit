#!/usr/bin/env bash
# Dump every skill's frontmatter (name + description + when_to_use) so Claude can
# reason about which skills are peers to the new/extended one. Replaces the old
# bucket+keyword filtering, which was too brittle to be useful — baseline evals
# showed false positives from substring bucket matches and false negatives from
# stopword-dominated keyword ranking.
#
# Output is the raw frontmatter block for each skill, separated by `=== <name> ===`
# headers. Claude reads it and applies the 4-step decision-rules test itself.
set -euo pipefail

SKILLS_DIR="${1:-skills}"

if [ ! -d "$SKILLS_DIR" ]; then
  echo "find-peers.sh: skills dir '$SKILLS_DIR' not found" >&2
  exit 2
fi

found=0
for sm in "$SKILLS_DIR"/*/SKILL.md; do
  [ -f "$sm" ] || continue
  found=1
  name="$(basename "$(dirname "$sm")")"
  echo "=== $name ==="
  awk '/^---[[:space:]]*$/{c++; if(c==2)exit; next} c==1' "$sm"
  echo
done

[ "$found" -eq 1 ] || { echo "find-peers.sh: no SKILL.md files in '$SKILLS_DIR'" >&2; exit 2; }
