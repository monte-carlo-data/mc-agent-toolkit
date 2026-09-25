# Onboarding Skill

Connect a data platform to Monte Carlo from your editor: choose or provision the **deployment** the
connection runs through (the Monte Carlo hosted cloud node, a collection agent in your network, or
a customer-owned data store), reference the **credentials**, create the **warehouse** and the
**connection**, then validate the connection. Built on the Monte Carlo REST API v2 tools served by the
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
   Snowflake key pair. **No secret passes through chat.** See *How credentials are handled*.
4. Reconciles the intended warehouse and connection before creating anything missing.
5. Validates the connection over MCP and reports each check's result, falling back to the UI test
   only when the session does not serve the validation tools.
6. Ends with created/reused IDs, the validation result, a scoped cleanup order and the next
   pending step. Creation alone is not a completed onboarding.

The assistant guides the requested connection by default and honors Terraform or SDK/CLI output
when requested. Missing MCP operations use an available v2 local-client handoff, with non-secret
results reconciled before continuing. Sample storage choices do not relocate metadata, metrics
or query logs from Monte Carlo.

## How credentials are handled

Monte Carlo exposes **no MCP tool that accepts or returns a credential**. Anything a tool receives,
the model has to write into the tool call, and anything a tool returns, the model reads. Either way
a secret would end up in the model's context, the conversation transcript and the logs of the
systems in between. So the skill works with credentials in one of two ways:

- **Reference a secret you keep.** For a collection agent, the credentials stay in your AWS Secrets
  Manager, GCP Secret Manager, Azure Key Vault, an environment variable or a file on the agent.
  The skill passes only the reference (secret name, ARN, vault, variable name or path), and the
  agent reads the value at query time.
- **Run a local step.** Credentials Monte Carlo must hold, such as a Snowflake key pair or a
  generic agent token, are created by a CLI command or a Terraform resource that the skill writes
  for you. You run it on your machine; it reads the secret from a file and sends it to Monte
  Carlo directly, and you give back only the resulting id.

The operations this rules out as MCP tools are listed under *Not yet*. If you paste a secret into
the chat anyway, the skill stops, asks you to rotate it, and continues with one of the paths above.

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

- **Azure and GCP agent/data-store registration, generic agent credentials, Snowflake key pair.**
  Their requests or responses carry a secret, so they are CLI/Terraform steps rather than MCP
  tools, by design (see *How credentials are handled*).

See [SKILL.md](SKILL.md) for the full flow.
