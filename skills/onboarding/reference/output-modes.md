# Output modes: Terraform, SDK script, CLI

The skill produces the same five steps in three shapes. Reads (`list_deployments`,
`list_warehouses`, `list_credentials`) always run through the MCP tools so the artifact reuses what
exists. Secrets never appear in an artifact: Terraform reads them with `file(...)` or a variable
from an uncommitted `*.tfvars`; the CLI reads them with `@<path>` or a `--<flag>-prompt`; a script
reads them from the environment or a file the customer names.

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
resource "montecarlo_deployment" "agent" {
  name             = "prod-vpc-agent"
  type             = "COLLECTION_AGENT"
  runtime_platform = "AWS"
}

# https://registry.terraform.io/modules/monte-carlo-data/mcd-agent/aws
module "mcd_agent" {
  source  = "monte-carlo-data/mcd-agent/aws"
  version = "~> 1.0"

  region      = "us-east-1"
  external_id = montecarlo_deployment.agent.aws_external_id
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

### Deployment + generic collection agent (Kubernetes, Docker)

```hcl
resource "montecarlo_deployment" "agent" {
  name             = "prod-k8s-agent"
  type             = "COLLECTION_AGENT"
  runtime_platform = "GENERIC"
}

# The credential the agent presents. Returned once; held in state.
resource "montecarlo_generic_collection_agent_token" "agent" {
  deployment_id = montecarlo_deployment.agent.id
}

# One way to run it: https://registry.terraform.io/modules/monte-carlo-data/mcd-k8s-agent/aws
# (azurerm and google variants take the same inputs). Or Helm/Docker with the same token.
module "mcd_agent" {
  source  = "monte-carlo-data/mcd-k8s-agent/aws"
  version = "~> 0.1"
  backend_service_url = var.backend_service_url   # Account information → Agent Service → Public endpoint
  # token or oauth_credentials from the resource above, see the module docs
}

# Enables the agent once it has connected; 503 (retried) until then.
resource "montecarlo_generic_collection_agent" "agent" {
  deployment_id = montecarlo_deployment.agent.id
  depends_on    = [module.mcd_agent]
}
```

### Deployment + AWS data store

No published module. Bucket, role trusting the external id, and the registration. `mcd_account_id`
is the Monte Carlo collection account shown under Account information → Collection.

```hcl
resource "montecarlo_deployment" "store" {
  name             = "prod-data-store"
  type             = "COLLECTION_DATA_STORE"
  runtime_platform = "AWS"
}

resource "aws_s3_bucket" "store" { bucket_prefix = "mcd-data-store-" }

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
      Effect   = "Allow"
      Action   = ["s3:PutObject", "s3:GetObject", "s3:DeleteObject", "s3:ListBucket",
                  "s3:GetBucketPublicAccessBlock", "s3:GetBucketPolicyStatus", "s3:GetBucketAcl"]
      Resource = [aws_s3_bucket.store.arn, "${aws_s3_bucket.store.arn}/*"]
    }]
  })
}

resource "montecarlo_aws_collection_data_store" "store" {
  deployment_id = montecarlo_deployment.store.id
  bucket_name   = aws_s3_bucket.store.bucket
  role_arn      = aws_iam_role.store.arn
  depends_on    = [aws_iam_role_policy.store]
}
```

Add public-access block, encryption and 90-day lifecycle rules on the bucket as the provider's
`examples/resources/montecarlo_aws_collection_data_store` shows. GCP and Azure stores use
`montecarlo_gcp_collection_data_store` / `montecarlo_azure_collection_data_store`.

### Credentials

Self-hosted, the secret stays in the customer's store. With an agent, grant its execution role
read access first.

```hcl
resource "aws_iam_role_policy" "agent_read_secret" {
  role = module.mcd_agent.mcd_agent_execution_role.name
  policy = jsonencode({
    Version = "2012-10-17"
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
  account     = "xy12345.us-east-1"
  user        = "MONTE_CARLO"
  warehouse   = "MONTE_CARLO_WH"
  private_key = file("${path.module}/snowflake_key.p8")   # PEM text, BEGIN/END lines included
  # private_key_passphrase = var.snowflake_key_passphrase  # only for an encrypted key
}
```

### Warehouse and connection

```hcl
resource "montecarlo_warehouse" "snowflake" {
  name          = "Snowflake prod"
  type          = "snowflake"                 # or connection_type = "snowflake"; never both
  deployment_id = montecarlo_deployment.agent.id
  depends_on    = [montecarlo_aws_collection_agent.agent]
}

resource "montecarlo_connection" "snowflake" {
  name           = "snowflake-prod"
  warehouse_id   = montecarlo_warehouse.snowflake.id
  credentials_id = montecarlo_self_hosted_aws_credentials.snowflake.id
  # job_types omitted: the type's defaults
}

output "created_ids" {
  value = {
    deployment  = montecarlo_deployment.agent.id
    agent       = montecarlo_aws_collection_agent.agent.id
    credentials = montecarlo_self_hosted_aws_credentials.snowflake.id
    warehouse   = montecarlo_warehouse.snowflake.id
    connection  = montecarlo_connection.snowflake.id
  }
}
```

Reusing an existing deployment: drop the `montecarlo_deployment` and agent blocks and set
`deployment_id = "<id from list_deployments>"`.

## CLI (`montecarlo`, the REST API CLI)

Install: `go install github.com/monte-carlo-data/mc-cli/cmd/montecarlo@latest` (or build from
source until the first release). Profile once:
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
montecarlo credentials create aws-secrets-manager --connection-type snowflake --aws-secret <arn-or-name>
# … or a key pair Monte Carlo stores (the key is read from a file, never typed into a chat)
montecarlo credentials create snowflake --account xy12345.us-east-1 --user MONTE_CARLO \
  --warehouse MONTE_CARLO_WH --private-key @snowflake_key.p8

montecarlo warehouses create --name "Snowflake prod" --type snowflake --deployment-id <deployment_id> --output json
montecarlo connections create --name snowflake-prod --warehouse-id <warehouse_id> --credentials-id <credentials_id> --output json
```

## Python script (`montecarlo` SDK, mc-sdk-python)

`pip install git+https://github.com/monte-carlo-data/mc-sdk-python.git`. The client reads
`MCD_DEFAULT_API_ID` / `MCD_DEFAULT_API_TOKEN` or the CLI profile; only `endpoint` is required.
Every operation is a method on its tag's `*Api` class with the same name as the tool; request
models are `<Schema>In`. Operations the MCP server does not expose (the Snowflake key pair) are
plain SDK calls here, with the secret read from a file the customer names.

```python
import os, sys
import montecarlo
from montecarlo.paging import paginate

client = montecarlo.new_client(montecarlo.Options(endpoint="https://api.getmontecarlo.com"))
deployments = montecarlo.DeploymentsApi(client)
agents = montecarlo.CollectionAgentsApi(client)
credentials = montecarlo.CredentialsApi(client)
warehouses = montecarlo.WarehousesApi(client)
connections = montecarlo.ConnectionsApi(client)

created: dict[str, str] = {}
try:
    # 1. deployment (reuse when the id is known)
    deployment_id = os.environ.get("MCD_DEPLOYMENT_ID")
    if not deployment_id:
        dep = deployments.create_deployment(
            montecarlo.DeploymentIn(type="COLLECTION_AGENT", runtime_platform="AWS", name="prod-vpc-agent")
        )
        created["deployment"] = deployment_id = dep.id
        external_id = deployments.get_deployment(deployment_id).aws_external_id
        print(f"deploy the agent with external_id={external_id}, then set LAMBDA_ARN and ROLE_ARN", file=sys.stderr)
        agent = agents.register_aws_collection_agent(
            montecarlo.AwsCollectionAgentIn(
                deployment_id=deployment_id,
                lambda_function_arn=os.environ["LAMBDA_ARN"],
                role_arn=os.environ["ROLE_ARN"],
            )
        )
        created["agent"] = agent.id

    # 2. credentials: a reference to the customer's store …
    creds = credentials.create_aws_secrets_manager_credentials(
        montecarlo.AwsSecretsManagerCredentialsIn(connection_type="snowflake", aws_secret=os.environ["SNOWFLAKE_SECRET_ARN"])
    )
    # … or a key pair Monte Carlo stores, read from a file:
    # creds = credentials.create_snowflake_credentials(montecarlo.SnowflakeCredentialsIn(
    #     account="xy12345.us-east-1", user="MONTE_CARLO", warehouse="MONTE_CARLO_WH",
    #     private_key=open(os.environ["SNOWFLAKE_KEY_PATH"]).read()))
    created["credentials"] = creds.id

    # 3. warehouse: reuse one of the right type on this deployment, else create
    existing = [w for w in paginate(warehouses.list_warehouses) if w.type == "snowflake" and w.deployment_id == deployment_id]
    if existing:
        warehouse_id = existing[0].id
    else:
        wh = warehouses.create_warehouse(montecarlo.WarehouseIn(name="Snowflake prod", deployment_id=deployment_id, type="snowflake"))
        created["warehouse"] = warehouse_id = wh.id

    # 4. connection
    conn = connections.create_connection(
        montecarlo.ConnectionIn(name="snowflake-prod", warehouse_id=warehouse_id, credentials_id=creds.id)
    )
    created["connection"] = conn.id
except montecarlo.ApiException as e:
    print(f"failed: {e.status} {e.body}", file=sys.stderr)
finally:
    # 6. summary, whatever happened
    for kind, id_ in created.items():
        print(f"{kind:12} {id_}")
    print("validate in the UI: Settings → Integrations → snowflake-prod → Test connection")
```

The legacy Python CLI (`pip install montecarlodata`) can still onboard Snowflake in one command,
`montecarlo integrations add-snowflake --private-key <file> …`, but it does not speak the v2 API and
its ids are not the ones the tools above return; prefer the v2 CLI or SDK so the summary is
consistent.
