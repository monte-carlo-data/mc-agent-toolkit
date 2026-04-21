# Registration checklist

After Phase 2a (extend) or Phase 2b (new skill), walk the relevant subset of these steps. `skill-author` tracks each as a TodoWrite item and confirms before writing any file.

## Full checklist (new skill)

Use when Phase 2b concludes with a scaffolded `skills/<name>/SKILL.md`.

1. **Signal definition.** Append a row to `skills/context-detection/references/signal-definitions.md` under *Conversation Signals* and/or *Workspace Signals*. Describe the keywords, artifacts, and user phrasings that should route to the new skill.
   *Skipped if bucket = Setup (after user confirmation).*
2. **`/mc` catalog entry.** Append a row to `plugins/claude-code/commands/catalog/mc.md`.
   *Skipped if bucket = Setup (after user confirmation).*
3. **Eval scaffold.** Create `plugins/claude-code/evals/<name>/` following the existing framework (see `plugins/claude-code/evals/<any-existing-skill>/` for structure). At minimum: a trigger-eval file with representative prompts collected in Phase 2b Q4.
4. **Editor plugin symlinks.** For each editor in `plugins/` (claude-code, cursor, opencode, codex), add a relative symlink:
   ```
   plugins/<editor>/skills/<name> -> ../../../skills/<name>
   ```
5. **Claude Code commands entry.** Create `plugins/claude-code/commands/<name>/` with at least one `.md` command file. Add the directory name to the `commands` array in `plugins/claude-code/.claude-plugin/plugin.json`.

## Partial checklist (extend)

Use when Phase 2a edits an existing peer.

1. **Signal definition.** Update only if phrasings shifted (new user-facing routing language).
2. **`/mc` catalog.** Update only if the user-facing surface changed (new capability described in the catalog row).
3. **Eval entry.** Update the peer's existing `plugins/claude-code/evals/<peer>/` entry only if the activation surface expanded.

No symlink or commands changes for extend (they already exist for the peer).

## Setup-bucket confirmation prompt

When Q1 = Setup, `skill-author` prompts:

> Setup skills are exempt from signal-definitions and `/mc` catalog registration per `CONTRIBUTING § Capability buckets`. Skip these steps? [Y/n]

Default Y. On N, proceed with steps 1 and 2 as normal (user opted back in).

## Version bump (always)

After the relevant registration subset, run:

```
./scripts/bump-version.sh <patch|minor>
```

See `CONTRIBUTING.md § Version bumping` for semver rules. `skill-author` proposes the level; user can override.
