# Onboarding Skill

Connect a data platform to Monte Carlo from your editor: choose or provision the **deployment** the
connection runs through (the Monte Carlo hosted cloud node, a collection agent in your network, or
a customer-owned data store), reference the **credentials**, create the **warehouse** and the
**connection**, then validate in the UI. Built on the Monte Carlo REST API v2 tools served by the
Monte Carlo MCP server.

## What it does

When you ask to connect Snowflake, BigQuery, Redshift, Databricks or any other supported platform,
the skill:

1. Discovers existing deployments and connections, identifies the target platform/cloud/region,
   and asks only for missing requirements: connection origin, credential custody and sample storage.
2. Reuses a suitable Cloud Deployment, Cloud with Customer-hosted Data Store Deployment, or
   Customer-hosted Agent & Data Store Deployment. Where an agent is needed, distinguishes
   cloud-native inbound agents from the outbound Generic Agent (Docker/Kubernetes, preview).
   PrivateLink may support direct Cloud or an agent's connection to the integration; support
   depends on the integration, cloud and region, and the customer's origin policy still applies.
3. References self-hosted credentials or hands over a local CLI/Terraform step for a managed
   Snowflake key pair. **No secret passes through chat.**
4. Reconciles the intended warehouse and connection before creating anything missing.
5. Ends with created/reused IDs, a scoped cleanup order and the next pending step. Connection
   validation remains a UI handoff; creation alone is not a completed onboarding.

The assistant guides the requested connection by default and honors Terraform or SDK/CLI output
when requested. Missing MCP operations use an available v2 local-client handoff, with non-secret
results reconciled before continuing. Sample storage choices do not relocate metadata, metrics
or query logs from Monte Carlo.

## Prerequisites

- An assistant environment with access to the Monte Carlo MCP server.
- A Monte Carlo account whose user may manage integrations. The tools that write need a token with
  the `mcp/edit` scope.
- Cloud credentials **on your machine** for the agent, data store or secret-store steps the skill
  hands over; the skill never asks for them.

## Setup

### Via the mc-agent-toolkit plugin (recommended)

Install the toolkit adapter for your environment — see the [main README](../../README.md).
Describe the platform you want to connect.

### Standalone

Load the `onboarding` directory, including `SKILL.md` and its `reference` directory, using the
skill or resource mechanism supported by your environment. Configure the Monte Carlo MCP
connection for the intended account. The workflow requires no particular assistant provider.

## Files

| Path | Role |
|---|---|
| `SKILL.md` | The workflow (hand-written) |
| `reference/api/<tag>.md` | One file per API tag with every tool's arguments, responses and failure modes. **Generated** by [api-codegen](https://github.com/monte-carlo-data/api-codegen) from the API spec; edit the spec, not these files. Until that generator mode ships they are stubs, with `deployments` and `warehouses` hand-filled from the live tools. |
| `reference/deployment-guide.md` | Cloud-specific prerequisites, network paths and official setup guides |
| `reference/output-modes.md` | Terraform, CLI and SDK snippets for each step |

## Not yet

- **Validation.** The validations API is live (`validate_connection` + `get_validation_run`, 202 +
  polling) and the skill uses it when the tools are served; a waiter tool that polls for you is
  planned, and until then the skill ends with "validate in the UI".
- **Azure and GCP agent/data-store registration, generic agent credentials, Snowflake key pair.**
  Their requests carry a secret, so they are CLI/Terraform steps rather than MCP tools.

See [SKILL.md](SKILL.md) for the full flow.
