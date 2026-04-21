#!/usr/bin/env bash
# Find peer skills by bucket + keyword overlap.
# Ranks by number of distinct keywords matched (descending); ties broken alphabetically.
# Outputs one peer-name per line (possibly empty).
set -euo pipefail

SKILLS_DIR=""
BUCKET=""
KEYWORDS=""

while [ $# -gt 0 ]; do
  case "$1" in
    --skills-dir) SKILLS_DIR="$2"; shift 2 ;;
    --bucket) BUCKET="$2"; shift 2 ;;
    --keywords) KEYWORDS="$2"; shift 2 ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done

if [ -z "$SKILLS_DIR" ] || [ -z "$BUCKET" ] || [ -z "$KEYWORDS" ]; then
  echo "Usage: find-peers.sh --skills-dir DIR --bucket NAME --keywords csv" >&2
  exit 2
fi

bucket_lc="$(echo "$BUCKET" | tr '[:upper:]' '[:lower:]')"
IFS=',' read -ra kw_arr <<< "$KEYWORDS"

ranked=""
for skill_dir in "$SKILLS_DIR"/*/; do
  [ -d "$skill_dir" ] || continue
  sm="$skill_dir/SKILL.md"
  [ -f "$sm" ] || continue

  content_lc="$(tr '[:upper:]' '[:lower:]' < "$sm")"

  if ! echo "$content_lc" | grep -qF "$bucket_lc"; then
    continue
  fi

  hits=0
  for kw in "${kw_arr[@]}"; do
    kw_lc="$(echo "$kw" | tr '[:upper:]' '[:lower:]' | xargs)"
    [ -z "$kw_lc" ] && continue
    if echo "$content_lc" | grep -qF "$kw_lc"; then
      hits=$((hits + 1))
    fi
  done
  [ "$hits" -gt 0 ] || continue

  name="$(basename "$skill_dir")"
  ranked+="$(printf '%d\t%s' "$hits" "$name")"$'\n'
done

[ -z "$ranked" ] && exit 0

# Sort by hits desc, then name asc. Emit names only.
printf '%s' "$ranked" | sort -t$'\t' -k1,1nr -k2,2 | awk -F'\t' '{print $2}'
