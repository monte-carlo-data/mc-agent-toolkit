# Extend-or-split decision rules

**Canonical source.** `CONTRIBUTING.md § Skill authoring standards → Extend or split?` summarizes and links here; if the two disagree, this file wins.

**Default:** extend an existing peer skill. Split only when a rule forces it.

**Forbidden buckets.** Agent-routing skills are owned by the toolkit core team per `CONTRIBUTING § Capability buckets` — do not author them via `/toolkit-skill-author`. If the contributor's Q1 answer is `Agent-routing`, halt and refuse before peer search. Do not proceed.

## The 4-step test

Apply in order. Stop at the first step that decides.

### Step 1 — Find the nearest peer

`find-peers.sh` (run in Pre-load) dumps every skill's `name + description + when_to_use`. Read the dump and reason about which skills could plausibly activate on the new skill's Q4 prompts.

For each plausible candidate, ask: *can you write a realistic user prompt that should route to the new skill but could plausibly activate the candidate instead?*

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

If the verdict is SPLIT, the contributor must name the peer(s) considered and cite which step forced the split. `toolkit-skill-author` captures this as the override reason and surfaces it for the PR description.

## Worked example

This example walks the tree for an **ambiguous new-skill** request — the case where Phase 0's Gate C doesn't fast-path, so the full decision applies. (Clear-extend requests skip the tree via Gate C; clear name collisions halt at Gate B.)

- Survey answers: bucket = Monitoring, surface = BigQuery INFORMATION_SCHEMA, purpose = "detect stale partitions," phrasings = ["find stale partitions", "partition freshness"].
- Peer dump shows: `monitoring-advisor`, `tune-monitor`, and others.
- Step 1: `monitoring-advisor`'s current scope ("create monitors for warehouse tables") plausibly activates on "find stale partitions." Peer survives. Continue.
- Step 2: measure `monitoring-advisor`'s actual combined `description + when_to_use` length and add the proposed bullet. If the sum stays under 1,400, no budget pressure. Continue.
- Step 3: same bucket (Monitoring), same primary surface (warehouse table reads, BigQuery is a subset), output overlaps (monitor recommendations). No surface pressure.
- Step 4: **extend** `monitoring-advisor` with the new phrasings.
