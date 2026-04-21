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

@test "ranks peers by number of distinct keyword hits" {
  TMP=$(mktemp -d)
  mkdir -p "$TMP/one-hit" "$TMP/three-hit" "$TMP/two-hit"
  cat > "$TMP/one-hit/SKILL.md" <<'EOF'
---
name: one-hit
description: Incident Response bucket. Mentions alerts only.
---
EOF
  cat > "$TMP/three-hit/SKILL.md" <<'EOF'
---
name: three-hit
description: Incident Response bucket. Mentions alerts, lineage, and freshness.
---
EOF
  cat > "$TMP/two-hit/SKILL.md" <<'EOF'
---
name: two-hit
description: Incident Response bucket. Mentions alerts and lineage.
---
EOF
  run "$SCRIPT" --skills-dir "$TMP" --bucket "Incident Response" --keywords "alerts,lineage,freshness"
  [ "$status" -eq 0 ]
  # Expect descending-hits order: three-hit (3), two-hit (2), one-hit (1)
  expected=$'three-hit\ntwo-hit\none-hit'
  [ "$output" = "$expected" ]
}

@test "breaks ties alphabetically" {
  TMP=$(mktemp -d)
  mkdir -p "$TMP/zebra" "$TMP/apple" "$TMP/mango"
  for name in zebra apple mango; do
    cat > "$TMP/$name/SKILL.md" <<EOF
---
name: $name
description: Monitoring bucket. Mentions monitor.
---
EOF
  done
  run "$SCRIPT" --skills-dir "$TMP" --bucket "Monitoring" --keywords "monitor"
  [ "$status" -eq 0 ]
  expected=$'apple\nmango\nzebra'
  [ "$output" = "$expected" ]
}

@test "exits 2 on missing arguments" {
  run "$SCRIPT"
  [ "$status" -eq 2 ]
}
