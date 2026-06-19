#!/usr/bin/env bash
# Test shim: replaces real curl on PATH. Logs argv + stdin to $MOCK_CURL_LOG
# (one JSON line per invocation) and exits 0. Used by install-beacon and skill-beacon tests to
# verify what would have been sent without making network calls.
set -uo pipefail

LOG="${MOCK_CURL_LOG:-/dev/null}"
STDIN_PAYLOAD="$(cat || true)"

# Pull the body from -d/--data when present; otherwise fall back to stdin.
data=""
prev=""
for arg in "$@"; do
  case "$prev" in
    -d|--data|--data-raw|--data-binary) data="$arg" ;;
  esac
  prev="$arg"
done
[[ -z "$data" ]] && data="$STDIN_PAYLOAD"

# argv as a JSON array; data as a string. jq handles all escaping.
jq -nc \
  --argjson argv "$(printf '%s\n' "$@" | jq -R . | jq -sc .)" \
  --arg data "$data" \
  '{argv: $argv, data: $data}' >> "$LOG"

exit 0
