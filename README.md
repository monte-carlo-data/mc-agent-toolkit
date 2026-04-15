# MC Agent Toolkit

Monte Carlo's official toolkit for AI coding agents. Brings data observability — lineage, monitoring, validation, alerting, and metadata ingestion — directly into your development workflow. The toolkit bundles multiple skills into a single plugin that works across supported editors.

## Features

The toolkit bundles the following capabilities as a single **mc-agent-toolkit** plugin. Each feature is a [skill](skills/) that can also be used standalone.

| Feature | Description | Details |
|---|---|---|
| **Asset Health** | Checks the health of a data table — surfaces last activity, alerts, monitoring coverage, importance, and upstream dependency health. | [README](skills/asset-health/README.md) |
| **Monitoring Advisor** | Analyzes data coverage across warehouses and use cases, identifies monitoring gaps, and creates monitors to protect critical data. | [README](skills/monitoring-advisor/README.md) |
| **Monitor Creation** | Guides AI agents through creating monitors correctly — validates tables, fields, and parameters before generating monitors-as-code YAML. | [README](skills/monitor-creation/README.md) |
| **Prevent** | Surfaces lineage, alerts, and blast radius before code changes. Generates monitors-as-code and targeted validation queries to prevent data incidents. | [README](skills/prevent/README.md) |
| **Generate Validation Notebook** | Generates SQL validation notebooks for dbt model changes, with targeted queries comparing baseline and development data. | [README](skills/generate-validation-notebook/README.md) |
| **Push Ingestion** | Generates warehouse-specific collection scripts for pushing metadata, lineage, and query logs to Monte Carlo. | [README](skills/push-ingestion/README.md) |
| **Automated Triage** | Guides AI agents through automated alert triage — scoring alerts, running deep troubleshooting on high-signal ones, classifying, and taking actions. | [SKILL](skills/automated-triage/SKILL.md) |
| **Storage Cost Analysis** | Identifies storage waste patterns (unread, zombie, dead-end tables) and recommends safe cleanup with cost estimates. | [README](skills/storage-cost-analysis/README.md) |
| **Performance Diagnosis** | Diagnoses slow pipelines and expensive queries across Airflow, dbt, and Databricks with tiered investigation. | [README](skills/performance-diagnosis/README.md) |
| **Remediation** | Investigates and remediates data quality alerts — runs TSA root cause analysis, discovers available tools, executes fixes (or escalates), and documents the resolution. | [README](skills/remediation/README.md) |
| **Agent Monitoring** | Investigation and monitor creation guide for AI agent observability. | [README](skills/agent-monitoring/README.md) |

## Installing the plugin (recommended)

**Monte Carlo recommends installing the mc-agent-toolkit plugin.** The plugin bundles all skills together with hooks, the Monte Carlo MCP server, and agent-specific capabilities — no separate MCP configuration or authentication setup needed. See the [plugins page](plugins/) for the full list of supported coding agents.

### Claude Code

1. Add the marketplace:
   ```
   /plugin marketplace add monte-carlo-data/mc-agent-toolkit
   ```
2. Install the plugin:
   ```
   /plugin install mc-agent-toolkit@mc-marketplace
   ```
3. Updates — `claude plugin update` pulls in the latest skill and hook changes.

See the [Claude Code plugin README](plugins/claude-code/README.md) for detailed setup and usage.

For other coding agents (Cursor, Copilot CLI, OpenCode, Codex), see the [plugins page](plugins/) for installation guides.

## Using skills directly (advanced)

Skills can also be used standalone without the plugin. This is for users who want to install individual skills via registries or use them with agents not listed above.

### Prerequisites

- A [Monte Carlo](https://www.montecarlodata.com) account with Editor role or above
- Monte Carlo MCP server — configure with:
  ```
  claude mcp add --transport http monte-carlo-mcp https://mcp.getmontecarlo.com/mcp
  ```
  Then authenticate: run `/mcp` in your editor, select `monte-carlo-mcp`, and complete the OAuth flow.

  See [official docs](https://docs.getmontecarlo.com/docs/mcp-server#option-1-oauth-21-recommended-for-mcp-clients-that-support-http-transport) for other MCP clients and advanced options.

  <details>
  <summary>Legacy: header-based auth (for MCP clients without HTTP transport)</summary>

  If your MCP client doesn't support HTTP transport, use `.mcp.json.example` with `npx mcp-remote` and header-based authentication. See the [MCP server docs](https://docs.getmontecarlo.com/docs/mcp-server) for details.

  </details>

### Installation

```bash
npx skills add monte-carlo-data/mc-agent-toolkit --skill prevent
```

Or copy directly:

```bash
cp -r skills/prevent ~/.claude/skills/prevent
```

See the [skills directory](skills/) for the full list and individual READMEs.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on adding skills, creating plugins, and submitting pull requests. It also covers [plugin architecture](docs/plugin-architecture-guide.md) and [releasing new versions](CONTRIBUTING.md#releasing).

## License

This project is licensed under the Apache-2.0 license — see [LICENSE](LICENSE) for details.

## Security

See [SECURITY.md](SECURITY.md) for reporting vulnerabilities.
