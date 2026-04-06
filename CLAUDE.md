# CLAUDE.md

## Repo Overview

Monte Carlo's official toolkit for AI coding agents. Contains **skills** (agent instructions) and **plugins** (editor-specific wrappers) that integrate Monte Carlo's data observability platform into development workflows.

## Architecture

```
skills/<name>/              ← Source of truth for skill content
  SKILL.md                  ← Required: YAML frontmatter + instructions
  README.md                 ← User-facing docs
  references/               ← Optional: detailed sub-docs loaded via Read tool

plugins/<editor>/<dir>/     ← Editor-specific wrappers (symlink to skills/)
  Claude Code: .claude-plugin/plugin.json, .mcp.json, skills/<name> → symlink
  Cursor:      .cursor-plugin/plugin.json, mcp.json, skills/<name> → symlink
  OpenCode:    opencode.json, skills/<name> → symlink

.claude-plugin/marketplace.json  ← Claude Code marketplace registry
```

**Key principle:** Skills are authored once in `skills/`. Plugins reference them via relative symlinks (`../../../../skills/<name>`). When an editor installs a plugin, it resolves symlinks and copies the real files.

## Adding a New Skill

### 1. Create the skill

```
skills/<name>/
  SKILL.md          ← YAML frontmatter: name, description, version (required)
  README.md         ← Setup, usage, prerequisites
  references/       ← Per-topic detail docs (loaded via Read tool from SKILL.md)
```

Follow `skills/monitor-creation/` or `skills/prevent/` as templates. SKILL.md must include:
- YAML frontmatter (`name`, `description`, `version`)
- "When to activate" / "When NOT to activate" sections
- Available MCP tools table
- Core procedure or workflows

Reference docs go in `references/` and are loaded via Read tool references in SKILL.md — not inlined.

### 2. Create plugin wrappers for all three editors

**Claude Code** (`plugins/claude-code/<dir>/`):
- `.claude-plugin/plugin.json` — name: `mc-<name>`, version, description, author, repo, license, keywords
- `.mcp.json` — `{"mcpServers": {"monte-carlo": {"type": "http", "url": "https://integrations.getmontecarlo.com/mcp"}}}`
- `skills/<name>` — symlink: `ln -s ../../../../skills/<name> skills/<name>`

**Cursor** (`plugins/cursor/<dir>/`):
- `.cursor-plugin/plugin.json` — same fields as Claude Code
- `mcp.json` — `{"mcpServers": {"monte-carlo": {"url": "https://integrations.getmontecarlo.com/mcp"}}}`
- `skills/<name>` — symlink: same relative path

**OpenCode** (`plugins/opencode/<dir>/`):
- `opencode.json` — MCP config + tool permissions. Only add `package.json`/`src/` if hooks are needed.
- `skills/<name>` — symlink: same relative path

### 3. Register and document

- Add the Claude Code plugin to `.claude-plugin/marketplace.json`
- Add the plugin to the `Available plugins` table in `README.md`
- Add the skill to the `Available skills` table in `README.md`

### 4. Test locally

```bash
claude --plugin-dir ./plugins/claude-code/<dir>
```

Verify: symlinks resolve (`ls -la plugins/<editor>/<dir>/skills/<name>`), JSON is valid (`python3 -m json.tool <file>`).

## Conventions

- **Skill naming:** kebab-case directories (`monitor-creation`, `push-ingestion`)
- **Plugin naming:** `mc-<name>` prefix (`mc-core`, `mc-prevent`)
- **Symlinks:** always relative (`../../../../skills/<name>`), never absolute
- **MCP tools:** all tools come from the `monte-carlo` MCP server — same HTTP endpoint across all plugins
- **No hooks unless needed:** only add hooks if the skill requires gating behavior (e.g., prevent's pre-edit gate). Skill content alone is usually sufficient.
- **Version bumping:** patch for fixes, minor for new features/content, major for breaking changes. Bump in `plugin.json`.

## Verification

```bash
# Validate JSON files
python3 -m json.tool plugins/claude-code/<dir>/.claude-plugin/plugin.json
python3 -m json.tool .claude-plugin/marketplace.json

# Verify symlinks resolve
ls -la plugins/claude-code/<dir>/skills/<name>
ls -la plugins/cursor/<dir>/skills/<name>
ls -la plugins/opencode/<dir>/skills/<name>
```

## Files to Ignore

- `.work/` — local work tracking (gitignored)
- `.mcp.json` at repo root — local MCP config (gitignored, but `plugins/**/.mcp.json` is tracked)
