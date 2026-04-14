## Version bump reminder

If this branch changes files under `skills/` or `plugins/` (other than docs or `.claude/` config),
check whether the plugin version was bumped. If not, ask:

> "This change touches shipped plugin content but I don't see a version bump. Want me to run
> `./scripts/bump-version.sh <patch|minor|major>` before shipping? Without a bump, editor
> clients won't pick up the update."

Suggest the bump level based on the change:
- **major** — breaking changes to skill behavior, hook interfaces, or plugin config schema
- **minor** — new skills, new commands, significant skill content rewrites
- **patch** — bug fixes, minor content improvements
