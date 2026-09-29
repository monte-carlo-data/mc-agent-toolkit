# Onboarding Skill

Connect a data platform to Monte Carlo from your editor: choose or provision the **deployment** the
connection runs through (the Monte Carlo hosted cloud node, a collection agent in your network, or
a customer-owned data store), reference the **credentials**, create the **warehouse** and the
**connection**, then validate the connection. Built on the Monte Carlo REST API v2 tools served by
the Monte Carlo MCP server.

## What it does

When you ask to connect Snowflake, BigQuery, Redshift, Databricks or any other supported platform,
the skill:

1. Discovers existing deployments, agents, data stores, warehouses and connections, shows you
   that inventory and what can be added (which integrations each kind of deployment supports and
   with which credential options), then asks what you want to connect. One run can onboard
   several integrations; each is checked for support before any other question about it.
2. Identifies the target platform/cloud/region and asks only for missing requirements:
   connection origin, credential custody and sample storage.
3. Reuses a suitable Cloud Deployment, Cloud with Customer-hosted Data Store Deployment, or
   Customer-hosted Agent & Data Store Deployment. Where an agent is needed, distinguishes
   cloud-native inbound agents from the outbound Generic Agent (Docker/Kubernetes, preview).
   PrivateLink may support direct Cloud or an agent's connection to the integration; support
   depends on the integration, cloud and region, and the customer's origin policy still applies.
4. References self-hosted credentials or hands over a local CLI/Terraform step for Monte
   Carlo-managed credentials (a Snowflake key pair, for example). **No secret passes through chat.** See *How credentials are handled*.
5. Reconciles the intended warehouse and connection before creating anything missing.
6. Validates the connection over MCP and reports each check's result, falling back to the UI test
   only when the session does not serve the validation tools.
7. Ends with created/reused IDs, the validation result, a scoped cleanup order and the next
   pending step. Creation alone is not a completed onboarding.

The assistant uses the MCP tools for every step they serve. A step moves to your machine only
when it carries a secret, or its tool is not served: you get the
[mc-cli](https://github.com/monte-carlo-data/mc-cli) command (`montecarlo`, the REST API v2 CLI)
and the equivalent Terraform resource side by side, you run the one you prefer, and you give back
only the non-secret result. The assistant never runs it for you, even when it has a shell and
you gave it the file's path. Ask for Terraform or an SDK script for the whole onboarding instead,
if you prefer.

Supported integrations are read from the tools in your session rather than listed in the skill:
the `create_warehouse` schema for integrations connected through a collection agent, and the
Monte Carlo-managed credential tools (or `montecarlo credentials create --help`) for credentials
Monte Carlo stores. A type in neither is handed off to the UI. Sample storage choices do not relocate metadata, metrics
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
  Carlo directly, and you give back only the resulting id. Terraform takes a secret you supply,
  such as the key pair, as a write-only argument (Terraform 1.11 or later), so it is never stored
  in state or a plan. A secret Monte Carlo generates, such as the agent token, is returned once and
  stays in that resource's state, so keep state encrypted and access-limited.

The operations this rules out as MCP tools are listed under *Not yet*. If you paste a secret into
the chat anyway, the skill stops, asks you to rotate it, and continues with one of the paths above.

## Prerequisites

- An assistant environment with access to the Monte Carlo MCP server.
- A Monte Carlo account whose user may manage integrations. The tools that write need a token with
  the `mcp/edit` scope.
- Cloud credentials **on your machine** for the agent, data store or secret-store steps the skill
  hands over; the skill never asks for them.
- [mc-cli](https://github.com/monte-carlo-data/mc-cli) for the steps you run locally. Until its
  first release, build it from source (`go build -o . ./cmd/montecarlo` in a clone), then set a
  profile with `montecarlo profile set default --api-id <id> --api-token-prompt`. The legacy
  `montecarlodata` Python CLI installs a command with the same name but speaks a different API;
  `montecarlo deployments --help` confirms you are running mc-cli.

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
| `reference/connection-inputs.md` | The inputs each deployment, credential path and connection type requires (including the keys a self-hosted secret must carry), and the rule that each comes from the customer or discovery, never an example value |

## Not yet

- **Azure and GCP agent/data-store registration, generic agent credentials, Monte Carlo-managed
  warehouse credentials (such as the Snowflake key pair).**
  Their requests or responses carry a secret, so they are CLI/Terraform steps rather than MCP
  tools, by design (see *How credentials are handled*).

See [SKILL.md](SKILL.md) for the full flow.
