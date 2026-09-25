# Output modes: Terraform, SDK script, CLI

The skill produces the selected onboarding path as tools, Terraform or a v2 CLI/SDK script.
Discover deployments, warehouses, credentials and connections first, using MCP or the available
v2 CLI/SDK fallback. Carry verified IDs into the artifact; do not recreate them. Secret values
are not embedded in generated source: Terraform reads them with `file(...)` or a variable
from an uncommitted `*.tfvars`; the CLI reads them with `@<path>` or a `--<flag>-prompt`; a script
reads them from the environment or a file the customer names.

These are composable examples: emit only the selected deployment and credential variant,
fill non-secret inputs from discovery, and keep references/dependencies consistent. Protect
Terraform state with an encrypted backend and restricted access; reading a secret from a file
does not keep it out of state.

Names below are the API's: `type` is `COLLECTION_AGENT` or `COLLECTION_DATA_STORE`,
`runtime_platform` is `AWS`, `GCP`, `AZURE` or `GENERIC`. Tool name = `operationId` = the
Terraform resource verb's counterpart = the CLI command.

## Terraform

Provider `monte-carlo-data/montecarlo` (generated from the same API). Credentials for the provider
come from the environment (`MCD_DEFAULT_API_ID` / `MCD_DEFAULT_API_TOKEN`) or the CLI profile in
`~/.mcd/profiles.ini`; never literals in a `.tf` file.

```hcl
terraform {
  required_providers {
    montecarlo = { source = "monte-carlo-data/montecarlo" }
  }
}

provider "montecarlo" {
  endpoint = "https://api.getmontecarlo.com"
}
```

### Deployment + AWS collection agent

The deployment comes first because it generates the external id the agent's role must trust.

```hcl
variable "aws_region" { type = string }
# Account information → Collection → AWS account ID, not the customer's account ID.
variable "monte_carlo_collection_account_id" { type = string }
provider "aws" { region = var.aws_region }

resource "montecarlo_deployment" "agent" {
  name             = "prod-vpc-agent"
  type             = "COLLECTION_AGENT"
  runtime_platform = "AWS"
}

# https://registry.terraform.io/modules/monte-carlo-data/mcd-agent/aws
module "mcd_agent" {
  source  = "monte-carlo-data/mcd-agent/aws"
  version = "1.0.7"

  region           = var.aws_region
  cloud_account_id = var.monte_carlo_collection_account_id
  external_id      = montecarlo_deployment.agent.aws_external_id
  # private_subnets = ["subnet-…", "subnet-…"]   # to reach a warehouse inside the VPC
}

resource "montecarlo_aws_collection_agent" "agent" {
  deployment_id       = montecarlo_deployment.agent.id
  lambda_function_arn = module.mcd_agent.mcd_agent_function_arn
  role_arn            = module.mcd_agent.mcd_agent_invoker_role_arn
}
```

GCP: module `monte-carlo-data/mcd-agent/google` (outputs `mcd_agent_uri`, `mcd_agent_invoker_key`)
and `montecarlo_gcp_collection_agent { deployment_id, cloud_run_url, authentication_type =
"GCP_JSON_SERVICE_ACCOUNT_KEY", service_account_key = module.….mcd_agent_invoker_key }`.
Azure: module `monte-carlo-data/mcd-agent/azurerm` (outputs `mcd_agent_function_url`, service
principal ids) and `montecarlo_azure_collection_agent`. Both keep the agent credential inside
Terraform state, which is why they are not MCP tools.

### Deployment + generic collection agent (AWS EKS example)

This example creates an EKS cluster, storage and agent; use the official Docker Compose or
existing-cluster guide instead when that is the chosen runtime. Requires Terraform >= 1.12,
AWS authentication and a pinned compatible chart version. Reuse the provider setup above;
configure the root AWS provider as below. This is the token variant; for OAuth, use the
`montecarlo_generic_collection_agent_oauth_client` resource and the module's `oauth_credentials`
instead. Do not configure both authentication methods.

```hcl
variable "aws_region" { type = string }
variable "backend_service_url" { type = string }
variable "agent_chart_version" { type = string }

provider "aws" { region = var.aws_region }

resource "montecarlo_deployment" "agent" {
  name             = "prod-k8s-agent"
  type             = "COLLECTION_AGENT"
  runtime_platform = "GENERIC"
}

# Returned once; held in protected Terraform state, never copied into chat.
resource "montecarlo_generic_collection_agent_token" "agent" {
  deployment_id = montecarlo_deployment.agent.id
}

module "mcd_agent" {
  source  = "monte-carlo-data/mcd-k8s-agent/aws"
  version = "0.1.10"
  # Account information → Agent Service; use the endpoint for this account/region.
  backend_service_url = var.backend_service_url
  token_credentials = {
    mcd_id    = montecarlo_generic_collection_agent_token.agent.mcd_id
    mcd_token = montecarlo_generic_collection_agent_token.agent.mcd_token
  }
  helm = {
    chart_version = var.agent_chart_version
  }
}
```

After the module has applied and the agent is connected, add/apply the registration below.
This explicit second phase avoids a plan-time module dependency on a module with nested providers
and an unbounded wait for the agent. If connectivity is still pending, fix it before retrying.

```hcl
resource "montecarlo_generic_collection_agent" "agent" {
  deployment_id = montecarlo_deployment.agent.id
}
```

The module populates the agent-auth secret; integration secrets and permissions remain a
separate step. For existing networking/cluster/identity, use the module's documented inputs
instead of its new-cluster defaults. See the [module](https://registry.terraform.io/modules/monte-carlo-data/mcd-k8s-agent/aws/0.1.10)
and the [Generic guide](https://docs.getmontecarlo.com/docs/generic-agent-platforms).

### Deployment + AWS data store

No published module. Bucket, role trusting the external id, and the registration. `mcd_account_id`
is the Monte Carlo collection account shown under Account information → Collection.

```hcl
variable "aws_region" { type = string }
variable "mcd_account_id" { type = string } # Collection AWS account ID
provider "aws" { region = var.aws_region }

resource "montecarlo_deployment" "store" {
  name             = "prod-data-store"
  type             = "COLLECTION_DATA_STORE"
  runtime_platform = "AWS"
}

resource "aws_s3_bucket" "store" { bucket_prefix = "mcd-data-store-" }

resource "aws_s3_bucket_public_access_block" "store" {
  bucket                  = aws_s3_bucket.store.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
resource "aws_s3_bucket_server_side_encryption_configuration" "store" {
  bucket = aws_s3_bucket.store.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}
resource "aws_s3_bucket_lifecycle_configuration" "store" {
  bucket = aws_s3_bucket.store.id
  rule {
    id     = "expire-temporary-data"
    status = "Enabled"
    filter { prefix = "" }
    expiration { days = 90 }
  }
}

resource "aws_iam_role" "store" {
  name_prefix = "mcd-data-store-"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Action    = "sts:AssumeRole"
      Principal = { AWS = "arn:aws:iam::${var.mcd_account_id}:root" }
      Condition = { StringEquals = { "sts:ExternalId" = montecarlo_deployment.store.aws_external_id } }
    }]
  })
}

resource "aws_iam_role_policy" "store" {
  role = aws_iam_role.store.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = ["s3:PutObject", "s3:GetObject", "s3:DeleteObject", "s3:ListBucket",
      "s3:GetBucketPublicAccessBlock", "s3:GetBucketPolicyStatus", "s3:GetBucketAcl"]
      Resource = [aws_s3_bucket.store.arn, "${aws_s3_bucket.store.arn}/*"]
    }]
  })
}

resource "montecarlo_aws_collection_data_store" "store" {
  deployment_id = montecarlo_deployment.store.id
  bucket_name   = aws_s3_bucket.store.bucket
  role_arn      = aws_iam_role.store.arn
  depends_on    = [aws_iam_role_policy.store, aws_s3_bucket_public_access_block.store]
}
```

The dedicated bucket above blocks public access, uses encryption and expires objects after 90 days.
Adjust retention to the approved policy. GCP and Azure stores use
`montecarlo_gcp_collection_data_store` / `montecarlo_azure_collection_data_store`.

### Credentials

Self-hosted direct-access example: the agent execution role reads the secret. If using
`assumable_role`, grant secret access to that target role instead, allow the caller to use
`sts:AssumeRole`, and configure the target trust policy (including its External ID condition
when required). With a customer-managed KMS key, also grant the reading identity the necessary
decrypt permission and key-policy access. Do not attach the direct-access policy below to the
wrong principal. This policy example uses the native AWS module; for Generic EKS, use the
agent identity from that module's guide (`agent_role_arn`), not the native module's output.

```hcl
variable "snowflake_secret_arn" { type = string }

resource "aws_iam_role_policy" "agent_read_secret" {
  role = module.mcd_agent.mcd_agent_execution_role.name
  policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Action = "secretsmanager:GetSecretValue", Resource = var.snowflake_secret_arn }]
  })
}

resource "montecarlo_self_hosted_aws_credentials" "snowflake" {
  connection_type = "snowflake"
  aws_secret      = var.snowflake_secret_arn
  depends_on      = [aws_iam_role_policy.agent_read_secret]
}
```

Other stores: `montecarlo_self_hosted_gcp_credentials { connection_type, gcp_secret }`,
`montecarlo_self_hosted_azure_credentials { connection_type, akv_secret, akv_vault_name }`,
`montecarlo_self_hosted_env_var_credentials { connection_type, env_var_name }`,
`montecarlo_self_hosted_file_credentials { connection_type, file_path }`.

Monte Carlo managed Snowflake key pair (the key is read from a file kept out of version control):

```hcl
resource "montecarlo_snowflake_credentials" "snowflake" {
  account   = "xy12345.us-east-1"
  user      = "MONTE_CARLO"
  warehouse = "MONTE_CARLO_WH"
  # Stored in Terraform state in plaintext: use an encrypted remote backend and restrict who can read state.
  private_key = file("${path.module}/snowflake_key.p8") # PEM text, BEGIN/END lines included
  # private_key_passphrase = var.snowflake_key_passphrase  # only for an encrypted key
}
```

### Warehouse and connection

Choose exactly one credential variant and set `local.snowflake_credentials_id` accordingly.
The rest of the connection and summary refer only to that local:

```hcl
# Self-hosted AWS variant (keep the self-hosted credential resource above):
locals {
  snowflake_credentials_id = montecarlo_self_hosted_aws_credentials.snowflake.id
}
```

For the managed key-pair variant, replace that locals block with:

```hcl
locals {
  snowflake_credentials_id = montecarlo_snowflake_credentials.snowflake.id
}
```

The following uses the AWS agent selected above. For a different or reused deployment, replace
its ID and registration dependency with that selected route; do not leave references to omitted
agent resources. For a reused credential, set the local to its verified ID instead.

```hcl
resource "montecarlo_warehouse" "snowflake" {
  name          = "Snowflake prod"
  type          = "snowflake" # or connection_type = "snowflake"; never both
  deployment_id = montecarlo_deployment.agent.id
  depends_on    = [montecarlo_aws_collection_agent.agent]
}

resource "montecarlo_connection" "snowflake" {
  name           = "snowflake-prod"
  warehouse_id   = montecarlo_warehouse.snowflake.id
  credentials_id = local.snowflake_credentials_id
  # job_types omitted: the type's defaults
}

output "created_ids" {
  value = {
    deployment  = montecarlo_deployment.agent.id
    agent       = montecarlo_aws_collection_agent.agent.id
    credentials = local.snowflake_credentials_id
    warehouse   = montecarlo_warehouse.snowflake.id
    connection  = montecarlo_connection.snowflake.id
  }
}
```

Reusing an existing deployment: omit creation/registration blocks and their `depends_on` and
outputs; use the verified deployment ID. Likewise omit reused warehouse/credential resources
and pass their IDs. Never destroy a shared reused resource as part of cleanup.

## CLI (mc-cli, the `montecarlo` command for the REST API v2) — recommended for local steps

Source: https://github.com/monte-carlo-data/mc-cli. Until its first release, build from source:
`git clone https://github.com/monte-carlo-data/mc-cli.git && cd mc-cli && go build -o . ./cmd/montecarlo`.
After the release, `go install github.com/monte-carlo-data/mc-cli/cmd/montecarlo@latest`. The
legacy `montecarlodata` Python CLI installs a `montecarlo` command too; `montecarlo deployments
--help` succeeds only with mc-cli. Profile once (the customer types the token at the prompt):
`montecarlo profile set default --api-id <id> --api-token-prompt`. Every resource is a command
group and every operation a verb; `--output json` for machine-readable ids; a secret flag takes
`@<path>` or has a `--<flag>-prompt` companion.

```bash
montecarlo whoami
montecarlo deployments list
montecarlo deployments create --type COLLECTION_AGENT --runtime-platform AWS --name prod-vpc-agent --output json
montecarlo deployments get <deployment_id> --output json          # aws_external_id

# … deploy the agent with the module / CloudFormation, then:
montecarlo collection-agents register aws --deployment-id <id> \
  --lambda-function-arn <arn> --role-arn <arn>

# generic agent: credential first, run the agent, then register
montecarlo collection-agents create generic-token --deployment-id <id> --output json   # secret printed once
montecarlo collection-agents register generic --deployment-id <id>

# data store
montecarlo collection-data-stores register aws --deployment-id <id> --bucket-name <bucket> --role-arn <arn>

# credentials: self-hosted reference …
montecarlo credentials list --output json
# Validate the reference against the deployment first (creates nothing; poll the returned run):
montecarlo credentials validate-aws-secrets-manager-credentials --deployment-id <deployment_id> \
  --connection-type snowflake --aws-secret <arn-or-name>
# Create only if discovery found no matching reference:
montecarlo credentials create aws-secrets-manager --connection-type snowflake --aws-secret <arn-or-name>
# … or a key pair Monte Carlo stores (the key is read from a file, never typed into a chat);
# validate it against the deployment first, then create:
montecarlo credentials validate-snowflake-credentials --deployment-id <deployment_id> \
  --account xy12345.us-east-1 --user MONTE_CARLO --private-key @snowflake_key.p8
montecarlo credentials create snowflake --account xy12345.us-east-1 --user MONTE_CARLO \
  --warehouse MONTE_CARLO_WH --private-key @snowflake_key.p8

montecarlo warehouses list --output json
# Reuse the intended warehouse or create it if absent:
montecarlo warehouses create --name "Snowflake prod" --type snowflake --deployment-id <deployment_id> --output json
montecarlo connections list --warehouse-id <warehouse_id> --output json
# Create only if the target connection is absent:
montecarlo connections create --name snowflake-prod --warehouse-id <warehouse_id> --credentials-id <credentials_id> --output json
```

## Python script (`montecarlo` SDK, mc-sdk-python)

`pip install git+https://github.com/monte-carlo-data/mc-sdk-python.git`. The client reads
`MCD_DEFAULT_API_ID` / `MCD_DEFAULT_API_TOKEN` or the CLI profile; only `endpoint` is required.
Every operation is a method on its tag's `*Api` class with the same name as the tool; request
models are `<Schema>In`. Operations the MCP server does not expose (the Snowflake key pair) are
plain SDK calls here, with the secret read from a file the customer names.

This AWS/Snowflake direct-secret-access example takes `MCD_DEPLOYMENT_NAME`,
`MCD_WAREHOUSE_NAME`, `MCD_CONNECTION_NAME` and `SNOWFLAKE_SECRET_ARN` from the approved target.
Populate existing `MCD_DEPLOYMENT_ID`, `MCD_CREDENTIALS_ID`, `MCD_WAREHOUSE_ID` and
`MCD_CONNECTION_ID` when discovery identified them. It never selects an arbitrary compatible
warehouse. Set `MCD_CREATE_DEPLOYMENT=1` only after discovery confirms a new deployment is needed;
otherwise it stops rather than provisioning one. Names/ARNs in this example are identity keys,
not a substitute for resolving the customer's intended account/environment before generation.

The first run of a new deployment stops for infrastructure. Subsequent runs reconcile existing
resources and register a pending agent before continuing. A null External ID or failed enable
stops the connection steps. The script prints created/reused IDs and the pending stage on exit.
It does not read secret contents; MCP-managed key pairs use the separate local CLI/Terraform path.

```python
import os
import sys
import montecarlo
from montecarlo.paging import paginate


def main():
    client = montecarlo.new_client(montecarlo.Options(endpoint="https://api.getmontecarlo.com"))
    deployments = montecarlo.DeploymentsApi(client)
    agents = montecarlo.CollectionAgentsApi(client)
    credentials = montecarlo.CredentialsApi(client)
    warehouses = montecarlo.WarehousesApi(client)
    connections = montecarlo.ConnectionsApi(client)
    created, reused = {}, {}
    pending = "Resolve inputs; no connection has been verified."

    def select(items, selected_id, label):
        matches = [x for x in items if not selected_id or x.id == selected_id]
        if selected_id and not matches:
            raise ValueError(f"{label} ID does not match the selected target")
        if len(matches) > 1:
            raise ValueError(f"Several {label} entries match; select a verified ID")
        return matches[0] if matches else None

    try:
        identity = montecarlo.UsersApi(client).get_current_user()
        print(f"Account: {identity.account_name} ({identity.account_id})")
        if identity.account_frozen:
            raise ValueError("Account is paused")
        # These non-secret inputs/IDs come from the skill's discovery and approved plan.
        secret_arn = os.environ["SNOWFLAKE_SECRET_ARN"]
        if not secret_arn.startswith("arn:") or ":secretsmanager:" not in secret_arn:
            raise ValueError("Use the full secret ARN to avoid matching names across regions/accounts")
        dep_name = os.environ["MCD_DEPLOYMENT_NAME"]
        warehouse_name = os.environ["MCD_WAREHOUSE_NAME"]
        connection_name = os.environ["MCD_CONNECTION_NAME"]
        dep_id = os.environ.get("MCD_DEPLOYMENT_ID")
        inventory = deployments.list_deployments()
        dep = select(inventory if dep_id else [d for d in inventory if d.name == dep_name],
                     dep_id, "deployment")
        if dep is None:
            if os.environ.get("MCD_CREATE_DEPLOYMENT") != "1":
                raise ValueError("Select an existing deployment or approve a new one before setting MCD_CREATE_DEPLOYMENT=1")
            dep = deployments.create_deployment(montecarlo.DeploymentIn(
                type="COLLECTION_AGENT", runtime_platform="AWS", name=dep_name))
            created["deployment"] = dep.id
        else:
            reused["deployment"] = dep.id
        dep = deployments.get_deployment(dep.id)
        if dep.type != "COLLECTION_AGENT" or dep.runtime_platform != "AWS":
            raise ValueError("This script requires the selected AWS collection-agent deployment")
        if not dep.enabled:
            pending = f"Resume with MCD_DEPLOYMENT_ID={dep.id}; deploy/register the AWS agent."
            if not dep.aws_external_id:
                print("External ID not available yet; retry this read or resolve permissions/status.")
                return 1
            print(f"Deployment External ID: {dep.aws_external_id}")
            if "deployment" in created:
                print("Deploy with the Collection AWS account ID and this External ID, then return LAMBDA_ARN and ROLE_ARN.")
                return 0
            if not os.environ.get("LAMBDA_ARN") or not os.environ.get("ROLE_ARN"):
                print("Set LAMBDA_ARN and ROLE_ARN after deploying the agent.")
                return 1
            agent = agents.register_aws_collection_agent(montecarlo.AwsCollectionAgentIn(
                deployment_id=dep.id, lambda_function_arn=os.environ["LAMBDA_ARN"],
                role_arn=os.environ["ROLE_ARN"]))
            created["agent"] = agent.id
            if not deployments.get_deployment(dep.id).enabled:
                raise ValueError("Registration is not enabled; stop before creating credentials or connection")

        # Direct execution-role access only; an assumed-role variant must match that role too.
        pending = "Reconcile credentials, warehouse and connection; do not retry uncertain creates blindly."
        candidates = []
        for row in paginate(credentials.list_credentials):
            if row.connection_type == "snowflake" and row.storage_type == "aws_secrets_manager":
                detail = credentials.get_aws_secrets_manager_credentials(row.id)
                if detail.aws_secret == secret_arn and not detail.assumable_role:
                    candidates.append(detail)
        creds = select(candidates, os.environ.get("MCD_CREDENTIALS_ID"), "credentials")
        if creds is None:
            creds = credentials.create_aws_secrets_manager_credentials(
                montecarlo.AwsSecretsManagerCredentialsIn(connection_type="snowflake", aws_secret=secret_arn))
            created["credentials"] = creds.id
        else:
            reused["credentials"] = creds.id

        # Names are supplied for the target discovered by the skill, not guessed from type.
        warehouse_id = os.environ.get("MCD_WAREHOUSE_ID")
        inventory = list(paginate(warehouses.list_warehouses))
        wh = select(inventory if warehouse_id else
                    [w for w in inventory if w.name == warehouse_name and w.type == "snowflake"],
                    warehouse_id, "warehouse")
        if wh is not None:
            if wh.type != "snowflake" or wh.deployment_id != dep.id:
                raise ValueError("Selected warehouse belongs to a different type/deployment")
            reused["warehouse"] = wh.id
        else:
            wh = warehouses.create_warehouse(montecarlo.WarehouseIn(
                name=warehouse_name, deployment_id=dep.id, type="snowflake"))
            created["warehouse"] = wh.id

        existing = list(paginate(connections.list_connections, warehouse_id=wh.id))
        conn = select([c for c in existing if c.credentials_id == creds.id and
                       c.connection_type == "snowflake"], os.environ.get("MCD_CONNECTION_ID"), "connection")
        if conn is not None:
            if conn.deployment_id != dep.id:
                raise ValueError("Connection deployment does not match the selected route")
            reused["connection"] = conn.id
        else:
            if any(c.name == connection_name for c in existing):
                raise ValueError("Connection name exists with another credential; verify identity before proceeding")
            conn = connections.create_connection(montecarlo.ConnectionIn(
                name=connection_name, warehouse_id=wh.id, credentials_id=creds.id))
            created["connection"] = conn.id
        pending = f"Validate connection {conn.id} in the UI and confirm initial collection."
        return 0
    except (ValueError, KeyError) as error:
        print(f"Stopped: {error}", file=sys.stderr)
        return 1
    except montecarlo.ApiException as error:
        print(f"API call failed (HTTP {error.status}); reconcile state before retrying.", file=sys.stderr)
        return 1
    finally:
        for label, resources in (("Created this run", created), ("Reused; excluded from cleanup", reused)):
            print(label)
            for kind, resource_id in resources.items():
                print(f"  {kind:12} {resource_id}")
        print(f"Pending: {pending}")


if __name__ == "__main__":
    raise SystemExit(main())
```

The legacy `montecarlodata` Python CLI is not part of this flow, even though its command is also
named `montecarlo`: it speaks a different API and its ids are not the ids the tools above return.
Use mc-cli or the SDK so the summary of created ids stays consistent.
