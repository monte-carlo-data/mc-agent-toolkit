#!/usr/bin/env bats

setup() {
  SCRIPT="$BATS_TEST_DIRNAME/../lint-skill.py"
  TMP=$(mktemp -d)
}

teardown() {
  rm -rf "$TMP"
}

# Write a SKILL.md with given frontmatter under $TMP/<name>/SKILL.md
make_skill() {
  local name="$1"
  local frontmatter="$2"
  mkdir -p "$TMP/$name"
  cat > "$TMP/$name/SKILL.md" <<EOF
---
$frontmatter
---

Body content.
EOF
}

@test "passes for a valid single-line scalar description" {
  make_skill good-skill "name: good-skill
description: Does a thing for users when they ask about doing that thing.
when_to_use: |
  When the user mentions doing that thing."
  run python3 "$SCRIPT" good-skill "$TMP"
  [ "$status" -eq 0 ]
  [[ "$output" == *"good-skill"* ]]
  [[ "$output" != *"ERROR"* ]]
}

@test "passes for a block-scalar description" {
  make_skill block-skill 'name: block-skill
description: |
  This is a multi-line description that spans
  several lines for readability.
when_to_use: |
  When the user needs this.'
  run python3 "$SCRIPT" block-skill "$TMP"
  [ "$status" -eq 0 ]
  [[ "$output" != *"ERROR"* ]]
}

@test "errors when description is missing" {
  make_skill nodesc "name: nodesc
when_to_use: Something."
  run python3 "$SCRIPT" nodesc "$TMP"
  [ "$status" -eq 1 ]
  [[ "$output" == *"ERROR: description is missing"* ]]
}

@test "errors when description exceeds 1024 chars" {
  # Build a >1024-char description
  long=$(python3 -c 'print("x" * 1100)')
  make_skill toolong "name: toolong
description: $long"
  run python3 "$SCRIPT" toolong "$TMP"
  [ "$status" -eq 1 ]
  [[ "$output" == *"description is 1100 chars"* ]]
}

@test "errors on first-person opener 'This skill'" {
  make_skill firstperson "name: firstperson
description: This skill does a thing when asked."
  run python3 "$SCRIPT" firstperson "$TMP"
  [ "$status" -eq 1 ]
  [[ "$output" == *"first-person"* ]]
}

@test "errors on first-person opener 'Use this skill'" {
  make_skill useskill "name: useskill
description: Use this skill when the user wants X."
  run python3 "$SCRIPT" useskill "$TMP"
  [ "$status" -eq 1 ]
  [[ "$output" == *"first-person"* ]]
}

@test "warns when when_to_use is missing, still exits 0" {
  make_skill nowtu "name: nowtu
description: A valid description."
  run python3 "$SCRIPT" nowtu "$TMP"
  [ "$status" -eq 0 ]
  [[ "$output" == *"WARN:  when_to_use is missing"* ]]
}

@test "errors when combined description + when_to_use exceeds 1400 chars" {
  desc=$(python3 -c 'print("a" * 900)')
  wtu=$(python3 -c 'print("b" * 600)')
  make_skill combined "name: combined
description: $desc
when_to_use: $wtu"
  run python3 "$SCRIPT" combined "$TMP"
  [ "$status" -eq 1 ]
  [[ "$output" == *"1500 chars"* ]]
  [[ "$output" == *"max 1400"* ]]
}

@test "errors when name field does not match directory" {
  make_skill my-dir "name: other-name
description: Does a thing."
  run python3 "$SCRIPT" my-dir "$TMP"
  [ "$status" -eq 1 ]
  [[ "$output" == *"does not match directory"* ]]
}

@test "errors when name is not kebab-case" {
  make_skill BadName "name: BadName
description: Does a thing."
  run python3 "$SCRIPT" BadName "$TMP"
  [ "$status" -eq 1 ]
  [[ "$output" == *"not kebab-case"* ]]
}

@test "errors when name contains underscores" {
  make_skill bad_name "name: bad_name
description: Does a thing."
  run python3 "$SCRIPT" bad_name "$TMP"
  [ "$status" -eq 1 ]
  [[ "$output" == *"not kebab-case"* ]]
}

@test "exits 2 when SKILL.md does not exist" {
  run python3 "$SCRIPT" nonexistent "$TMP"
  [ "$status" -eq 2 ]
  [[ "$output" == *"not found"* ]]
}

@test "exits 2 with usage message when no args given" {
  run python3 "$SCRIPT"
  [ "$status" -eq 2 ]
  [[ "$output" == *"Usage"* ]]
}

@test "handles quoted scalar descriptions" {
  make_skill quoted 'name: quoted
description: "A quoted description with colons: and commas."'
  run python3 "$SCRIPT" quoted "$TMP"
  [ "$status" -eq 0 ]
  [[ "$output" == *"quoted"* ]]
  [[ "$output" != *"ERROR"* ]]
}

@test "defaults skills_root to ./skills when omitted" {
  mkdir -p "$TMP/skills/defroot"
  cat > "$TMP/skills/defroot/SKILL.md" <<'EOF'
---
name: defroot
description: A default-root test skill.
---
EOF
  cd "$TMP"
  run python3 "$SCRIPT" defroot
  [ "$status" -eq 0 ]
  [[ "$output" == *"defroot"* ]]
}
