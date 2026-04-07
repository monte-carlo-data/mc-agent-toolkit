# mc-agent-toolkit

Monte Carlo's official toolkit for AI coding agents. Contains skills and plugins that integrate Monte Carlo's data observability platform — lineage, monitoring, validation and alerting — into your development workflow.

## Prerequisites

- A [Monte Carlo](https://www.montecarlodata.com) account with Editor role or above
- Monte Carlo MCP server — configure with:
  ```
  claude mcp add --transport http monte-carlo-mcp https://integrations.getmontecarlo.com/mcp
  ```
  Then authenticate: run `/mcp` in Claude Code, select `monte-carlo-mcp`, and complete the OAuth flow in your browser.

  > **Note:** The `mc-agent-toolkit` plugin bundles its own MCP server, so if you install the plugin you can skip this step.

  See [official docs](https://docs.getmontecarlo.com/docs/mcp-server#option-1-oauth-21-recommended-for-mcp-clients-that-support-http-transport) for other MCP clients and advanced options.

  <details>
  <summary>Legacy: header-based auth (for MCP clients without HTTP transport)</summary>

  If your MCP client doesn't support HTTP transport, use `.mcp.json.example` with `npx mcp-remote` and header-based authentication. See the [MCP server docs](https://docs.getmontecarlo.com/docs/mcp-server) for details.

  </details>


## Installing plugins (recommended)

**Monte Carlo recommends installing skills via their corresponding plugins.** Plugins bundle the skill together with hooks, configuration and additional capabilities that provide a richer experience (e.g., automatic context enrichment from MC lineage data, executing validation queries and synthesizing results in your coding sessions).

### Claude Code

1. Add the marketplace:
   ```
   /plugin marketplace add monte-carlo-data/mc-marketplace
   ```
2. Install the plugin:
   ```
   /plugin install mc-agent-toolkit@mc-marketplace
   ```
3. Updates — `claude plugin update` pulls in the latest skill and hook changes.

### Cursor

Run the install script (clones the repo and copies the `mc-agent-toolkit` plugin to `~/.cursor/plugins/local/mc-agent-toolkit`):

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/monte-carlo-data/mc-agent-toolkit/main/plugins/cursor/scripts/install.sh)
```

Or install manually:

```bash
git clone https://github.com/monte-carlo-data/mc-agent-toolkit.git
cd mc-agent-toolkit
bash plugins/cursor/scripts/install.sh
```

Then restart Cursor (or run **Developer: Reload Window** from the Command Palette). The Monte Carlo MCP server will prompt for OAuth authentication on first use.

### GitHub Copilot CLI

Install from a local clone:

```bash
git clone https://github.com/monte-carlo-data/mcd-agent-toolkit.git

# Install hooks into your dbt project
./mcd-agent-toolkit/plugins/copilot/scripts/install.sh /path/to/your/dbt-project

# Install the plugin (skills + MCP)
copilot plugin install ./mcd-agent-toolkit/plugins/copilot
```

Verify with `copilot plugin list`, then start a Copilot session. The Monte Carlo MCP server will prompt for authentication on first use.

## Available plugins

All editors use a single **`mc-agent-toolkit`** plugin that bundles the following features:

| Feature | Description |
|---|---|
| **MC Prevent** | Analyzes schema changes using MC lineage, monitoring, alerts, queries, and table metadata. Generates Monte Carlo monitors and validation queries to prevent data incidents. |
| **MC Generate Validation Notebook** | Generates executable validation queries from a pull request and packages them into Monte Carlo notebooks for direct testing. |
| **MC Push Ingestion** | Generates warehouse-specific collection scripts and guides customers through pushing metadata, lineage, and query logs to Monte Carlo. |

## Using skills directly (advanced)

Skills can also be used standalone without the plugin wrapper. This section is for users who want to submit skills to registries or use them with non-Claude-Code agents. Monte Carlo recommends the plugin approach above for the best experience.

### skills.sh (Vercel CLI)

```bash
npx skills add monte-carlo-data/mc-agent-toolkit --skill prevent
```

### Manual installation

Copy to `~/.claude/skills/` or `.agents/skills/`:

```bash
cp -r skills/prevent ~/.claude/skills/prevent
```

## Available skills

| Skill | Description |
|---|---|
| `prevent` | Analyzes schema changes using MC lineage, monitoring, alerts, queries, and table metadata. Generates monitors and validation queries to prevent data incidents. |
| `generate-validation-notebook` | Generates executable validation queries from a pull request and packages them into Monte Carlo notebooks for direct testing. |
| `push-ingestion` | Generates warehouse-specific collection scripts and guides customers through pushing metadata, lineage, and query logs to Monte Carlo. |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on adding skills, creating plugins, and submitting pull requests.

## License

This project is licensed under the Apache-2.0 license — see [LICENSE](LICENSE) for details.

## Security

See [SECURITY.md](SECURITY.md) for reporting vulnerabilities.
