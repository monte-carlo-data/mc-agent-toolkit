# Monte Carlo Agent Toolkit — Codex Plugin

Data observability skills and enforcement hooks for AI coding agents, powered by Monte Carlo.

**Requires Python 3.10+.**

## Installation

Run the install script from your target repo:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/monte-carlo-data/mc-agent-toolkit/main/plugins/codex/scripts/install.sh)
```

Or specify a target repo path:

```bash
bash install.sh /path/to/your/repo
```

The script handles everything:
1. Copies the plugin into `<repo>/plugins/mc-agent-toolkit/`
2. Registers skills in `<repo>/.agents/skills/` (prevent, generate-validation-notebook, push-ingestion)
3. Writes hooks to `<repo>/.codex/hooks.json` (project-level)
4. Creates `.agents/plugins/marketplace.json` for Codex plugin discovery
5. Adds (and, on reinstall, refreshes) the Monte Carlo MCP server block in `~/.codex/config.toml` with `http_headers`: the required `User-Agent` (workaround for [codex#12859](https://github.com/openai/codex/issues/12859)) plus anonymous toolkit telemetry headers (`x-mcd-toolkit-install-id`, `x-mcd-toolkit-version`) baked in at install time. Opt out with `MC_AGENT_TOOLKIT_TELEMETRY_DISABLED=1` (see Telemetry below).
6. Enables `hooks` in your config (migrating a legacy `codex_hooks` entry if present)
7. Opens a browser for OAuth login with your Monte Carlo account

After installation, restart Codex in your project. You should see "Installed mc-agent-toolkit plugin" on startup.

## How It Works

The plugin registers these hooks to enforce the Monte Carlo Prevent workflow:

| Hook | Event | Matcher | Purpose |
|------|-------|---------|---------|
| bash_hook | PreToolUse | `Bash` | Gate `apply_patch` sent through the shell; prompt for validation before `git commit` |
| bash_hook | PreToolUse | `apply_patch` | Gate edits made with Codex's own `apply_patch` tool |
| post_edit | PostToolUse | `apply_patch` | Track the dbt models a successful `apply_patch` changed |
| turn_end | Stop | — | Suggest validation queries for pending tables |

Every file a patch adds, deletes, updates or moves (both paths of a move) is checked before the patch runs. If any of them is a dbt model without an impact assessment, the whole patch is blocked with one message naming every table.

**Codex versions.** Codex 0.124.0 and later send hook events for the `apply_patch` tool, so edits made with it are gated. Older versions only send them for shell commands, so only `apply_patch` run through the shell is gated there.

**Hook review.** Codex runs a new or changed hook only after you review it. After you install or update the plugin, Codex lists the hooks as "New hook - review required" or "Modified since last trusted - review required" in its hooks browser. Until you trust them they don't run, so edits aren't gated. Review and trust the Monte Carlo hooks after each install or update.

**Hooks load once.** `scripts/install.sh` registers the hooks in `.codex/hooks.json` and removes them from its copy of the plugin (`hooks/prevent/hooks.json` and the manifest's `hooks` entry), so Codex loads them once. Don't also install the plugin from another source in the same project: its own `hooks/prevent/hooks.json` would load next to `.codex/hooks.json`, Codex doesn't remove duplicates, and every Prevent hook would run twice (the Stop hook could ask about validation twice, and each copy needs its own review).

**`apply_patch` in the shell.** Codex applies a shell patch itself, without a shell, only in two forms: the whole command is `apply_patch <<'EOF' ... EOF`, or `cd <dir> && apply_patch <<'EOF' ... EOF` (`applypatch` works too). Prevent checks a shell `apply_patch` only in these two forms. It gates the patch against the command's working directory, or against `<dir>`, and tracks it once it is allowed. Codex 0.166.0 and later tell the hook the folder the shell command runs in. Older versions tell it the session's folder, even when the command runs in another one. The delimiter must be a plain word (`EOF`, `'EOF'` or `"EOF"`). It may be unquoted only if the body has no `$`, backtick or `\`. No body line may start with the delimiter (after any whitespace), the heredoc must end with its delimiter line, `<<-` isn't accepted, and the body must hold one patch. Words are separated by spaces and tabs only. `<dir>` must be written out plainly, quoted or bare, with no `~`, `$`, backtick or `\`. It can't be a bare number (`2024`, `0x1`) or a bare name starting with `=`, start with `-` or `+`, or be blank. Any other command that names `apply_patch` (after removing quotes, a `$` before a quote, and backslashes) runs in a real shell, so Prevent can't tell what it changes. It blocks the command as one it couldn't check, in every repo, whatever the command does. That includes wrappers, pipes, patch files, other heredoc forms, and commands that only mention the name, such as `rg apply_patch`, `cat lib/apply_patch.py` or a commit message. The block asks you to retry with Codex's `apply_patch` tool or the plain form, with one patch, the folder written out plainly (not `~`, a variable, a bare number, or a name starting with `-`, `+` or `=`) and a delimiter no patch line starts with, or to reword a mention (`apply_patc[h]` in a search pattern, `git commit -F <file>` for a message). `MC_PREVENT_HOOKS_DISABLED=1` turns this block off along with the rest of the gate.

## Skills

All skills are registered in `.agents/skills/` during installation.

| Skill | Description | Details |
|---|---|---|
| **Prevent** | Gates dbt model edits with impact assessments, generates monitors-as-code, and produces targeted validation queries. | [Skill README](../../skills/prevent/README.md) |
| **Generate Validation Notebook** | Generates SQL validation notebooks for dbt model changes from a PR or local repo. | [Skill README](../../skills/generate-validation-notebook/README.md) |
| **Push Ingestion** | Generates warehouse-specific collection scripts for pushing metadata, lineage, and query logs to Monte Carlo. | [Skill README](../../skills/push-ingestion/README.md) |
| **Automated Triage** | Guides you through automated alert triage — scoring, deep troubleshooting, classification, and actions. Requires extended MCP toolset. | [SKILL](../../skills/automated-triage/SKILL.md) |

Codex activates skills automatically when you work with dbt models or SQL files. You can also invoke prevent explicitly with `$monte-carlo-prevent`.

## Known Issues

Known limits:

- `apply_patch` limits. The checks assume the patch runs on this machine: a patch for a remote environment is checked against local paths. A path through a symlink is checked both as written and as the file it reaches, so deleting a link to a model asks for that model's assessment too. A patch that fails partway may have changed files without being tracked, because Codex sends PostToolUse only after a successful patch. Another hook that rewrites the patch after Prevent checked it isn't seen. Before Codex 0.166.0, a shell `apply_patch` whose command runs in a folder other than the session's is checked against the session's folder, so relative paths can point at the wrong files; update Codex to 0.166.0 or later. A change whose patch isn't in the command at all, like `git apply`, `sed` or a script, isn't seen. Prevent finds `apply_patch` in a shell command by its name, after removing quotes, a `$` before a quote, and backslashes, so `ap''ply_patch` and `apply_pa$''tch` count. A name the shell builds at run time (`ap${x}ply_patch`, a variable, an escape inside `$'...'` such as `apply_pa$'\x74'ch`) isn't seen.

The skill-based impact assessment (via `SKILL.md`) works reliably regardless of these limits.

## Telemetry

The toolkit sends an anonymous install beacon — a `Toolkit Installed` event so we can count installations and version adoption. It includes an opaque per-install UUID, a per-session UUID, the toolkit version, and the editor it runs in (`codex`). No prompts, arguments, skill names, or code are ever sent. It fires once per machine per toolkit version — the first time you start Codex after installing, and again after each version change (deduped by a local marker) — and is fail-open and non-blocking, never delaying or interrupting your session.

**Authenticated MCP traffic (v1.13.3+).** The same anonymous `install_id` and the toolkit version also ride as HTTP headers (`x-mcd-toolkit-install-id`, `x-mcd-toolkit-version`) on **authenticated** requests to the Monte Carlo MCP server (baked into `~/.codex/config.toml` at install time). This lets the otherwise-anonymous install record be correlated with your account's MCP tool usage server-side — still no prompts, arguments, or code. The opt-out below disables these headers too.

To opt out, set `MC_AGENT_TOOLKIT_TELEMETRY_DISABLED=1` in your shell environment before starting Codex. The toolkit will not phone home.

The data is stored in Mixpanel and Datadog and is used only for product-development decisions. The UUIDs are generated locally on first session and stored under `~/.codex/mc-agent-toolkit/`. Deleting that directory resets your install identity to a fresh anonymous one.

## Architecture

This plugin uses the shared core library at `hooks/prevent/lib/`, a copy of `plugins/shared/prevent/lib/` kept in sync by `./scripts/bump-version.sh --sync-only` (CI rejects symlinks there). The gate, the `apply_patch` parser and edit tracking live in the shared library; the hooks in this plugin are adapters that translate Codex JSON to and from it. `shell_patch.py` is Codex-only: it recognises the two shell `apply_patch` forms Codex applies itself, and flags any other command that names `apply_patch` as one Prevent couldn't check.
