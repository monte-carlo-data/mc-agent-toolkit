#!/usr/bin/env bats

setup() {
  SCRIPT="$BATS_TEST_DIRNAME/../find-peers.sh"
  CATALOG_A="$BATS_TEST_DIRNAME/fixtures/skills-catalog-a"
}

@test "returns matching peer when bucket and keyword match" {
  run "$SCRIPT" --skills-dir "$CATALOG_A" --bucket "Incident Response" --keywords "alerts,lineage"
  [ "$status" -eq 0 ]
  [[ "$output" == *"alpha"* ]]
  [[ "$output" != *"beta"* ]]
  [[ "$output" != *"gamma"* ]]
}

@test "returns multiple peers when multiple match the bucket" {
  TMP=$(mktemp -d)
  cp -r "$CATALOG_A"/* "$TMP/"
  mkdir -p "$TMP/delta"
  cat > "$TMP/delta/SKILL.md" <<'EOF'
---
name: delta
description: Proactive monitor coverage review. Activates on "coverage", "monitor gaps".
when_to_use: |
  Monitoring bucket.
---
EOF
  run "$SCRIPT" --skills-dir "$TMP" --bucket "Monitoring" --keywords "monitor"
  [ "$status" -eq 0 ]
  [[ "$output" == *"beta"* ]]
  [[ "$output" == *"delta"* ]]
}

@test "returns empty when no peers match" {
  run "$SCRIPT" --skills-dir "$CATALOG_A" --bucket "Trust" --keywords "asset,health"
  [ "$status" -eq 0 ]
  [ -z "$output" ]
}

@test "exits 2 on missing arguments" {
  run "$SCRIPT"
  [ "$status" -eq 2 ]
}
