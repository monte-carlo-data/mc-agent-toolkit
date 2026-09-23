# Onboarding Skill

Connect a data platform to Monte Carlo from your editor: choose or provision the **deployment** the
connection runs through (the Monte Carlo hosted cloud node, a collection agent in your network, or
a customer-owned data store), reference the **credentials**, create the **warehouse** and the
**connection**, then validate in the UI. Built on the Monte Carlo REST API v2 tools served by the
Monte Carlo MCP server.

## What it does

When you ask to connect Snowflake, BigQuery, Redshift, Databricks or any other supported platform,
the skill:

1. Lists your deployments and asks two questions only when your request leaves them open: can Monte
   Carlo reach the warehouse over the public internet, and may sampled rows be stored in Monte Carlo.
2. Reuses an existing deployment, or provisions one for a collection agent or a data store and hands
   you the deploy step (Terraform module, CLI) to run in your cloud, then registers it.
3. Stores a *reference* to your credentials (AWS Secrets Manager, GCP Secret Manager, Azure Key
   Vault, an environment variable or a file on the agent). A Snowflake key pair that Monte Carlo
   should hold is created by a CLI or Terraform command you run yourself. **No secret ever passes
   through the chat.**
4. Creates the warehouse and the connection.
5. Ends with a summary of every id it created, and the cleanup order if you abandon the setup.

Three output modes, asked up front: act through the MCP tools now, emit Terraform
(`terraform-provider-montecarlo` plus the `monte-carlo-data/mcd-agent/*` modules), or emit a script
over the `montecarlo` SDK or CLI.

## Prerequisites

- Claude Code or any MCP-capable editor with the Monte Carlo MCP server (bundled by the plugin).
- A Monte Carlo account whose user may manage integrations. The tools that write need a token with
  the `mcp/edit` scope.
- Cloud credentials **on your machine** for the agent, data store or secret-store steps the skill
  hands over; the skill never asks for them.

## Setup

### Via the mc-agent-toolkit plugin (recommended)

Install the plugin for your editor — see the [main README](../../README.md). The skill is bundled;
invoke it with `/monte-carlo-onboarding connect Snowflake` or just describe what you want.

### Standalone

```bash
cp -r skills/onboarding ~/.claude/skills/onboarding
```

## Files

| Path | Role |
|---|---|
| `SKILL.md` | The workflow (hand-written) |
| `reference/api/<tag>.md` | One file per API tag with every tool's arguments, responses and failure modes. **Generated** by [api-codegen](https://github.com/monte-carlo-data/api-codegen) from the API spec; edit the spec, not these files. Until that generator mode ships (YET-2891) they are stubs, with `deployments` and `warehouses` hand-filled from the live tools. |
| `reference/output-modes.md` | Terraform, CLI and SDK snippets for each step |

## Not yet

- **Validation.** There is no v2 validation tool yet; the skill ends with "validate in the UI" until
  the validations API and its `wait_for_validation_run` tool ship.
- **Azure and GCP agent/data-store registration, generic agent credentials, Snowflake key pair.**
  Their requests carry a secret, so they are CLI/Terraform steps rather than MCP tools.

See [SKILL.md](SKILL.md) for the full flow.
