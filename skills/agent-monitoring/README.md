# Monte Carlo Agent Monitoring Skill

Create and manage observability monitors for AI agents — track latency, token usage, quality scores, and execution patterns. Walks users through agent discovery, behavior investigation, and monitor creation through natural conversation.

## Editor & Stack Compatibility

The skill works with any AI editor that supports MCP and the Agent Skills format — including Claude Code, Cursor, and VS Code.

All AI agents monitored by Monte Carlo are supported. The skill uses `get_agent_metadata` to discover agents and their trace tables automatically.

## Prerequisites

- Claude Code, Cursor, VS Code or any editor with MCP support
- Monte Carlo account with Editor role or above
- AI agents sending traces to Monte Carlo (via OTLP or the Monte Carlo SDK)

## Setup

### Via the mc-agent-toolkit plugin (recommended)

Install the plugin for your editor — it bundles the skill, MCP server, and permissions automatically. See the [main README](../../README.md#installing-plugins-recommended) for editor-specific instructions.

### Standalone

1. Configure the Monte Carlo MCP server:
   ```
   claude mcp add --transport http monte-carlo-mcp https://integrations.getmontecarlo.com/mcp
   ```

2. Install the skill:
   ```bash
   npx skills add monte-carlo-data/mc-agent-toolkit --skill agent-monitoring
   ```

3. Authenticate: run `/mcp` in your editor, select `monte-carlo-mcp`, and complete the OAuth flow.

4. Verify: ask your editor "Test my Monte Carlo connection" — it should call `testConnection` and confirm.

<details>
<summary>Legacy: header-based auth (for MCP clients without HTTP transport)</summary>

If your MCP client doesn't support HTTP transport, use `.mcp.json.example` with `npx mcp-remote` and header-based authentication. See the [MCP server docs](https://docs.getmontecarlo.com/docs/mcp-server) for details.

</details>

## How to use it

Ask your AI editor about monitoring your AI agents. The skill guides the agent through discovery, investigation, and monitor creation. No special commands needed.

### Example prompts

- "Help me monitor my AI agents"
- "Set up latency monitoring for my chat agent"
- "Create an evaluation monitor to track answer quality"
- "Alert me when my agent makes too many tool calls"
- "Monitor token usage for my support agent"
- "What agents do I have and what should I monitor?"

### Available monitor types

| Monitor type | Best for |
|---|---|
| **Metric** | Latency, token usage, span volume — quantitative trends over time |
| **Evaluation** | LLM-judged quality scores — relevance, helpfulness, safety |
| **Trajectory** | Execution pattern alerts — excessive tool calls, missing steps, loops |
| **Validation** | Business rule assertions — token limits, latency bounds, compliance |

### What it does

1. **Discovers** your AI agents and their trace tables
2. **Investigates** agent behavior — conversations, traces, error patterns
3. **Recommends** the right monitor type based on what you want to track
4. **Creates** monitors with dry-run preview before committing
