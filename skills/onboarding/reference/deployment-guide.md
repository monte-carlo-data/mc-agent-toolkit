# Deployment prerequisites and handoffs

Read only the section for the selected route. Start with the official
[Deployment and Connecting](https://docs.getmontecarlo.com/docs/deployment-and-connecting)
terminology and requirements. That guide covers Cloud Deployment, Cloud with Customer-hosted
Data Store Deployment, and Customer-hosted Agent & Data Store Deployment. For the outbound
agent family, use the separate [Generic Agent guide](https://docs.getmontecarlo.com/docs/generic-agent-platforms).
These are collection agents, not AI agents.

## Select from requirements, not from product vocabulary

Discover the integration, account/host, environment, cloud/region and existing deployments.
Resolve only missing decisions. Customer-network origin (including a stated preference) or
self-hosted credentials requires an agent. Otherwise collection may run in Monte Carlo Cloud
if its public or private route is supported and authorized. Customer-hosted samples require
customer storage: datastore-only with Cloud, or the storage used by the agent.

[Architecture](https://docs.getmontecarlo.com/docs/platform-architecture) distinguishes samples
and temporary results from metadata, metrics, query logs and aggregated statistics stored in
Monte Carlo. Turning sampling off is not a promise that no data leaves the customer.

## Preflight for the chosen path

- Check Monte Carlo Account Owner access for deployment registration, effective write scope,
  and the subscription requirements in the selected guide. The general hybrid guide currently
  requires Scale or Enterprise with ESP; PrivateLink has its own Advanced Networking requirement;
  Generic requires Enterprise + Advanced Networking. Identity reads alone do not expose all of these.
- Identify the cloud administrator for external resources, supported region and integration/auth
  compatibility. Use the exact target cloud/region, not the example's region. A missing read or
  an unknown/legacy deployment calls for a UI/support handoff, not forced new infrastructure.
- Give the customer a concrete handoff: selected deployment ID, non-secret inputs, guide or
  artifact to execute, safe outputs to return and the condition for resuming. Do not ask them
  to paste tokens, keys, auth headers or connection strings into chat.

## Direct Cloud connectivity, with either data-store location

Use [Network Connectivity](https://docs.getmontecarlo.com/docs/networking) and the
[AWS](https://docs.getmontecarlo.com/docs/aws-private-link) or
[Azure](https://docs.getmontecarlo.com/docs/azure-private-link) PrivateLink compatibility sections.
A private warehouse endpoint does not automatically require an agent, and PrivateLink does not
require customers to give up a preference for connections from their own network.

For public routes, obtain the account's Collection IPs and allowlist all required addresses.
For private routes, check integration, cloud, region, vendor edition/authentication, endpoint
creation and approval. Do not infer universal support from Snowflake or Databricks support on
AWS/Azure; use the matrix for the exact integration. Follow required support handoffs and wait
for endpoint approvals before registration. For Snowflake, distinguish service connectivity from
internal-stage connectivity and use the account identifier supplied for the approved route.

A customer-hosted data store changes sample storage, not where Cloud connects to the integration.

## Cloud-native agents (inbound from Monte Carlo)

Treat the two network segments separately: **Monte Carlo → agent** and **agent → integration**.
An agent can use PrivateLink toward its integration when supported, independently of its
inbound route. Cloud-native deployment is generally the simpler agent option when it satisfies
both paths; it is not a guarantee of no internet exposure on every cloud.

| Platform | Deployment and registration handoff |
|---|---|
| [AWS](https://docs.getmontecarlo.com/docs/create-and-register-an-aws-agent) | Provision in Monte Carlo first. Read its generated External ID. Configure the module/template with that value, the **Collection AWS account ID** from Account information (not the customer's account ID), and the chosen region/network. Return Lambda and invoker-role ARNs, register, confirm enabled. V2 uses supported VPC endpoints for inbound invocation; separately configure the agent's route to the warehouse and required cloud services. |
| [Azure](https://docs.getmontecarlo.com/docs/create-and-register-an-azure-agent) | Provision, deploy Function and storage, choose Function App Key or supported service-principal/custom-header auth, then complete registration locally. Inbound HTTPS is public by default; private endpoints require the documented provision/request/approval sequence. Configure outbound VNet reachability separately. |
| [GCP](https://docs.getmontecarlo.com/docs/create-and-register-a-gcp-agent) | Provision, choose project/region and deploy the Cloud Run agent/storage; establish invoker credentials and network access. Complete registration locally and confirm enabled. The general matrix lists no Private Link for GCP **classic ingress**; it does not describe Generic's outbound path. |

The v2 CLI/SDK/provider registrations are separate from the historical CLI commands in public
product docs. Use the per-tag API reference and output-modes for v2 syntax/IDs. Do not substitute
an older command into a v2 resource chain without verifying how its result is reconciled.

## Customer-hosted data store without an agent

Use a dedicated private object store and the cloud's access identity. AWS External ID trust is
not the Azure/GCP authentication model. Complete the selected guide before registering:

- [AWS S3](https://docs.getmontecarlo.com/docs/direct-connection-with-an-aws-data-store): provision
  first; use generated External ID and Collection account in the assumable role; return bucket
  name and role ARN. The output-modes reference includes an S3 Terraform example.
- [Azure Blob](https://docs.getmontecarlo.com/docs/create-and-register-an-azure-blob-data-store):
  storage account supporting block blobs, private container, and connection-string or OAuth
  credentials. Follow the guide's permissions and private endpoint requirements for the chosen auth.
- [GCP](https://docs.getmontecarlo.com/docs/direct-connection-with-a-gcp-data-store): private GCS
  bucket and service account with the documented object/bucket permissions; registration uses
  credentials supplied locally. Follow encryption/lifecycle guidance in the selected guide.

## Generic Agent (outbound to Monte Carlo)

Use [Generic Agent](https://docs.getmontecarlo.com/docs/generic-agent-platforms) and its children;
do not inherit the classic architecture/networking rules. No inbound ports are required, but
outbound access and customer-hosted storage/credentials must be configured.

1. Choose an existing suitable runtime: [Docker Compose](https://docs.getmontecarlo.com/docs/docker-compose)
   or [Kubernetes](https://docs.getmontecarlo.com/docs/kubernetes), including supported cloud modules.
   A new managed cluster is one option, not a prerequisite for every Generic deployment.
2. Choose token or OAuth before registration (the auth method is fixed afterward). Create the
   credential locally and keep it in the customer's secret system. Use the regional Agent Service
   endpoint from Account information; a private endpoint needs its own approved setup.
3. Configure object storage and the agent's access to it. Bare Docker/Helm deployment does not
   create usable storage by itself; do not register a second datastore deployment merely for this.
4. Supply integration credentials via a supported secret manager or mounted JSON file; the file
   path must exist inside the container. Follow the selected runtime's identity/permissions guide.
5. Allow the required outbound destinations from that guide (Agent Service, token endpoint for
   OAuth, storage, secrets and integrations; runtime image pulls as applicable). Account for proxies
   or TLS inspection when present. Confirm the agent is connected before enabling registration.

Generic is public preview, requires Enterprise + Advanced Networking, and the customer operates
and upgrades the runtime. Hand off unsupported integration/auth/runtime requirements explicitly.
