---
name: monte-carlo-onboarding
description: Connect a warehouse to Monte Carlo using API v2 tools. Discover or provision deployments, reference credentials, reuse or create the connection, and guide validation. Use when asked to connect a platform or onboard a warehouse.
metadata:
  bucket: Setup
---

# Monte Carlo Onboarding

Walk a customer from "connect `<warehouse>` to Monte Carlo" to a working connection, using the
Monte Carlo **REST API v2** MCP tools. Discover what already exists, resolve only the missing
customer decisions, and reuse or provision
the deployment before creating a connection. A request to connect Snowflake does not imply that
the customer knows which deployment or collection agent they need.

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

If a referenced resource is unavailable, identify what is missing and consult the linked official
documentation before proceeding. Do not guess a tool schema or provisioning parameter.

This workflow covers connecting supported data platforms and selecting deployments, agents,
data stores and credentials. For metadata or lineage without a connector use push-ingestion;
for Connection Auth Rules JSON use connection-auth-rules; for AI agent instrumentation use
instrument-agent; for an already-connected warehouse's monitoring use monitoring-advisor.


## Rules that hold for the whole run

1. **v2 tools only.** Use the tools listed under *Tools* below, and the tool schema or the per-tag
   API reference for any other v2 operation, and nothing else for reads or writes about deployments, agents, data
   stores, credentials, warehouses and connections. Other
   Monte Carlo tools that list warehouses, integrations or platform services, or that test an
   integration, are a different API with different ids and fields. Never mix them into this flow,
   even to "double-check".
2. **No secret ever travels through the chat or a tool argument.** Not a private key, password,
   service-account key, token, or passphrase. Credentials the customer hosts are *referenced*
   (secret name, ARN, vault, variable name, file path). Credentials Monte Carlo must hold (a
   Snowflake key pair, a generic agent token) are created by a CLI or Terraform step the customer
   runs on their own machine. If the user pastes a secret into the chat, stop, tell them it is now
   in the transcript and should be rotated, and continue with the reference or CLI path.
3. **Never create a deployment with nothing behind it.** A deployment exists to host a collection
   agent or a data store. It is provisioned only when one of those will be registered on it, in
   the same run or in a follow-up the user commits to.
4. **Confirm the concrete plan before writing.** Explain what will be reused or created and
   which steps the customer must run. Approval of the whole plan covers its writes; do not ask
   again for each call. Confirm a change of scope or a destructive action separately.
5. **Every run ends with the summary** in *Step 6*, whether it completed, stopped early, or hit an
   error. Ids created by this run are the customer's cleanup list.

## Tools

| Step | Tools (REST API v2) |
|---|---|
| Deployment | `list_deployments`, `get_deployment`, `create_deployment`, `update_deployment`, `delete_deployment` |
| Agent | `list_collection_agents`, `register_aws_collection_agent`, `register_generic_collection_agent`, `get_aws_collection_agent`, `get_gcp_collection_agent`, `get_azure_collection_agent`, `get_generic_collection_agent`, `update_aws_collection_agent`, `update_generic_collection_agent`, `delete_aws_collection_agent`, `delete_gcp_collection_agent`, `delete_azure_collection_agent`, `delete_generic_collection_agent`, `delete_generic_collection_agent_token`, `delete_generic_collection_agent_oauth_client` |
| Data store | `list_collection_data_stores`, `register_aws_collection_data_store`, `get_aws_collection_data_store`, `get_gcp_collection_data_store`, `get_azure_collection_data_store`, `update_aws_collection_data_store`, `delete_aws_collection_data_store`, `delete_gcp_collection_data_store`, `delete_azure_collection_data_store` |
| Credentials | `list_credentials`, `create_aws_secrets_manager_credentials`, `create_gcp_secret_manager_credentials`, `create_azure_key_vault_credentials`, `create_env_var_credentials`, `create_file_credentials`, `get_snowflake_credentials`, `update_aws_secrets_manager_credentials`, `update_gcp_secret_manager_credentials`, `update_azure_key_vault_credentials`, `update_env_var_credentials`, `update_file_credentials`, `delete_snowflake_credentials`, `delete_aws_secrets_manager_credentials`, `delete_gcp_secret_manager_credentials`, `delete_azure_key_vault_credentials`, `delete_env_var_credentials`, `delete_file_credentials`, `validate_aws_secrets_manager_credentials`, `validate_gcp_secret_manager_credentials`, `validate_azure_key_vault_credentials`, `validate_env_var_credentials`, `validate_file_credentials` |
| Warehouse | `list_warehouses`, `get_warehouse`, `create_warehouse`, `update_warehouse`, `delete_warehouse` |
| Connection | `list_connections`, `get_connection`, `create_connection`, `update_connection`, `delete_connection` |
| Identity | `get_current_user` (which account you are in, and whether it is paused) |
| Validation | `validate_connection`, `get_validation_run` (Step 5; when the session serves them) |

Operations whose request or response carries a secret are **not MCP tools** and are handed to the
customer as a CLI or Terraform step: `create_snowflake_credentials`, `validate_snowflake_credentials`, the Azure and GCP agent and
data-store registrations, `create_generic_collection_agent_token` and
`create_generic_collection_agent_oauth_client`. The reference files mark them.

Check which v2 tools are actually available before promising an automated run. Missing tools,
read-only mode and a missing `mcp/edit` scope are different conditions. Use the equivalent v2
CLI/SDK/Terraform operation from the output-modes reference when needed; request only its
non-secret result/IDs and reconcile them before continuing. If neither the tool nor a usable
local-client path is available, explain the pending step and who can complete it. A reference
entry or an open implementation PR is not evidence that a tool is deployed in this session.

## Step 0: Discover and frame the run

Start from the user's intent, such as "connect Snowflake". Use the request and available reads
before asking questions:

- `get_current_user`: identify the account; stop if `account_frozen`. Confirm account ambiguity.
- `list_deployments` before provisioning; also inspect `list_warehouses` and `list_connections`
  for the target account/host and environment. Follow `next_cursor` while `has_more` on paginated
  lists, including credentials. Read the relevant agent/store details when needed.
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
reuse existing setup where appropriate. Guide the required steps without requesting secrets.

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
     information page's **Collection AWS account ID**, chosen region and generated `external_id`
     (or the CloudFormation template from the docs). Outputs: Lambda function ARN, invoker role ARN.
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

Otherwise the deployment from Step 1 decides what is possible:

- **Collection agent** → credentials can stay in the customer's store (self-hosted, below). The
  agent reads the secret at query time, so its role or identity needs read access to that secret.
- **Hosted cloud node or data-store deployment** → nothing on the customer's side can be read, so
  the credentials are Monte Carlo managed. Through the v2 API that is the Snowflake key pair
  (CLI or Terraform step, last row below). Any other connection type on these deployments is
  onboarded in the UI today. Hand off with the selected deployment and any existing IDs; do not
  create an empty warehouse until its reuse in that UI flow is established.

Use the credential policy already resolved in Step 1; ask only for the missing reference or
authentication details. If it changes, revisit the deployment choice before writing:

| Where | Tool | Notes |
|---|---|---|
| AWS Secrets Manager | `create_aws_secrets_manager_credentials(connection_type, aws_secret, aws_region?, assumable_role?, external_id?)` | Direct access: the agent execution identity needs `secretsmanager:GetSecretValue`. With `assumable_role`, the target role needs secret access and a trust policy for the caller, and the caller needs `sts:AssumeRole`; honor its External ID condition. See output-modes. |
| GCP Secret Manager | `create_gcp_secret_manager_credentials(connection_type, gcp_secret)` | Same idea: the agent's service account must read it. |
| Azure Key Vault | `create_azure_key_vault_credentials(connection_type, akv_secret, akv_vault_name and/or akv_vault_url)` | |
| Environment variable on the agent | `create_env_var_credentials(connection_type, env_var_name (MCD_…), kms_key_id?)` | Only with a collection agent the customer runs; the cloud node has no customer-set variables. |
| File on the agent | `create_file_credentials(connection_type, file_path)` | Generic Kubernetes/Docker: mount the JSON file into the agent; use its container path. |
| Monte Carlo stores it (Snowflake key pair) | **not a tool** | Emit `montecarlo credentials create snowflake --account … --user … --warehouse … --private-key @key.p8` or the `montecarlo_snowflake_credentials` resource with `file(...)`. The user runs it and gives back the `id`. |

**Validate before creating.** Each self-hosted create has a matching validate that takes the same
arguments plus `deployment_id`: `validate_aws_secrets_manager_credentials`, `validate_gcp_secret_manager_credentials`, `validate_azure_key_vault_credentials`, `validate_env_var_credentials`, `validate_file_credentials`. It creates nothing and
returns a run: poll `get_validation_run` until `status` is `completed`, honoring `Retry-After`, and
create only once every validation has `passed`. A failure here is almost always the agent's access
to the secret (IAM grant, trust policy, service-account role, Key Vault policy), and it is cheapest
to fix now, before a warehouse or connection exists. For a Snowflake key pair Monte Carlo will
store, emit the validate step beside the create step:
`montecarlo credentials validate-snowflake-credentials --deployment-id … --account … --user … --private-key @key.p8`
(not an MCP tool: the key travels in the request). When the session does not serve these tools,
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

## Step 3: The warehouse

Use the warehouses discovered in Step 0. Match the intended account/host and environment as
well as type and deployment; different Snowflake accounts on one deployment are not automatically
one warehouse. Prefer a verified prior `warehouse_id`; otherwise inspect its connections and
confirm any ambiguity. Do not take the first warehouse with a matching type.

If none represents the target, `create_warehouse(name, deployment_id, type=<warehouse type>)` or
`create_warehouse(name, deployment_id, connection_type=<connection type>)`. Send exactly one of
`type` / `connection_type`; names are unique per type. Carry and record the `warehouse_id`.

## Step 4: The connection

`list_connections(warehouse_id)` first (paginate). Reuse a connection for the same target and
credential identity; inspect the existing non-secret credential details if the IDs differ.
A matching name alone is not proof. A name collision with a different target needs resolution,
not another blind create. Preserve existing jobs and record its ID when reusing.

Otherwise `create_connection(name, warehouse_id, credentials_id)`. The type comes from the
credentials and must fit the warehouse type; omit `job_types` for defaults. Verify the returned
warehouse/deployment association and record `id`, `connection_type`, `deployment_id`, `job_types`.

## Step 5: Validate

The validations API is live: `validate_connection` starts a run for a connection (202, with the
run id) and `get_validation_run` reads it — poll until `status` is `completed`, honoring the
`Retry-After` the response carries, then read each validation's own `passed` verdict. Use those
tools when the session serves them (they reach the MCP server as the generator ships). A dedicated
waiter tool that polls for you is planned; until one of these is available, end with UI validation.
Do **not** substitute any other tool for validation. End with:

> Validate the connection in the Monte Carlo UI: Settings → Integrations → the integration → the
> new connection → **Test**. Collection starts on its own once the connection exists; the first metadata
> appears within about an hour. Until the test and initial collection are confirmed, report
> **connection created, validation pending**, not a completed onboarding.

If validation fails there, the usual causes are, in order: the agent cannot read the secret (IAM
grant, service-account role or Key Vault policy missing); the warehouse user lacks the grants in
the connector's docs page; the network path is missing (Monte Carlo's IPs not allowlisted for the
cloud node, or the agent's VPC has no route to the warehouse). Fix, then `update_connection` is not needed: re-test in the UI.

## Step 6: Summary (always)

Finish every run, including an aborted one, with:

```
Account: <account_name> (<account_id>)
Output mode: act now | terraform | script

Created in this run
  deployment    <id>  <name>  <type>/<runtime_platform>  enabled=<bool>
  agent|store   <id>  (or: registration step handed over, pending)
  credentials   <id>  <connection_type>  <storage_type>  (or: CLI/Terraform step handed over)
  warehouse     <id>  <name>  <type>
  connection    <id>  <name>  <connection_type>  job_types=<…>

Reused (excluded from cleanup)
  deployment / agent|store / credentials / warehouse / connection  <ids and names>

Pending on your side
  - <deploy/register/credential step still to run, with the exact command or file>
  - Validate the connection (Step 5: validate_connection, or in the UI under Settings → Integrations → <integration> → <connection name> → Test)

Cleanup if you abandon this: delete_connection → delete_warehouse → delete_<kind>_credentials →
delete_<platform>_collection_agent|data_store → delete_deployment, in that order. On the generic
agent path, also delete the token or OAuth client this run minted (delete_generic_collection_agent_token /
delete_generic_collection_agent_oauth_client).
```

In artifact mode label resources as **planned**, not created. Record IDs only after execution.
On a handoff or failure, give the last completed stage, non-secret IDs and the exact next step;
show validation only when a connection exists. Cleanup applies only to resources created by this
run, after checking shared dependencies. Deregistration does not delete cloud infrastructure or
storage contents; coordinate removal of deployments with jobs/history rather than forcing it.

## Error handling

- Tool errors arrive as `"<operation> failed: <detail>"` with field-level messages and a request
  id when exposed. Some server errors are masked; do not invent their cause. Fix actionable
  input errors; bound transient retries and reconcile state after uncertain results. Include an available request id
  when a call failed for a reason you could not fix.
- `create_deployment` refused with an account limit reached: the per-account deployment cap is
  raised by Monte Carlo support; do not delete a working deployment to make room.
- A conflict on `create_*` usually means the name exists (warehouse names are unique per type,
  connection names per warehouse) or the deployment cannot take that resource. `list_*` and reuse.
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
