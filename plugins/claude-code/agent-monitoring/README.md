# mc-agent-monitoring plugin

Monte Carlo Agent Monitoring plugin for Claude Code. Creates observability monitors for AI agents — metric, evaluation, trajectory, and validation monitors.

## Install

1. Add the marketplace:
   ```
   /plugin marketplace add monte-carlo-data/mcd-agent-toolkit
   ```
2. Install the plugin:
   ```
   /plugin install mc-agent-monitoring@mcd-agent-toolkit
   ```
3. Authenticate: run `/mcp`, select `monte-carlo`, and complete the OAuth flow.

## What's included

- **Skill:** Agent monitoring — discovery, investigation, and monitor creation
- **MCP server:** Monte Carlo public MCP server (bundled)
- **Permissions:** Auto-approve Monte Carlo tool calls

## Skill docs

See [skills/agent-monitoring/README.md](../../../skills/agent-monitoring/README.md) for detailed usage and examples.
