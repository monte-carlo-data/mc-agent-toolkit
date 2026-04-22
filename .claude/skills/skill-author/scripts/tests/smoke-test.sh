#!/usr/bin/env bash
# Verify every path and script that skill-author's SKILL.md references still exists
# and behaves as expected. Catches drift when registration targets move or scripts
# are renamed — without this, skill-author would fail silently mid-flow.
#
# Run from repo root:  bash .claude/skills/skill-author/scripts/smoke-test.sh
# Exits 0 on pass, 1 on any failure.
set -u

SKILL_DIR=".claude/skills/skill-author"
fail=0

assert_file() {
  if [ ! -f "$1" ]; then
    echo "FAIL: missing file $1"
    fail=1
  fi
}

assert_dir() {
  if [ ! -d "$1" ]; then
    echo "FAIL: missing dir $1"
    fail=1
  fi
}

assert_script_runs() {
  local label="$1"; shift
  if ! "$@" >/dev/null 2>&1; then
    echo "FAIL: $label — '$*' exited non-zero"
    fail=1
  fi
}

# Core skill-author files
assert_file "CONTRIBUTING.md"
assert_file "$SKILL_DIR/SKILL.md"
assert_file "$SKILL_DIR/references/decision-rules.md"
assert_file "$SKILL_DIR/references/handoff-preamble.md"
assert_file "$SKILL_DIR/references/registration-checklist.md"
assert_file "$SKILL_DIR/scripts/find-peers.sh"
assert_file "$SKILL_DIR/scripts/lint-skill.py"

# Registration-checklist targets (referenced in registration-checklist.md)
assert_file "skills/context-detection/references/signal-definitions.md"
assert_file "plugins/claude-code/commands/catalog/mc.md"
assert_file "plugins/claude-code/.claude-plugin/plugin.json"
assert_file "scripts/bump-version.sh"

# Editor-plugin dirs for symlinks (registration-checklist step 4)
for editor in claude-code cursor codex opencode; do
  assert_dir "plugins/$editor/skills"
done

# Scripts run without crashing on valid input
assert_script_runs "find-peers.sh dumps skills" bash "$SKILL_DIR/scripts/find-peers.sh" skills

# Lint against a synthetic compliant skill (real skills in skills/ have legacy
# version/bucket debt that the linter correctly flags — not what this test
# measures).
FIXTURE=$(mktemp -d)
mkdir -p "$FIXTURE/smoke-fixture"
cat > "$FIXTURE/smoke-fixture/SKILL.md" <<'EOF'
---
name: monte-carlo-smoke-fixture
description: A fixture skill for smoke-testing lint-skill.py.
when_to_use: When smoke-testing.
bucket: Monitoring
---
EOF
assert_script_runs "lint-skill.py accepts a compliant skill" python3 "$SKILL_DIR/scripts/lint-skill.py" smoke-fixture "$FIXTURE"
rm -rf "$FIXTURE"

if [ "$fail" -eq 0 ]; then
  echo "skill-author smoke test: OK"
  exit 0
else
  echo "skill-author smoke test: FAILED"
  exit 1
fi
