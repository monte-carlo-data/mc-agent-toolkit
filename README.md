# mc-agent-toolkit

Monte Carlo's official toolkit for AI coding agents. Integrates Monte Carlo's data observability platform — lineage, monitoring, validation, and alerting — directly into your development workflow.

## Features

The toolkit bundles the following capabilities as a single **mc-agent-toolkit** plugin. Each feature is a [skill](skills/) that can also be used standalone.

| Feature | Description | Details |
|---|---|---|
| **MC Prevent** | Surfaces lineage, alerts, and blast radius before code changes. Generates monitors-as-code and targeted validation queries to prevent data incidents. | [README](skills/prevent/README.md) |
| **MC Generate Validation Notebook** | Generates SQL validation notebooks for dbt model changes, with targeted queries comparing baseline and development data. | [README](skills/generate-validation-notebook/README.md) |
| **MC Push Ingestion** | Generates warehouse-specific collection scripts for pushing metadata, lineage, and query logs to Monte Carlo. | [README](skills/push-ingestion/README.md) |

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

## Installing the plugin (recommended)

**Monte Carlo recommends installing the mc-agent-toolkit plugin.** It bundles skills together with hooks, MCP server configuration, and editor-specific capabilities for a richer experience. See the [plugins README](plugins/README.md) for editor support details.

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

See the [Claude Code plugin README](plugins/claude-code/README.md) for detailed setup and usage.

### Cursor

Run the install script:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/monte-carlo-data/mc-agent-toolkit/main/plugins/cursor/scripts/install.sh)
```

Then restart Cursor. See the [Cursor plugin README](plugins/cursor/README.md) for details.

### GitHub Copilot CLI

```bash
git clone https://github.com/monte-carlo-data/mc-agent-toolkit.git

# Install hooks into your dbt project
./mc-agent-toolkit/plugins/copilot/scripts/install.sh /path/to/your/dbt-project

# Install the plugin (skills + MCP)
copilot plugin install ./mc-agent-toolkit/plugins/copilot
```

See the [Copilot CLI plugin README](plugins/copilot/README.md) for details.

## Using skills directly (advanced)

Skills can also be used standalone without the plugin. This is for users who want to install individual skills via registries or use them with editors not listed above.

```bash
npx skills add monte-carlo-data/mc-agent-toolkit --skill prevent
```

Or copy directly:

```bash
cp -r skills/prevent ~/.claude/skills/prevent
```

See the [skills directory](skills/) for the full list and individual READMEs.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on adding skills, creating plugins, and submitting pull requests.

## License

This project is licensed under the Apache-2.0 license — see [LICENSE](LICENSE) for details.

## Security

See [SECURITY.md](SECURITY.md) for reporting vulnerabilities.
