# Extend-or-split decision rules

Source of truth: `CONTRIBUTING.md § Skill authoring standards → Extend or split?` at the repo root.
This file is a Claude-facing restatement. If it drifts from `CONTRIBUTING.md`, trust CONTRIBUTING.

**Default:** extend an existing peer skill. Split only when a rule forces it.

## The 4-step test

Apply in order. Stop at the first step that decides.

### Step 1 — Find the nearest peer

Run `find-peers.sh --bucket <B> --keywords <k1,k2,...>` against `skills/`.

For each candidate returned, ask: *can you write a realistic user prompt that should route to the new skill but could plausibly activate the candidate instead?*

- If no candidate survives this test → **there is no routing collision. Go to new-skill path. Stop.**
- If at least one survives → that is the peer. Continue to Step 2.

### Step 2 — Budget check

Open the peer's `SKILL.md`. Count the combined character length of `description` + `when_to_use`.
If adding one sentence to `description` or one bullet to `when_to_use` would push the combined length past **1,400 characters** → **split.** Stop.
(The hard ceiling is 1,536; 1,400 leaves headroom.)

### Step 3 — Surface check

Does the new behavior:
- hit a different MCP surface / data input, **or**
- produce a different output artifact, **or**
- belong to a different capability bucket

…than the peer? If yes → **split.** Stop.

### Step 4 — Otherwise, extend

Phrasing overlap, "it feels like its own thing," or wanting a cleaner file are not reasons to split. Add a bullet to the peer's `when_to_use`, add a `references/` file if the workflow needs more room.

## PR requirement

If the verdict is SPLIT, the contributor must name the peer(s) considered and cite which step forced the split. `skill-author` captures this as the override reason and surfaces it for the PR description.

## Worked example

- Survey answers: bucket = Monitoring, surface = BigQuery INFORMATION_SCHEMA, purpose = "detect stale partitions," phrasings = ["find stale partitions", "partition freshness"].
- Peer search returns: `monitoring-advisor`, `tune-monitor`.
- Step 1: `monitoring-advisor` passes the collision test (prompt "find stale partitions" could plausibly activate it). Continue.
- Step 2: `monitoring-advisor`'s combined front-matter is 920 chars. Adding a 180-char bullet = 1,100. OK, no budget pressure.
- Step 3: same bucket (Monitoring), same primary surface (BigQuery), output overlaps (monitor recommendations). No surface pressure.
- Step 4: **extend** `monitoring-advisor` with the new phrasings.
