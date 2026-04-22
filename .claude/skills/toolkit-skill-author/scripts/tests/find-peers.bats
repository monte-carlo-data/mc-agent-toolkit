#!/usr/bin/env bats

setup() {
  SCRIPT="$BATS_TEST_DIRNAME/../find-peers.sh"
}

@test "dumps frontmatter for every skill under the dir" {
  TMP=$(mktemp -d)
  mkdir -p "$TMP/alpha" "$TMP/beta"
  cat > "$TMP/alpha/SKILL.md" <<'EOF'
---
name: alpha
description: Alpha does X.
when_to_use: |
  When the user asks about X.
---

Body content here.
EOF
  cat > "$TMP/beta/SKILL.md" <<'EOF'
---
name: beta
description: Beta does Y.
---
EOF
  run "$SCRIPT" "$TMP"
  [ "$status" -eq 0 ]
  [[ "$output" == *"=== alpha ==="* ]]
  [[ "$output" == *"=== beta ==="* ]]
  [[ "$output" == *"description: Alpha does X."* ]]
  [[ "$output" == *"description: Beta does Y."* ]]
  [[ "$output" == *"When the user asks about X."* ]]
  [[ "$output" != *"Body content here."* ]]
}

@test "exits 2 when skills dir is missing" {
  run "$SCRIPT" /nonexistent-path-$$
  [ "$status" -eq 2 ]
}

@test "exits 2 when skills dir has no SKILL.md files" {
  TMP=$(mktemp -d)
  run "$SCRIPT" "$TMP"
  [ "$status" -eq 2 ]
}

@test "defaults to ./skills when no arg given" {
  TMP=$(mktemp -d)
  mkdir -p "$TMP/skills/gamma"
  cat > "$TMP/skills/gamma/SKILL.md" <<'EOF'
---
name: gamma
description: Gamma.
---
EOF
  cd "$TMP"
  run "$SCRIPT"
  [ "$status" -eq 0 ]
  [[ "$output" == *"=== gamma ==="* ]]
}
