# Registration checklist

After Phase 2a (extend) or Phase 2b (new skill), walk the relevant subset of these steps. `toolkit-skill-author` tracks each as a TodoWrite item and confirms before writing any file.

## Full checklist (new skill)

Use when Phase 2b concludes with a scaffolded `skills/<name>/SKILL.md`.

1. **Signal definition.** Append a row to `skills/context-detection/references/signal-definitions.md` under *Conversation Signals* and/or *Workspace Signals*. Describe the keywords, artifacts, and user phrasings that should route to the new skill.
   *Skipped if bucket = Setup (after user confirmation).*
2. **`/mc` catalog entry.** Append a row to `plugins/claude-code/commands/catalog/mc.md`.
   *Skipped if bucket = Setup (after user confirmation).*
3. **Eval scaffold.** Create both eval artifacts under `plugins/claude-code/evals/<name>/`:

   **(a) `plugins/claude-code/evals/<name>/trigger-evals.json`** — trigger accuracy. Read `plugins/claude-code/evals/onboarding/trigger-evals.json` as a template. Schema:

   ```json
   {
     "skill": "monte-carlo-<name>",
     "description": "<one-line description of the trigger eval suite>",
     "cases": [
       {"id": "should-01", "prompt": "<realistic user prompt>", "expected": "trigger", "rationale": "<why it should trigger>"},
       {"id": "should-not-01", "prompt": "<near-miss prompt>", "expected": "no-trigger", "rationale": "<why it should not>"}
     ]
   }
   ```

   Seed with the Q4 phrasings plus 2–3 should-not-trigger near-misses. Run with `make trigger-evals SKILL=<name>`; validate cheaply with `make dry-run SKILL=<name>`, which needs no API key.

   **(b) `plugins/claude-code/evals/<name>/live-evals-dev.yaml`** — flow evals. Use the YAML schema the repo already ships for every other skill. Read `plugins/claude-code/evals/monitoring-advisor/live-evals-dev.yaml` or `plugins/claude-code/evals/context-detection/live-evals-dev.yaml` as templates before writing. Schema:

   ```yaml
   cases:
     - id: <slug-id>
       turns:
         - prompt: "<realistic user prompt>"
           criteria:
             must_call: [mcp_tool_1, mcp_tool_2]      # optional
             must_not_call: [forbidden_tool]           # optional
       criteria:
         judge_rubric: |
           <free-form description of desired behavior>
   ```

   Seed with the Q4 phrasings plus 2–3 should-not-trigger near-misses. The `live-evals-dev.yaml` may be deferred when the flow needs credentials or tools not yet available, but only with a ticket that exists first: create the follow-up ticket, name it in the PR, and land the evals there. Never leave text in the repo saying something "needs a ticket".
4. **Editor plugin symlinks.** For each editor in `plugins/` (claude-code, cursor, opencode, codex), add a relative symlink:
   ```
   plugins/<editor>/skills/<name> -> ../../../skills/<name>
   ```
5. **Portability markers.** Confirm every plugin-only passage in the new `SKILL.md` (slash commands, hooks, `Read` instructions) sits inside `<!-- plugin-only:start -->` / `<!-- plugin-only:end -->` per `CONTRIBUTING.md § Portability markers for plugin-only sections`.
6. **Claude Code commands entry.** Create `plugins/claude-code/commands/<name>/` with at least one `.md` command file. Add the directory name to the `commands` array in `plugins/claude-code/.claude-plugin/plugin.json`.

## Partial checklist (extend)

Use when Phase 2a edits an existing peer.

1. **Signal definition.** Update only if phrasings shifted (new user-facing routing language).
2. **`/mc` catalog.** Update only if the user-facing surface changed (new capability described in the catalog row).
3. **Eval entry.** Update the peer's existing `plugins/claude-code/evals/<peer>/` entry only if the activation surface expanded.

No symlink or commands changes for extend (they already exist for the peer).

## Setup-bucket confirmation prompt

When Q1 = Setup, `toolkit-skill-author` prompts:

> Setup skills are exempt from signal-definitions and `/mc` catalog registration per `CONTRIBUTING § Capability buckets`. Skip these steps? [Y/n]

Default Y. On N, proceed with steps 1 and 2 as normal (user opted back in).

## Version bump (always)

After the relevant registration subset, run:

```
./scripts/bump-version.sh <patch|minor>
```

See `CONTRIBUTING.md § Version bumping` for semver rules. `toolkit-skill-author` proposes the level; user can override.
