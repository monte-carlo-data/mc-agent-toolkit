# Monte Carlo Agent Toolkit — Cortex Code Plugin

Cortex Code (CoCo) plugin that brings Monte Carlo data observability into Snowflake's coding agent, in both the CoCo Desktop app and the `cortex` CLI. Bundles skills, hooks, commands, and the Monte Carlo MCP server in a single plugin.

**Requires Python 3.10+ and [CoCo Desktop](https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code-desktop) or the [Cortex Code CLI](https://docs.snowflake.com/en/user-guide/cortex-code/cortex-code).**

## Installation

### CoCo Desktop

CoCo Desktop has no `cortex` command, so install from GitHub. Every release publishes a copy of this plugin that is already in CoCo Desktop's format to the `coco-desktop` branch, so CoCo installs it as-is.

1. In CoCo Desktop, open **Settings → Plugins** and choose **Add from GitHub**.
2. Enter `https://github.com/monte-carlo-data/mc-agent-toolkit/tree/coco-desktop`.

If you added the toolkit to CoCo Desktop another way before (for example with **Add Local Plugin**), remove that copy first. Two copies load side by side and their skill names collide.

CoCo should report the plugin as already CoCo-ready and install it without changes. The plugin page then shows the GitHub source, a **Sync** button, and the skills.

To pin a version instead of following the latest release, use the release's tag: `https://github.com/monte-carlo-data/mc-agent-toolkit/tree/coco-desktop-v<version>` (for example `coco-desktop-v1.32.0`). Each tag holds one release and never changes.

### Cortex Code CLI

Cortex Code's `cortex plugin install` can't consume this plugin directly from the repo, because the skill entries are symlinks shared across all editor plugins (they point outside the plugin directory, which the installer rejects). The install script materializes a symlink-resolved copy and installs that for you:

```bash
git clone https://github.com/monte-carlo-data/mc-agent-toolkit.git
cd mc-agent-toolkit
bash plugins/cortex-code/scripts/install.sh
```

The script clones (or uses your local checkout), resolves the symlinks into a staging copy, and runs `cortex plugin install`. Verify with:

```bash
cortex plugin list
```

You should see `mc-agent-toolkit` listed as `[enabled, managed]` with command, skill, hook, and MCP-server components.

## Setup

1. **Authenticate with Monte Carlo.**
   - CLI: run `/mcp` inside Cortex Code (or `cortex mcp`), select the Monte Carlo server, and complete the OAuth flow.
   - CoCo Desktop: the plugin adds the `monte-carlo-mcp` server, listed under **Settings → MCP → From Plugins**. If it isn't connected, connect it there and complete the Monte Carlo sign-in.
2. **Verify** — ask Cortex: "Test my Monte Carlo connection."

## Usage

- **Invoke a skill explicitly** with `$<skill-name>`, e.g. `$monte-carlo-prevent` or `$monte-carlo-asset-health`. Run `/skill list` to see what's available.
- **Auto-activation** — Cortex selects the right skill from your request (e.g. editing a dbt model activates Prevent; "how healthy is this table?" activates Asset Health).
- **Validation** — run `/mc-validate` (or `/mc-agent-toolkit:mc-validate`) to generate or run validation queries for the dbt models you changed this session.

## Telemetry

The toolkit sends anonymous skill-usage telemetry by default — which skills are invoked, how often. Each event includes an opaque per-install UUID, a per-session UUID, the skill name, the toolkit version, and the editor it runs in (`cortex-code`). No prompts, arguments, or code are ever sent.

It also sends a `Toolkit Installed` beacon once per toolkit version — the first time you start Cortex Code after installing, and again after each version change — deduped by a local marker, independent of whether you ever run a skill. It carries the install/session UUIDs, toolkit version, and editor (`cortex-code`) — no skill field. Like the skill beacon, it is fail-open and non-blocking.

**Authenticated MCP traffic.** The plugin's MCP config asks Cortex Code to run a headers helper that adds the same anonymous `install_id`, a per-session id, and the toolkit version as HTTP headers (`x-mcd-toolkit-install-id`, `x-mcd-toolkit-session-id`, `x-mcd-toolkit-version`) to **authenticated** requests to the Monte Carlo MCP server. Current Cortex Code releases (CoCo Desktop 2.0.0 and Cortex Code CLI 1.2.46) don't run the helper, so they send none of these headers. Your MCP calls still reach the server through the toolkit's endpoint, but they aren't linked to this install. If a later Cortex Code release runs the helper, the headers carry only the opaque ids and version (no prompts, arguments, or code), and the opt-out below disables them.

To opt out, set `MC_AGENT_TOOLKIT_TELEMETRY_DISABLED=1` in your shell environment before starting Cortex Code. The toolkit will not phone home.

The data is stored in Mixpanel and Datadog and is used only for product-development decisions about which skills to invest in. The UUIDs are generated locally on first session and stored under `~/.snowflake/cortex/mc-agent-toolkit/` (Cortex Code's own config home) — separate from any Claude Code toolkit install, so each editor keeps its own anonymous identity. Deleting that directory resets the Cortex Code install identity to a fresh one.

## Available Features

| Feature | Description | Details |
|---|---|---|
| **Monitoring Advisor** | Analyzes data coverage, creates monitors for warehouse tables and AI agents — covers coverage gaps, use-case analysis, data monitor creation, and agent observability. | [Skill README](https://github.com/monte-carlo-data/mc-agent-toolkit/blob/v1.32.4/skills/monitoring-advisor/README.md) |
| **Prevent** | Gates dbt model edits with impact assessments, generates monitors-as-code, and produces targeted validation queries. Full hook enforcement. | [Skill README](https://github.com/monte-carlo-data/mc-agent-toolkit/blob/v1.32.4/skills/prevent/README.md) |
| **Generate Validation Notebook** | Generates SQL validation notebooks for dbt model changes from a PR or local repo. | [Skill README](https://github.com/monte-carlo-data/mc-agent-toolkit/blob/v1.32.4/skills/generate-validation-notebook/README.md) |
| **Push Ingestion** | Generates warehouse-specific collection scripts for pushing metadata, lineage, and query logs to Monte Carlo. Includes 10 `/mc-*` slash commands. | [Skill README](https://github.com/monte-carlo-data/mc-agent-toolkit/blob/v1.32.4/skills/push-ingestion/README.md) |
| **Onboarding** | Connects a warehouse to Monte Carlo through the REST API v2 tools: deployment choice, credential references, warehouse and connection; Terraform or SDK/CLI script output on request. `/monte-carlo-onboarding`. | [Skill README](https://github.com/monte-carlo-data/mc-agent-toolkit/blob/v1.32.4/skills/onboarding/README.md) |
| **Automated Triage** | Guides you through automated alert triage — scoring, deep troubleshooting, classification, and actions. Requires extended MCP toolset. | [SKILL](https://github.com/monte-carlo-data/mc-agent-toolkit/blob/v1.32.4/skills/automated-triage/SKILL.md) |

All 21 skills are bundled — see the [skills directory](https://github.com/monte-carlo-data/mc-agent-toolkit/tree/v1.32.4/skills) for the full list. CoCo Desktop has no slash commands, so the Desktop build turns them into skills: it has 35 in all.

The Prevent feature includes **PreToolUse hooks that block edits to dbt SQL files** until an impact assessment runs. The hooks only fire on `.sql` files inside dbt model, macro, or snapshot directories — they do not affect non-dbt files, except that an `apply_patch` call that changes a gated dbt file and other files together is blocked as a whole.

Cortex Code (CoCo Desktop and the CLI) gives models whose name contains "gpt" or "openai" an `apply_patch` tool instead of edit and write tools; the hooks check every file a patch touches, so those models are gated too. In CoCo Desktop, hooks run only in a trusted workspace.

One Prevent behavior is CLI-only for now: the **pre-commit checkpoint**. Desktop doesn't pass a pre-tool hook's added context to the model, so the reminder before `git commit` doesn't appear in Desktop.

Also in Desktop, the first retry of an edit right after the impact assessment is denied once more, because Desktop saves the assistant's completion line to the session history only after that retry's hook has run. Retrying the edit again goes through.

**To disable the Prevent hooks**, set `MC_PREVENT_HOOKS_DISABLED=1` in your environment. The hooks will exit immediately without blocking any edits.

See the [Prevent Hook Behavior](https://github.com/monte-carlo-data/mc-agent-toolkit/blob/v1.32.4/plugins/README.md#prevent-hook-behavior) section in the plugins README for full details on scope and configuration.

## Updating

**CoCo Desktop:** press **Sync** on the plugin page. It re-installs the latest release from the `coco-desktop` branch. A plugin installed from a `coco-desktop-v<version>` tag stays on that version; to upgrade it, remove it and add the newer tag.

**CLI:** re-run the installer from your repo checkout (the clone from the Installation step) to pull the latest skills and hooks:

```bash
cd mc-agent-toolkit
git pull
bash plugins/cortex-code/scripts/install.sh
```

## Uninstalling

**CoCo Desktop:** remove the plugin from **Settings → Plugins**.

**CLI:**

```bash
cortex plugin uninstall mc-agent-toolkit
```

## Architecture

Cortex Code wraps Claude Code, so this plugin reuses the same SKILL.md skills, the same prevent hook lifecycle (PreToolUse/PostToolUse/Stop), and the same MCP configuration. Hooks live in a single `hooks/hooks.json` at the plugin root, which CoCo Desktop loads (it ignored the manifest's list of hook files), and their matchers use Cortex's lowercase tool IDs (`^bash$`, `^(edit|write|multi_edit|apply_patch)$`, `^skill$`) because matching is case-sensitive. For `apply_patch`, the edit hooks read the patch text and check or track each file in it (`hooks/prevent/apply_patch.py`). The CoCo Desktop copy is built by `scripts/build_coco_desktop.py` and published by `scripts/publish_coco_desktop.py` from the release workflow. The other Cortex-specific adaptation is the prevent transcript reader: Cortex stores session messages in a sibling `<id>.history.jsonl` and persists hook output back into the transcript, so the gate scans only assistant-authored text to find its completion marker. See the [plugins README](https://github.com/monte-carlo-data/mc-agent-toolkit/blob/v1.32.4/plugins/README.md) for the editor-support comparison and hook-format details, and the [Plugin Architecture Guide](https://github.com/monte-carlo-data/mc-agent-toolkit/blob/v1.32.4/docs/plugin-architecture-guide.md) for the shared-core/adapter design.

## Changelog

See [CHANGELOG.md](docs/CHANGELOG.md).
