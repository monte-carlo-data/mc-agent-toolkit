---
name: monte-carlo-onboarding
description: Connect warehouses, BI tools (Tableau, Looker, Power BI) and custom connectors to Monte Carlo with API v2 tools: show what exists, reference credentials, create, validate and fix connections. Use to onboard platforms or generate Terraform or scripts.
metadata:
  bucket: Setup
---

# Monte Carlo Onboarding

Walk a customer from "connect `<warehouse or BI tool>` to Monte Carlo" to working connections,
one or several, using the Monte Carlo MCP tools for deployments, credentials, warehouses, BI
containers and connections. Start by showing what already exists and what can be added, then
resolve only the missing customer decisions, and reuse or provision the deployment before
creating a connection. A request to connect Snowflake does not imply that the customer knows
which deployment or collection agent they need.

A warehouse connection goes on a **warehouse**. A Tableau, Looker or Power BI connection goes on a
**BI container** instead: the BI tool's counterpart of a warehouse, with a type (`tableau`,
`looker` or `power-bi`) and a deployment. The steps are the same; Step 3 picks the parent.

A **custom connector** is a connection type a customer's collection agent registered, or one whose
data the customer pushes. Its type decides the parent and the deployment; *Custom connectors*,
after Step 5, adapts Steps 1 to 5 for it.

## Tools and supporting references

Use the configured Monte Carlo MCP connection for the intended account. If multiple connections
are available, verify the account before choosing one. Tool names below identify operations;
match them to the tools and schemas exposed by the current environment.

Read the supporting references with the environment's available file or resource capability:

<!-- plugin-only:start -->
- API references in `reference/api/<tag>.md`: per-tag arguments, responses and failure modes.
<!-- plugin-only:end -->
- [Deployment guide](reference/deployment-guide.md): prerequisites, networking and handoffs.
- [Output modes](reference/output-modes.md): Terraform, SDK and CLI examples.
- [Connection inputs](reference/connection-inputs.md): the inputs each deployment, credential path
  and connection type requires, and where each value must come from.
- [Troubleshooting](reference/troubleshooting.md): a connection that worked and now fails; the
  order of checks and what each validation result means.

If a referenced resource is unavailable, identify what is missing and consult the linked official
documentation before proceeding. Do not guess a tool schema or provisioning parameter.

This workflow covers connecting supported data platforms and selecting deployments, agents,
data stores and credentials, and fixing a connection that stopped working (the troubleshooting
reference; it skips the onboarding steps below). For metadata or lineage without a connector use push-ingestion;
for Connection Auth Rules JSON use connection-auth-rules; for AI agent instrumentation use
instrument-agent; for an already-connected warehouse's monitoring use monitoring-advisor.


## Rules that hold for the whole run

1. **v2 tools only.** Use the tools listed under *Tools* below, and the tool schema or the per-tag
   API reference for any other v2 operation, and nothing else for reads or writes about deployments, agents, data
   stores, credentials, warehouses, BI and ETL containers, connection types and connections. Other
   Monte Carlo tools that list warehouses, integrations or platform services, or that test an
   integration, are a different API with different ids and fields. Never mix them into this flow,
   even to "double-check".
2. **No secret ever travels through the chat or a tool argument.** Not a private key, password,
   service-account key, token, or passphrase. Credentials the customer hosts are *referenced*
   (secret name, ARN, vault, variable name, file path). Credentials Monte Carlo must hold (managed
   warehouse credentials such as a Snowflake key pair, a generic agent token) are created by a CLI or Terraform step the customer
   runs on their own machine. The reason is structural, not a preference: whatever a tool receives
   the model has to write into the call, and whatever a tool returns the model reads, so a secret
   in either direction lands in the model's context, the transcript and the logs of every system
   in between. That is why Monte Carlo exposes **no MCP tool that accepts or returns a secret**;
   the operations that do are CLI or Terraform steps. Tell the user this the first time the flow
   reaches a credential, so a local step reads as a safeguard rather than a gap. If the user
   pastes a secret into the chat, stop, tell them it is now in the transcript and should be
   rotated (call it the password or key they pasted: never repeat or quote it, not even to ask
   for rotation), and continue with the reference or CLI path. A secret on disk is no different: when
   the user gives the path of a key or credential file on their machine, the path only goes into
   a command they run. Never open, list, read, copy or inspect that file with any tool, not even
   its first line to check the format, because what a tool reads lands in the context just as a
   paste does. Say so before anything else, add that Monte Carlo cannot read a file on their
   machine either, and offer the routes the deployment allows: they put the secret into their
   own secret store themselves and give you its reference (collection agent only), or they run
   the mc-cli or Terraform step you write, which reads the file locally.
3. **Never create a deployment with nothing behind it.** A deployment exists to host a collection
   agent or a data store. It is provisioned only when one of those will be registered on it, in
   the same run or in a follow-up the user commits to.
4. **Confirm the concrete plan before writing.** Explain what will be reused or created and
   which steps the customer must run. Approval of the whole plan covers its writes; do not ask
   again for each call. Confirm a change of scope or a destructive action separately.
5. **Every run ends with the summary** in *Step 6*, whether it completed, stopped early, or hit an
   error. Ids created by this run are the customer's cleanup list.
6. **MCP tools first; a local step only when a secret is involved.** Use the MCP tools for every
   operation they serve. A step moves to the customer's machine only when its request or response
   carries a secret (the operations listed under *Tools*), or when a tool the run needs is not
   served in this session. For that step, offer both forms side by side and let the customer
   choose: the [mc-cli](https://github.com/monte-carlo-data/mc-cli) command (`montecarlo`, the
   REST API v2 CLI) and the equivalent Terraform resource. Write a Python script over the SDK
   only when asked, and emit a whole Terraform artifact instead of acting when the customer asks
   for one or already manages this infrastructure with Terraform. **The customer runs the
   command, never you**, even when this session has a shell and the customer gave the file's
   path: running it puts the file within reach of your tools, and an error can print the secret
   into the transcript (rule 2). Ask only for the non-secret result, such as the credentials id.
   If the customer cannot run mc-cli or Terraform, say the step is completed in the UI, or
   recommend a collection agent with a self-hosted reference when its whole setup is served by
   tools (connection-inputs reference, support section). Setup and commands are in the
   output-modes reference, and every command handed over follows its rules for commands the
   customer runs: never one that reads a secret's value, short paste-safe lines, `${VAR}`
   braces, portable to macOS. Two cautions to pass on: the legacy `montecarlodata`
   Python CLI installs a command with the same name, so have the customer confirm with
   `montecarlo deployments --help` that the REST API CLI is the one on their path; and the
   profile is set by the customer with `montecarlo profile set … --api-token-prompt`, never by
   pasting a token here.
7. **Terraform takes secrets write-only.** In a Terraform artifact, pass every secret as the
   resource's write-only argument, `<name>_wo` with `<name>_wo_version = 1` (for example
   `private_key_wo` on `montecarlo_snowflake_credentials`), read from a file or an uncommitted
   variable, and set `required_version = ">= 1.11"`. Every Terraform artifact starts from the
   output-modes `terraform` block, including one with only AWS resources (a data store's bucket
   and role), so the version floors are the same everywhere. Tell the customer that changing a secret
   alone plans nothing, so they bump its version with it. Secrets Monte Carlo generates (a generic
   agent's token or OAuth client secret) are returned once and stay in that resource's state:
   hand them on write-only, for example to Secrets Manager with `secret_string_wo` as the
   output-modes reference shows, and never through an `output`, which state stores too. Either
   way, recommend a state backend that encrypts state and limits who can read it.
8. **Every required input comes from the customer or discovery.** Before the first write, in any
   output mode, build the inputs checklist for the chosen deployment, credential path and
   connection type from the connection-inputs reference, show it in the plan with each value's
   source, and ask for everything missing. **Never give a credential field a default value**
   (account, user, warehouse, host, key path, secret reference), in any output mode: no Terraform
   `default`, no script fallback, no filled-in CLI placeholder. A missing value fails at once
   and names the field; a defaulted one creates the credentials and connection, then fails
   validation with an error that doesn't say which value was wrong (a wrong Snowflake user shows
   as `JWT token is invalid`). Example values in these references are not defaults either.

## Tools

| Step | Tools |
|---|---|
| Deployment | `list_deployments`, `get_deployment`, `create_deployment`, `update_deployment`, `delete_deployment` |
| Agent | `list_collection_agents`, `register_aws_collection_agent`, `register_generic_collection_agent`, `get_aws_collection_agent`, `get_gcp_collection_agent`, `get_azure_collection_agent`, `get_generic_collection_agent`, `update_aws_collection_agent`, `update_generic_collection_agent`, `delete_aws_collection_agent`, `delete_gcp_collection_agent`, `delete_azure_collection_agent`, `delete_generic_collection_agent`, `delete_generic_collection_agent_token`, `delete_generic_collection_agent_oauth_client` |
| Data store | `list_collection_data_stores`, `register_aws_collection_data_store`, `get_aws_collection_data_store`, `get_gcp_collection_data_store`, `get_azure_collection_data_store`, `update_aws_collection_data_store`, `delete_aws_collection_data_store`, `delete_gcp_collection_data_store`, `delete_azure_collection_data_store` |
| Credentials | `list_credentials`, `create_aws_secrets_manager_credentials`, `create_gcp_secret_manager_credentials`, `create_azure_key_vault_credentials`, `create_env_var_credentials`, `create_file_credentials`, `get_<type>_credentials` for each managed type served (for example `get_snowflake_credentials`), `update_aws_secrets_manager_credentials`, `update_gcp_secret_manager_credentials`, `update_azure_key_vault_credentials`, `update_env_var_credentials`, `update_file_credentials`, `delete_<type>_credentials` for each managed type served (for example `delete_snowflake_credentials`), `delete_aws_secrets_manager_credentials`, `delete_gcp_secret_manager_credentials`, `delete_azure_key_vault_credentials`, `delete_env_var_credentials`, `delete_file_credentials`, `validate_aws_secrets_manager_credentials`, `validate_gcp_secret_manager_credentials`, `validate_azure_key_vault_credentials`, `validate_env_var_credentials`, `validate_file_credentials` |
| Warehouse | `list_warehouses`, `get_warehouse`, `create_warehouse`, `update_warehouse`, `delete_warehouse` |
| BI container | `list_bi_containers`, `get_bi_container`, `create_bi_container`, `update_bi_container`, `delete_bi_container` |
| ETL container (custom ETL connectors) | `list_etl_containers`, `get_etl_container`, `create_etl_container`, `delete_etl_container` |
| Connection types | `list_connection_types`, `list_custom_connector_types`, `get_custom_connector_type` |
| Connection | `list_connections`, `get_connection`, `create_connection`, `update_connection`, `delete_connection` |
| Identity | `get_current_user` (which account you are in, and whether it is paused) |
| Validation | `validate_connection`, `get_validation_run` (Steps 2 and 5) |

By design, no MCP tool accepts or returns a secret (rule 2). Operations whose request or response
carries one are **not MCP tools** and are handed to the customer as a CLI or Terraform step, which
reads the secret from a file on their machine and sends it to Monte Carlo directly:
`create_<type>_credentials`, `update_<type>_credentials` and `validate_<type>_credentials` for
every Monte Carlo-managed type (the Snowflake key pair, and the Tableau, Looker, Looker git clone
and Power BI credentials, among them), the Azure and GCP agent and
data-store registrations, `create_generic_collection_agent_token` and
`create_generic_collection_agent_oauth_client`. The reference files mark them.

Check which v2 tools are actually available before promising an automated run. Missing tools,
read-only mode and a missing `mcp/edit` scope are different conditions. Use the equivalent mc-cli
command (rule 6), or the SDK or Terraform equivalent, from the output-modes reference when needed;
request only its non-secret result/IDs and reconcile them before continuing. If neither the tool nor a usable
local-client path is available, explain the pending step and who can complete it. A reference
entry or an open implementation PR is not evidence that a tool is deployed in this session.

## Step 0: Discover, show what exists, ask what to connect

Invoking this workflow sets the scene for the rest of the conversation: discover the account,
show the customer what they already have and what can be added, then let them lead. The rules
above and the steps below keep applying to every later turn, however the customer phrases it.

**0a. Discover.** Read before asking anything:

- `get_current_user`: identify the account; stop if `account_frozen`. Confirm account ambiguity.
- `list_deployments`, `list_collection_agents`, `list_collection_data_stores`, `list_warehouses`,
  `list_bi_containers` (when served) and `list_connections`. When the account has custom
  connectors or the customer names one, also `list_custom_connector_types` and
  `list_etl_containers`. Follow `next_cursor` while
  `has_more` on every paginated list, including credentials later. Read agent/store details only
  when a choice depends on them.

**0b. Show.** Present a short inventory in customer language: each deployment with its type,
platform and `enabled`, the agent or data store behind it, and the existing warehouses and BI
containers with their connections. An empty account is an answer too; say so. Follow it with what
can be added, from this session's tools, as the support section of the connection-inputs reference
describes: which integrations can be connected, and with which credential options. Keep both to a
few lines; do not dump raw ids unless asked.

**0c. Ask what to connect, then follow the customer.** If the request already names the
integrations ("connect Snowflake and Postgres"), skip the question. Otherwise ask one open
question, such as "What would you like to connect?", and stop. Do not open with deployment or
credential questions; they come after the target is known.

Several integrations can be onboarded in one run. For each one requested:

- **Check support first**, from the tool schemas in this session as the connection-inputs
  support section describes, before
  any other question about it. When the integration cannot be connected through these tools on
  any deployment, or only through the UI on the one the customer wants, say so now and offer the
  UI handoff or a route that is supported; do not provision anything for it. When
  `list_connection_types` marks the type `is_custom`, or the customer names their own connector,
  follow *Custom connectors* instead of Steps 1 to 5.
- **Resolve the route** (Step 1): reuse a compatible deployment from the inventory where one fits.
  Integrations that fit the same deployment share it; do not create one per integration.
- **Credentials, warehouse or BI container, connection, validation** (Steps 2 to 5) run per
  integration. The
  inputs checklist (rule 8) covers every integration in the plan, and missing values for all of
  them are asked in one message.

Also in discovery:

- Infer the integration's cloud and region from reliable existing information; otherwise ask
  only when needed to choose or configure the route. Do not infer an agent's cloud from the
  product name (Snowflake runs on multiple clouds), or assume its region from an example.
- For a request to connect now, guide the run through available tools and local handoffs.
  Honor a requested Terraform or SDK/CLI artifact; offer those modes when useful instead of
  making every new customer choose an implementation technology. Discovery and reuse apply in
  all modes, via MCP or the v2 CLI/SDK fallback above.

Before provisioning, check the chosen path's requirements in the deployment guide: Account
Owner permissions, subscription/add-ons, supported platform/region and an administrator who
can deploy cloud resources. `get_current_user` does not prove subscription eligibility. If a
requirement cannot be read, ask only for that missing fact or hand off to the account owner.

The customer runs the connector's service-user/grants setup (for example,
https://docs.getmontecarlo.com/docs/snowflake). Identify the intended account and databases;
reuse existing setup where appropriate. Guide the required steps without requesting secrets. For
a BI tool, that setup is the user, token, API client or app registration Monte Carlo signs in
with, from the tool's page in the Monte Carlo docs (for example
https://docs.getmontecarlo.com/docs/tableau or https://docs.getmontecarlo.com/docs/looker).

## Step 1: Resolve the deployment

Use the product's deployment names from
https://docs.getmontecarlo.com/docs/deployment-and-connecting:

- **Cloud Deployment**: Monte Carlo hosts collection and the data store.
- **Cloud with Customer-hosted Data Store Deployment**: Monte Carlo hosts collection; the
  customer hosts object storage for samples and temporary results. It does not give collection
  access to a private warehouse network; direct integration connectivity is still required.
- **Customer-hosted Agent & Data Store Deployment**: collection originates in the customer's
  environment and uses their storage. Cloud-native agents and the Generic Agent have different
  connectivity requirements; select the family only after determining that an agent is needed.

Storage placement concerns samples and temporary query results. Metadata, metrics, query logs
and aggregated statistics still reside in Monte Carlo. If the requirement is that no data may
leave the company, clarify compatibility before proceeding; do not promise that an agent meets it.

Resolve these independent requirements from discovery and stated policy. Ask only what remains
unknown and can change the recommendation, in customer language:

| Decision | What it determines |
|---|---|
| Must connections originate from the customer's network, or does the customer prefer that control? | Use an agent, even if direct Cloud connectivity is technically possible. |
| Must integration credentials remain self-hosted? | Use an agent. Resolve this before committing to a deployment, not after it. |
| May Monte Carlo connect directly, using an authorized public route or supported private connectivity? | Cloud is possible if neither of the requirements above requires an agent. Check the exact integration/cloud/region and PrivateLink prerequisites. "No public internet" alone does not imply an agent. |
| Must samples and temporary results stay in customer storage? | Use a customer-hosted data store with Cloud, or the agent's customer-hosted storage when an agent is already needed. Do not ask again to choose a separate datastore deployment for an agent. |

For example: "Do connections need to come from your company's network?" and "Must credentials
stay in your secret store?" are policy questions; "Which deployment type do you want?" assumes
product knowledge. Skip answered questions and explain the recommended route in one sentence.

Cloud + PrivateLink and agent + PrivateLink to the integration are both valid where supported.
Do not override the customer's origin policy. PrivateLink support is not universal: consult the
deployment guide for the selected integration, cloud, region and authentication method, and wait
for required endpoint approvals before connection registration.

### 1a. Reuse or resume

| Observed state | Action |
|---|---|
| `type: CLOUD`, `enabled: true` | Reuse if origin, credentials, connectivity and storage requirements allow Cloud. |
| Enabled `COLLECTION_AGENT` or `COLLECTION_DATA_STORE` | Check platform, network reach, secret access and storage policy for the target, then reuse. `enabled` alone does not prove reachability to a new warehouse. |
| Typed, disabled deployment with an identifiable agent/store in progress | Inspect its details and resume that registration when it belongs to this onboarding. |
| Null type, unknown platform, disabled Cloud, or an expected deployment missing from the list | Do not use it or conclude that the customer must install an agent. v2 excludes older deployments. Resolve in the UI or with support; do not mix IDs from other APIs. |

Choose one compatible `deployment_id`, explaining why. If several fit, use the target environment
and policy to narrow them; ask only for an unresolved choice. Never retire a working deployment
or start a migration merely to make the new connection fit.

### 1b. Provision a deployment for a collection agent

1. Use the deployment guide to choose a cloud-native agent (`AWS`, `AZURE`, `GCP`) or the
   `GENERIC` family. Classic agents need a route from Monte Carlo to the agent and a separate
   route from the agent to the integration. Generic initiates connections to Monte Carlo and
   needs no inbound ports. Infer the hosting cloud/runtime first; ask about ingress restrictions
   only if they remain unknown. Prefer native when it meets the requirements; Generic supports
   Docker Compose and Kubernetes, is in preview, and needs Enterprise + Advanced Networking.
2. `create_deployment(type="COLLECTION_AGENT", runtime_platform=<platform>, name=<optional>)`.
   Note the returned `id`. On AWS, `get_deployment` returns `aws_external_id` (it can be null for
   a moment right after creation; retry the read briefly, then check permission/status if still null).
3. **Hand over the deploy step.** The customer runs it where their cloud credentials are; keep secrets outside this
   session. Per platform, from the output-modes reference:
   - AWS: Terraform module `monte-carlo-data/mcd-agent/aws` with the account
     information page's **Collection AWS account ID** (never the account the agent is deployed
     into), chosen region and generated `external_id`, or the CloudFormation template with a
     parameters file (output-modes; parameter names from the template itself). Outputs: Lambda
     function ARN, invoker role ARN.
   - GCP: module `monte-carlo-data/mcd-agent/google`. Outputs: Cloud Run URL, invoker key.
   - Azure: module `monte-carlo-data/mcd-agent/azurerm`. Outputs: function app URL, auth details.
   - Generic: first a credential for the agent — `montecarlo collection-agents create generic-token
     --deployment-id <id>` or the `montecarlo_generic_collection_agent_token` resource; the secret
     is printed once, to the customer, never to this chat — then run the agent (the
     selected Kubernetes module or Docker Compose guide) with it. Choose token or OAuth before
     registration, and configure the backend endpoint, object storage, integration secrets and
     outbound access. Storage is not automatically supplied by a bare container.
4. **Register.** Ask for the outputs (ARNs and URLs are not secrets) and call:
   - AWS: `register_aws_collection_agent(deployment_id, lambda_function_arn, role_arn, name)`.
   - Generic: `register_generic_collection_agent(deployment_id, name)`. If registration reports that the agent
     is not connected, check its outbound path and authentication, then retry after it connects.
     Do not diagnose every 503 as that condition; use the error code when available.
   - GCP and Azure: the registration carries the agent's credentials, so it is not an MCP tool.
     Emit `montecarlo collection-agents register gcp|azure …` or the
     `montecarlo_gcp_collection_agent` / `montecarlo_azure_collection_agent` resource and wait
     for the user to confirm it ran; then `list_collection_agents` to read the agent id.
5. `get_deployment` should now show `enabled: true`. If not, the registration failed its check;
   the error names the cause, fix it and register again (safe to repeat with the same values).

### 1c. Provision a deployment for a data store

1. Use the selected customer storage cloud (`AWS`, `GCP` or `AZURE`) and region; ask only if unknown.
2. `create_deployment(type="COLLECTION_DATA_STORE", runtime_platform=<platform>)`; on AWS read
   `aws_external_id` with `get_deployment`.
3. **Hand over the storage step** from the cloud-specific deployment guide: private object
   storage and its access identity. AWS uses an assumable role trusting the generated External ID;
   Azure/GCP use their own credential/permission models. Use the output-modes reference for AWS
   Terraform and the official guides for complete Azure/GCP resource setup.
4. **Register**: AWS → `register_aws_collection_data_store(deployment_id, bucket_name, role_arn,
   name)`. GCP and Azure carry credentials → emit the CLI or Terraform step, then
   `list_collection_data_stores`.
5. Confirm `enabled: true` on the deployment.

Whatever the branch, carry one `deployment_id` into Step 2.

## Step 2: Credentials

`list_credentials` first (paginate). Match the target account/host and intended identity, not
just `connection_type`. Use the appropriate non-secret getter to inspect the secret reference,
region and assumed role, or ask for a known credentials ID. Do not read secret contents to make
this choice; if identity remains ambiguous, ask. Record reused IDs as well as created ones.

Before asking anything about credentials, and unless the run already covered it (rule 2), tell
the user how they are handled in one or two sentences of your own. For example: "Monte Carlo never passes a credential through this chat or
through a tool: anything a tool receives or returns is visible to the model. So I will either
reference a secret you keep in your own secret store, or give you a command to run on your
machine that sends it to Monte Carlo directly." Then ask only for the reference or the non-secret
details.

Otherwise the deployment from Step 1 decides what is possible:

- **Collection agent** → credentials can stay in the customer's store (self-hosted, below). The
  agent reads the secret at query time, so its role or identity needs read access to that secret.
- **Hosted cloud node or data-store deployment** → nothing on the customer's side can be read, so
  the credentials are Monte Carlo managed. Through the v2 API that is a managed type, discovered
  as the connection-inputs support section describes (CLI or Terraform step, last row below). A
  type that is not managed is onboarded in the UI on these deployments. Hand off with the selected deployment and any existing IDs; do not
  create an empty warehouse until its reuse in that UI flow is established.

Use the credential policy already resolved in Step 1; ask only for the missing reference or
authentication details. Those details are the connection type's rows in the connection-inputs
reference (rule 8): for managed credentials, the create operation's non-secret fields and the
secret file's path (only for the customer's command; never open it, rule 2), as in the Snowflake
key-pair example; for
a self-hosted reference, the store's fields plus the customer's confirmation that the secret
carries the type's required keys. If the policy changes, revisit the deployment choice before
writing:

| Where | Tool | Notes |
|---|---|---|
| AWS Secrets Manager | `create_aws_secrets_manager_credentials(connection_type, aws_secret, aws_region?, assumable_role?, external_id?)` | Direct access: the agent execution identity needs `secretsmanager:GetSecretValue`. With `assumable_role`, the target role needs secret access and a trust policy for the caller, and the caller needs `sts:AssumeRole`; honor its External ID condition. See output-modes. |
| GCP Secret Manager | `create_gcp_secret_manager_credentials(connection_type, gcp_secret)` | Same idea: the agent's service account must read it. |
| Azure Key Vault | `create_azure_key_vault_credentials(connection_type, akv_secret, akv_vault_name and/or akv_vault_url)` | |
| Environment variable on the agent | `create_env_var_credentials(connection_type, env_var_name (MCD_…), kms_key_id?)` | Only with a collection agent the customer runs; the cloud node has no customer-set variables. |
| File on the agent | `create_file_credentials(connection_type, file_path)` | Generic Kubernetes/Docker: mount the JSON file into the agent; use its container path. A path on the customer's machine (`~/Downloads/key.p8`) is not a file credential: it goes into the CLI or Terraform step. |
| Monte Carlo stores it (a managed type) | **not a tool** | Offer both (rule 6): `montecarlo credentials create <type> …` with each secret field as `@<path>` or `--<field>-prompt`, never a literal; or the `montecarlo_<type>_credentials` resource with the secret in `<field>_wo` (rule 7). For a Snowflake key pair: `montecarlo credentials create snowflake --account … --user … --warehouse … --private-key @key.p8`. The user runs it and gives back the `id`. |

**Grant, then validate, then create.** A self-hosted reference only validates once the agent
can read the secret, so hand over that grant first: read that section and hand over its commands
(output-modes: grant the agent read access), with its policy-list check and a simulator check, and
ask the customer to confirm it is applied; validating before the grant exists only fails.

**Validate before creating.** Each self-hosted create has a matching validate that takes the same
arguments plus `deployment_id`: `validate_aws_secrets_manager_credentials`, `validate_gcp_secret_manager_credentials`, `validate_azure_key_vault_credentials`, `validate_env_var_credentials`, `validate_file_credentials`. It creates nothing and
returns a run: read it with `get_validation_run` as in Step 5, and create only when every validation
has `passed: true`. If any has `passed: false`, relay its errors' `friendly_message` and
`resolution` and stop before creating anything. A failure here is almost always the agent's access
to the secret (IAM grant, trust policy, service-account role, Key Vault policy), and it is cheapest
to fix now, before a warehouse or connection exists. For managed credentials, emit the validate
step beside the create step, with the same fields plus `--deployment-id`: for a Snowflake key pair,
`montecarlo credentials validate snowflake --deployment-id … --account … --user … --private-key @key.p8`
(not an MCP tool: the secret travels in the request). When the session does not serve these tools,
skip this check; Step 5 still validates the connection.

Two Snowflake key formats belong to different paths; do not interchange them:

- **Self-hosted secret contents**, following https://docs.getmontecarlo.com/docs/self-hosted-credentials:
  JSON `connect_args` with `user`, `account`, optional `warehouse`, and `private_key` as the
  decrypted PKCS#8 base64 body (no PEM BEGIN/END lines). The customer prepares this locally.
- **Monte Carlo-managed v2 Snowflake credentials**: the CLI/provider reads the full PEM text,
  including BEGIN/END lines, with a passphrase if encrypted. The output-modes reference shows
  this request, not the contents of a self-hosted secret.

Describe schemas without asking for values. For other types follow their self-hosted schema;
add `bq_project_id` / `databricks_warehouse_id` where the v2 credential operation requires them.
Password or external OAuth Snowflake setup is a UI handoff. Carry the `credentials_id` forward.

**BI tools.** Tableau, Looker, Looker git clone and Power BI credentials are managed types
(`tableau`, `looker`, `looker-git-clone`, `power-bi`), created and validated by the customer's
CLI or Terraform step like the Snowflake key pair: `montecarlo credentials validate <type>
--deployment-id …`, then `montecarlo credentials create <type> …`. Each type has its own inputs
and sign-in methods; take them from the connection-inputs BI section. A collection agent can also
read a self-hosted reference with `connection_type` set to one of these types, holding the keys
that section's self-hosted table lists. A Looker instance takes the API client (`looker`) and,
when the customer wants it, the LookML repository (`looker-git-clone`): two credentials, two
connections, one container.

## Step 3: The warehouse, or the BI container

For a Tableau, Looker or Power BI connection, skip to *3b*. Every other connection goes on a
warehouse.

### 3a. The warehouse

Use the warehouses discovered in Step 0. Match the intended account/host and environment as
well as type and deployment; different Snowflake accounts on one deployment are not automatically
one warehouse. Prefer a verified prior `warehouse_id`; otherwise inspect its connections and
confirm any ambiguity. Do not take the first warehouse with a matching type.

**Warn before duplicating collection.** Once the target account/host is known, check the
discovered connections for the same one (the same Snowflake account, database host, project or
workspace; the same self-hosted secret; or managed credentials with the same account and user),
on any deployment. If one exists, say so before creating anything: a second connection collects
the same metadata and query logs twice. Offer to reuse it, or, when the customer is moving the
connection (to a new agent, to Terraform, to a data store), note that the old connection should be
removed once the new one has collected, and name it. Removing it follows the rule below on how an
existing resource was created.

If none represents the target, `create_warehouse(name, deployment_id, type=<warehouse type>)` or
`create_warehouse(name, deployment_id, connection_type=<connection type>)`. Send exactly one of
`type` / `connection_type`; names are unique per type. For a connection type that is not itself a
warehouse type, send `connection_type`: a refusal means the API cannot map it, nothing was
created, and the integration is handed off to the UI (connection-inputs support section). Carry and record the `warehouse_id`.

### 3b. The BI container

Use the BI containers discovered in Step 0. Match the tool and the instance (the same Tableau
server and site, Looker instance or Power BI tenant), as well as the deployment; inspect a
container's connections and their credentials' non-secret fields when its name alone does not say.
The duplicate warning above applies here too: a second container for an instance already
connected collects its reports twice.

If none represents the target, `create_bi_container(type, name, deployment_id)` with `type`
`tableau`, `looker` or `power-bi`. Create one per instance: one `looker` container holds both the
Looker API and the LookML repository connection, so never create a second one for the repository.
NEVER create a warehouse for a BI tool: `create_warehouse` has no BI type, and a warehouse refuses
BI credentials. Carry and record the `bi_container_id`.

## Step 4: The connection

`list_connections(warehouse_id)` or `list_connections(bi_container_id)` first (paginate). Reuse a
connection for the same target and credential identity; inspect the existing non-secret
credential details if the IDs differ. A matching name alone is not proof. A name collision with a
different target needs resolution, not another blind create. Preserve existing jobs and record its
ID when reusing.

Otherwise `create_connection(name, warehouse_id, credentials_id)`, or for a BI tool
`create_connection(name, bi_container_id, credentials_id)`. Send exactly one of `warehouse_id` and
`bi_container_id`. The type comes from the credentials and must fit the parent: the warehouse
type, or the container type (`looker` and `looker-git-clone` credentials both fit a `looker`
container). Omit `job_types` for defaults; Power BI dataflows are not added through this API.
Verify the returned parent/deployment association and record `id`, `connection_type`,
`deployment_id`, `job_types`.

## Step 5: Validate

Run this for every connection created or reused in this run:

1. `validate_connection(connection_id)` starts a run and returns at once. Its response is the run
   itself, still in progress; keep its `id`.
2. `get_validation_run(run_id=<id>)` reads the run. Read it again until its `status` is `completed`.
   A run usually takes from a few seconds to a few minutes. Read it again directly; if the
   environment needs a pause, keep it to about 3 seconds, never a longer or repeated shell
   `sleep`. If it is still running after
   about 5 minutes, stop and report it as still running with its `id`, which can be read again until its
   `expires_at`.

Judge each validation by `passed` only, never by its `status`. `status` only says whether the check
ran: a validation can be `completed` and still have failed. The connection works when every
validation has `passed: true`; it does not when any has `passed: false`.

- **Every validation passed**: the connection works. `warnings` are non-blocking; list them.
  Collection starts on its own, and the first metadata appears within about an hour.
- **Any validation did not pass**: for each one, give its `name`, then its errors'
  `friendly_message` and `resolution` verbatim. A `skipped` validation waited on a prerequisite that
  did not pass; fix that one first. The usual causes, in order: a credential input is wrong (a
  Snowflake `JWT token is invalid` means the user is not the one the key is set on; "No active
  warehouse selected" means the warehouse is missing or not granted), so re-check the
  connection-inputs checklist; the agent cannot read the secret (IAM
  grant, service-account role or Key Vault policy missing); the warehouse user lacks the grants in
  the connector's docs page; the network path is missing (Monte Carlo's IPs not allowlisted for the
  cloud node, or the agent's VPC has no route to the warehouse). After the fix, call
  `validate_connection` again; a new run is needed, and the connection itself does not change.
- **Validate call refused as rate limited**: the account already has the maximum of 10 validation runs in
  progress. Do not start more. Finish reading the runs this session started, then try again a
  minute later.

Do **not** substitute any other tool for validation. If the session does not serve
`validate_connection` and `get_validation_run`, end with:

> Validate the connection in the Monte Carlo UI: Settings → Integrations → the integration → the
> new connection → **Test**. Until the test and initial collection are confirmed, report
> **connection created, validation pending**, not a completed onboarding.

## Custom connectors

A custom connector is a connection type the customer's collection agent registered with Monte
Carlo, or a connector whose data the customer pushes. Discovery, the plan, the credential rules and
the summary are the same as for any integration; what changes is that the **type decides the
parent and the deployment**, so there is no deployment to choose.

### Find the type

`list_custom_connector_types` lists the types the account's agents registered; pass `asset_class`
(`etl`, `bi` or `warehouse`) to narrow it. Each item gives the `id` (the connection type, for
example `custom-etl-connector-<id>`), the agent-supplied `name`, the `asset_class`, the
`collection_agent_id` that registered it and that agent's `deployment_id`. Match what the customer
names against `name`; it is not validated, so confirm when two types could fit. Read one type with
`get_custom_connector_type`.

There are two kinds, and they take different steps:

- **Agent-registered**: the type is listed. Its connection runs through the registering agent's
  deployment, with self-hosted credentials that agent reads.
- **Push-only**: the customer sends the data to Monte Carlo themselves (ETL jobs and runs, or BI
  assets), and no agent reaches anything. Nothing is listed for it. Its container is created with
  no deployment, and its connection takes no credentials.

When the customer's words leave the kind open, ask one question, such as "Does a Monte Carlo agent
run this connector, or will you push its data to Monte Carlo yourselves?" A type whose agent was
removed is not listed; when the customer expects one that is missing, check
`list_collection_agents` with them before going further.

### The parent and its deployment

| `asset_class` | Parent | Deployment |
|---|---|---|
| `etl` | `create_etl_container(type="custom-etl-connector", name, deployment_id)` | Agent-registered: the type's `deployment_id`. Push-only: none. |
| `bi` | `create_bi_container(type="custom-bi-connector", name, deployment_id)` | Agent-registered: the type's `deployment_id`. Push-only: none. |
| `warehouse` | Not served yet (below). | |

<!-- placeholder(YET-3103): custom warehouse connectors. Replace this paragraph with the
create_warehouse step for a custom-connector-<id> type once YET-3103 phase 2 ships it. -->
A custom **warehouse** connector cannot be connected through these tools yet. Say so, create
nothing for it, and hand it off to the Monte Carlo app (Settings → Integrations).

Step 1 does not apply: never create or provision a deployment for a custom connector. Check that
the type's `deployment_id` is in `list_deployments` and `enabled`; if it is missing or disabled,
the agent behind it is the problem, so stop and resolve it with the customer (Step 1a). Reuse a
container of the same type on that deployment, or with no deployment for push-only, that has no
connection yet; an ETL container holds one connection. Otherwise create one and record its id.

### Credentials (agent-registered only)

The agent that registered the type reads the secret, so the credentials are a self-hosted
reference (Step 2) with `connection_type` set to the type's `id`, in a store that agent can read:
`list_connection_types` lists the stores for the type in `self_hosted_credentials_storages`. An
environment variable name must start with `MCD_`. The keys inside the secret are whatever the
customer's connector reads; this skill does not know them, so ask the customer to confirm the
secret carries them, without seeing it. Validate before creating, as in Step 2, with
`deployment_id` set to the type's deployment: any other deployment is refused.

A push-only connector takes no credentials. Do not create any for it.

### Connection and validation

- **Agent-registered**: `create_connection(name, etl_container_id|bi_container_id,
  credentials_id)`, then Step 5.
- **Push-only**: `create_connection(name, etl_container_id|bi_container_id)` with no
  `credentials_id`; the connection takes the container's type. There is nothing for Monte Carlo to
  validate, because no agent reaches anything: skip Step 5 and do not call `validate_connection`.
  The connection is ready to receive what the customer pushes.

<!-- placeholder(YET-3141): push-only ingestion key. Replace this paragraph with the step that
mints the key for the push-only container once YET-3141 ships it. -->
The key the customer pushes with is not created by these tools yet. Say so, list it under
*Pending on your side* in the summary, and point the customer to the push-ingestion workflow for
the key and the push itself.

### Refusals, in the customer's words

A refusal creates nothing. Relay the meaning, then the fix:

- **`custom_connector_has_no_agent`**: the agent that registered this connector is no longer
  registered with Monte Carlo, so nothing could run it. Check `list_collection_agents` with the
  customer; the connector can be connected once its agent is running and registered again.
- **`custom_connector_deployment_mismatch`**: the container, or the deployment given to a
  credentials validation, is not the one the connector's agent runs on. The message names the
  right deployment. Use a container on that deployment; never move the agent to fit. An empty
  container this run created on the wrong deployment is removed with `delete_etl_container` or
  `delete_bi_container`.
- **An argument error on `credentials_id`**: credentials were sent to a push-only container, or
  left out on an agent's container, or their type does not fit the container. Recheck the kind
  (agent-registered or push-only) and the type's `asset_class` against the container.
- **The caller is not allowed** (and the account is not paused): custom connectors may not be
  enabled for the account. Hand off to the Monte Carlo account team; do not retry.

## Step 6: Summary (always)

Finish every run, including an aborted one, with the block below. With several integrations,
repeat the credentials, warehouse, connection and validation lines under a heading per
integration, and list any integration that was not supported, with its handoff, under *Pending
on your side*.

```
Account: <account_name> (<account_id>)
Output mode: act now | mc-cli | terraform | script

Created in this run
  deployment    <id>  <name>  <type>/<runtime_platform>  enabled=<bool>
  agent|store   <id>  (or: registration step handed over, pending)
  credentials   <id>  <connection_type>  <storage_type>  (or: CLI/Terraform step handed over)
  warehouse     <id>  <name>  <type>  (or: bi container | etl container  <id>  <name>  <type>  deployment=<id or none>)
  connection    <id>  <name>  <connection_type>  job_types=<…>
  validation    <run id>  passed | failed | running  <validations_passed>/<validations_total> passed  (or: not available in this session; or: none, push-only)

Reused (excluded from cleanup)
  deployment / agent|store / credentials / warehouse|bi container|etl container / connection  <ids and names>

Pending on your side
  - <deploy/register/credential step still to run, with the exact command or file>
  - Validation still running: read it again with get_validation_run(run_id=<run id>) before its expires_at; do not start a new one
  - Validation failed: fix what it reported, then re-run Step 5 (a new validate_connection)
  - Validation tools not available in this session: test in the UI under Settings → Integrations → <integration> → <connection name> → Test
  - Push-only custom connector: the key to push with, then the push itself (push-ingestion)

Cleanup if you abandon this: delete_connection → delete_warehouse|delete_bi_container|delete_etl_container → delete_<kind>_credentials →
delete_<platform>_collection_agent|data_store → delete_deployment, in that order. On the generic
agent path, also delete the token or OAuth client this run minted (delete_generic_collection_agent_token /
delete_generic_collection_agent_oauth_client).
```

In artifact mode label resources as **planned**, not created. Record IDs only after execution.
On a handoff or failure, give the last completed stage, non-secret IDs and the exact next step;
show validation only when a connection exists. Cleanup applies only to resources created by this
run, after checking shared dependencies.

**Ask how an existing resource was created before deleting it.** Monte Carlo doesn't record whether
Terraform, the CLI, the UI or an earlier run created a deployment, agent, credentials, warehouse
or connection, so for anything this run didn't create, ask before offering a delete tool. If the
customer isn't sure, hand over the output-modes check for each Terraform directory that uses the
provider. A Terraform-managed resource is removed by Terraform (the output-modes steps for removing
what Terraform manages): deleting it here leaves the state pointing at nothing, and the next apply
creates it again. Offer the delete tools only for the rest, after confirmation. Deregistration does not delete cloud infrastructure or
storage contents; coordinate removal of deployments with jobs/history rather than forcing it.
When the customer removes an agent's cloud side, hand over the output-modes steps for removing an
agent: its versioned bucket must be emptied, including old versions, before `terraform destroy`
or `delete-stack` can remove it.

## Error handling

- Tool errors arrive as `"<operation> failed: <detail>"` with field-level messages and a request
  id when exposed. Some server errors are masked; do not invent their cause. Fix actionable
  input errors; bound transient retries and reconcile state after uncertain results. Include an available request id
  when a call failed for a reason you could not fix.
- `create_deployment` refused with an account limit reached: the per-account deployment cap is
  raised by Monte Carlo support; do not delete a working deployment to make room.
- A conflict on `create_*` usually means the name exists (warehouse names are unique per type,
  connection names per warehouse or BI container) or the deployment cannot take that resource.
  `list_*` and reuse. `delete_bi_container` is refused while connections remain on it.
- `register_*` that fails its check registers nothing; the same call can be repeated after the fix.
- `delete_deployment` is refused while anything is registered or connected through it: the
  cleanup order in the summary is the order that works.
- Never retry a `create_*` blindly: `list_*` first to see whether it went through.

## Worked example: "Connect our Snowflake account"

1. Discover account, capabilities, deployments and connections. Infer Snowflake's cloud/region
   where possible. Reuse a verified existing connection instead of creating one.
2. Resolve missing policy only: if credentials must remain in Secrets Manager or connections
   must originate in the customer's VPC, recommend an agent. A public-internet restriction alone
   leaves Cloud + supported PrivateLink as an option; respect a preference for agent + PrivateLink.
3. If an AWS native agent fits and none can be reused, approve the concrete plan, provision the
   deployment, and hand over the module with the Collection AWS account ID and External ID.
   Stop until infrastructure exists, then register and confirm enabled. Use Generic only when
   its outbound architecture/runtime fits the requirements; follow its separate guide.
4. Reuse or create the correct Snowflake credential reference, warehouse and connection; verify
   their association. Hand off the UI test and report created/reused IDs and remaining work.

## Worked example: "Connect our Tableau Server"

1. Discover, including `list_bi_containers`. Reuse a container already connected to the same
   server and site; say so instead of creating a second one.
2. Resolve the deployment as in Step 1. The Cloud Deployment reaches Tableau Cloud and a public
   Tableau Server; a server reachable only inside the customer's network takes one of the
   private routes Step 1 describes.
3. Build the Tableau checklist (connection-inputs): the server URL, the site, and exactly one
   sign-in method. Approve the plan.
4. `create_bi_container(type="tableau", name, deployment_id)`. Hand over the credentials step:
   `montecarlo credentials validate tableau --deployment-id …`, then `montecarlo credentials
   create tableau …` with the secret as `--password-prompt` or `@<path>`, or the
   `montecarlo_tableau_credentials` resource with `password_wo`. Ask only for the returned `id`.
5. `create_connection(name, bi_container_id, credentials_id)`, then validate (Step 5).

## Worked example: "Connect our custom ETL connector"

1. Discover, including `list_custom_connector_types(asset_class="etl")`, `list_etl_containers`
   and `list_connections`. The customer's "orders scheduler" matches one listed type by `name`;
   note its `id`, `collection_agent_id` and `deployment_id`, and check that deployment is enabled.
2. Plan: a `custom-etl-connector` container on the type's deployment (or reuse an empty one
   there), a self-hosted reference with `connection_type` set to the type's `id` in a store the
   agent reads (an environment variable such as `MCD_ORDERS_SCHEDULER` on the agent, for
   example, which the customer names), the connection, then validation. Approve the plan.
3. Hand over the agent's read grant if the store needs one, then `validate_env_var_credentials`
   with the type's `deployment_id`, and create the credentials once it passes.
4. `create_etl_container(type="custom-etl-connector", name, deployment_id)`, then
   `create_connection(name, etl_container_id, credentials_id)`, then validate (Step 5).
5. Had the customer said they push the jobs and runs themselves, the container would take no
   deployment, the connection no credentials, and there would be no validation; the push key
   stays pending on their side.
