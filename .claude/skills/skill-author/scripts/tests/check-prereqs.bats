#!/usr/bin/env bats

setup() {
  SCRIPT="$BATS_TEST_DIRNAME/../check-prereqs.sh"
}

@test "fails when skill-creator plugin directory is missing" {
  FAKE_HOME=$(mktemp -d)
  run env HOME="$FAKE_HOME" MC_TOOLKIT_ROOT="$BATS_TEST_DIRNAME/../../../../.." "$SCRIPT"
  [ "$status" -ne 0 ]
  [[ "$output" == *"skill-creator"*"not installed"* ]]
}

@test "fails when not in mc-agent-toolkit repo" {
  FAKE_REPO=$(mktemp -d)
  (cd "$FAKE_REPO" && git init -q)
  run env MC_TOOLKIT_ROOT="$FAKE_REPO" "$SCRIPT"
  [ "$status" -ne 0 ]
  [[ "$output" == *"agent-toolkit"* ]]
}

@test "fails when CONTRIBUTING.md is missing" {
  FAKE_REPO=$(mktemp -d)
  (cd "$FAKE_REPO" && git init -q && git remote add origin git@github.com:monte-carlo-data/mc-agent-toolkit.git)
  run env MC_TOOLKIT_ROOT="$FAKE_REPO" "$SCRIPT"
  [ "$status" -ne 0 ]
  [[ "$output" == *"CONTRIBUTING.md"* ]]
}

@test "succeeds when all prereqs are met" {
  FAKE_HOME=$(mktemp -d)
  mkdir -p "$FAKE_HOME/.claude/plugins/marketplaces/claude-plugins-official/plugins/skill-creator"
  run env HOME="$FAKE_HOME" MC_TOOLKIT_ROOT="$BATS_TEST_DIRNAME/../../../../.." "$SCRIPT"
  [ "$status" -eq 0 ]
}
