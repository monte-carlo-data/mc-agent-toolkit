# Output modes: Terraform, SDK script, CLI

The skill produces the selected onboarding path as tools, Terraform or a v2 CLI/SDK script.
Discover deployments, warehouses, credentials and connections first, using MCP or the available
v2 CLI/SDK fallback. Carry verified IDs into the artifact; do not recreate them. Secret values
are not embedded in generated source: Terraform reads them with `file(...)` or a variable
from an uncommitted `*.tfvars` into a write-only argument; the CLI reads them with `@<path>` or a `--<flag>-prompt`; a script
reads them from the environment or a file the customer names.

These are composable examples: emit only the selected deployment and credential variant,
fill non-secret inputs from discovery, and keep references/dependencies consistent.

Names below are the API's: `type` is `COLLECTION_AGENT` or `COLLECTION_DATA_STORE`,
`runtime_platform` is `AWS`, `GCP`, `AZURE` or `GENERIC`. Tool name = `operationId` = the
Terraform resource verb's counterpart = the CLI command.

## Rules for every command the customer runs

These apply to every shell snippet handed over, in any mode: mc-cli, AWS CLI, gcloud, az,
Terraform commands. Customers paste them into bash or zsh, often on macOS.

- **CRITICAL: NEVER suggest a command that reads a secret's value**, not even piped into
  `jq keys` or `wc`: `aws secretsmanager get-secret-value`, `gcloud secrets versions access`,
  `az keyvault secret show`, `cat` of a key file. The value passes through the customer's shell
  and one typo prints it. To check access, use the cloud's policy simulator or Monte Carlo's
  credential validation; to check a secret exists or changed, use its metadata
  (`describe-secret`, `list-secret-version-ids`).
- **IMPORTANT: keep every line short and paste-safe.** Put long values in variables, one per
  line, and pass multi-value parameters through a file (CloudFormation `--parameters
  file://params.json`, `--policy-document file://policy.json`) rather than inline JSON or escaped
  commas. Terminals wrap long lines when copying, which splits URLs and ids.
- **IMPORTANT: brace every variable next to a colon, bracket, dot or letter: `${VAR}:secret:…`,
  `${KIND}[]`, never `$VAR:secret:…` or `$KIND[]`.** zsh reads `$VAR:s…` as a substitution
  modifier and `$VAR[…]` as an array subscript, and silently rewrites the value (a garbled ARN,
  then `MalformedPolicyDocument`; an empty JMESPath query).
- **IMPORTANT: portable only.** No GNU-only flags: `date -d` fails on macOS, so use fixed UTC
  timestamps (`2026-01-31T00:00:00Z`) or `--start-time` values the customer fills in; no
  `sed -i` without a suffix; no `source <(…)`.
- Print only what the customer sends back: ARNs, ids, names, decisions (`allowed`), never a
  credential. Say which outputs to send.

## Terraform

Provider `monte-carlo-data/montecarlo` (generated from the same API). Credentials for the provider
come from the environment (`MCD_DEFAULT_API_ID` / `MCD_DEFAULT_API_TOKEN`) or the CLI profile in
`~/.mcd/profiles.ini`; never literals in a `.tf` file.

**NEVER hard-code the provider's `endpoint`.** An API key works only in its own Monte Carlo
environment, and an explicit `endpoint` overrides the profile's `mcd_api_endpoint`: a key sent to
another environment's API is refused (`User is not authorized … explicit deny`, which the provider
may surface as `no value given for required property type`). Use the variable below: left unset
(`null`), the provider takes the profile's endpoint; when credentials come from
`MCD_DEFAULT_API_*` alone, the customer sets it to their environment's API URL. Its default is
never a URL. `montecarlo whoami` shows which account the profile reaches.

**Secrets are write-only arguments.** Every secret a resource sends to Monte Carlo is
`<name>_wo`, with a required `<name>_wo_version`. Terraform sends it on apply and never stores it
in state or in a plan, which needs Terraform 1.11 or later (an older one errors rather than
storing it). Changing a secret alone plans nothing: bump its version with it. A secret can still
reach state from another source, in these two cases, so keep state in a backend that encrypts it
and limits who can read it:

- Secrets Monte Carlo generates, the generic agent's token and its OAuth client secret. They are
  returned once and held by their resource. Hand them on through a write-only argument, for
  example `aws_secretsmanager_secret_version.secret_string_wo`, never through an output: an
  output, even a sensitive one, is stored in state too.
- Secrets an upstream module or resource returns, such as the GCP agent module's invoker key,
  which that module keeps in its own state.

```hcl
terraform {
  # Write-only arguments need Terraform 1.11 or later.
  required_version = ">= 1.11"

  required_providers {
    # 0.1.27 is the first with `montecarlo_hosting_private_link`.
    montecarlo = { source = "monte-carlo-data/montecarlo", version = ">= 0.1.27" }
    # For the AWS examples; 6.50 is the first with `secret_string_wo`. Omit when no AWS resource is used.
    aws = { source = "hashicorp/aws", version = ">= 6.50" }
  }
}

# Endpoint from the profile's mcd_api_endpoint when set; otherwise pass it in (no default).
variable "montecarlo_endpoint" {
  type    = string
  default = null # null means "use the profile's endpoint"; never a URL here
}

provider "montecarlo" {
  endpoint = var.montecarlo_endpoint
}
```

### Deployment + AWS collection agent

The deployment comes first because it generates the external id the agent's role must trust.
Monte Carlo's AWS account, which assumes the invoker role, comes from the
`montecarlo_hosting_private_link` data source: never ask the customer
for it or make it a variable.

```hcl
variable "aws_region" { type = string }
variable "deployment_name" { type = string } # from the customer
provider "aws" { region = var.aws_region }

# Monte Carlo's AWS account, which assumes the agent's invoker role.
data "montecarlo_hosting_private_link" "this" {}

resource "montecarlo_deployment" "agent" {
  name             = var.deployment_name
  type             = "COLLECTION_AGENT"
  runtime_platform = "AWS"
}

# https://registry.terraform.io/modules/monte-carlo-data/mcd-agent/aws
module "mcd_agent" {
  source  = "monte-carlo-data/mcd-agent/aws"
  version = "1.0.7"

  region           = var.aws_region
  cloud_account_id = data.montecarlo_hosting_private_link.this.aws.account_id
  external_id      = montecarlo_deployment.agent.aws_external_id
  # private_subnets = ["subnet-…", "subnet-…"]   # to reach a warehouse inside the VPC
}

resource "montecarlo_aws_collection_agent" "agent" {
  deployment_id       = montecarlo_deployment.agent.id
  lambda_function_arn = module.mcd_agent.mcd_agent_function_arn
  role_arn            = module.mcd_agent.mcd_agent_invoker_role_arn
}
```

GCP: module `monte-carlo-data/mcd-agent/google` with `generate_key = true` (outputs
`mcd_agent_uri`, `mcd_agent_invoker_key`) and `montecarlo_gcp_collection_agent { deployment_id,
cloud_run_url, authentication_type = "GCP_JSON_SERVICE_ACCOUNT_KEY", service_account_key_wo =
base64decode(module.….mcd_agent_invoker_key[0]), service_account_key_wo_version = 1 }`: the
module returns the key base64-encoded and the API takes the key file's contents.
Azure: module `monte-carlo-data/mcd-agent/azurerm` (outputs `mcd_agent_function_url`, service
principal ids) and `montecarlo_azure_collection_agent { …, function_app_key = { app_key_wo,
app_key_wo_version } }`, or a `service_principal` block with `client_secret_wo` /
`client_secret_wo_version`. Both registrations send a secret, which is why they are not MCP tools;
the provider takes it write-only, but the module still holds it in its own state.

### Deployment + generic collection agent (AWS EKS example)

This example creates an EKS cluster, storage and agent; use the official Docker Compose or
existing-cluster guide instead when that is the chosen runtime. Requires Terraform >= 1.12 (the
module's floor, above the provider's 1.11), AWS authentication and a pinned compatible chart
version. Reuse the provider setup above, keeping its `aws >= 6.50` constraint, which
`secret_string_wo` needs; configure the root AWS provider as below.

The agent's credential goes to Secrets Manager through a write-only argument and the module
reads that secret (`create = false`), so the only other copy is the credential resource's own.
Passing it to the module's `oauth_credentials` or `token_credentials` instead would store it a
second time. This is the OAuth variant. For a token, use
`montecarlo_generic_collection_agent_token`, write `{ mcd_id, mcd_token }` to the secret, and
point `token_secret = { create = false, name = … }` at it instead of `oauth_secret`. Do not
configure both authentication methods.

```hcl
variable "aws_region" { type = string }
variable "backend_service_url" { type = string }
variable "agent_chart_version" { type = string }
variable "deployment_name" { type = string } # from the customer

provider "aws" { region = var.aws_region }

resource "montecarlo_deployment" "agent" {
  name             = var.deployment_name
  type             = "COLLECTION_AGENT"
  runtime_platform = "GENERIC"
}

# Returned once and held in this resource's state; never copied into chat.
resource "montecarlo_generic_collection_agent_oauth_client" "agent" {
  deployment_id = montecarlo_deployment.agent.id
}

# Named per deployment: with `create = false` the module grants the agent read access to every
# secret whose name starts with `name`.
resource "aws_secretsmanager_secret" "mcd_agent_oauth" {
  name = "mcd/agent/${montecarlo_deployment.agent.name}/oauth"
}

resource "aws_secretsmanager_secret_version" "mcd_agent_oauth" {
  secret_id = aws_secretsmanager_secret.mcd_agent_oauth.id
  secret_string_wo = jsonencode({
    client_id     = montecarlo_generic_collection_agent_oauth_client.agent.client_id
    client_secret = montecarlo_generic_collection_agent_oauth_client.agent.client_secret
  })
  # Bump when the client is replaced, so the new secret is written.
  secret_string_wo_version = 1
}

module "mcd_agent" {
  source  = "monte-carlo-data/mcd-k8s-agent/aws"
  version = "0.1.10" # 0.1.4 is the first that reads an existing secret
  # Account information → Agent Service; use the endpoint for this account/region.
  backend_service_url = var.backend_service_url
  oauth_secret = {
    create = false
    name   = aws_secretsmanager_secret.mcd_agent_oauth.name
  }
  # Required alongside `oauth_secret`: without it the module asks for token credentials.
  token_secret = {
    create = false
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

The agent reads its credential from the secret written above; integration secrets and
permissions remain a separate step. For existing networking/cluster/identity, use the module's documented inputs
instead of its new-cluster defaults. See the [module](https://registry.terraform.io/modules/monte-carlo-data/mcd-k8s-agent/aws/0.1.10)
and the [Generic guide](https://docs.getmontecarlo.com/docs/generic-agent-platforms).

### Deployment + AWS data store

No published module. Bucket, role trusting the external id, and the registration. The role
trusts Monte Carlo's AWS account from the `montecarlo_hosting_private_link` data source. When the
deployment already exists and the artifact holds only the AWS resources, keep the `montecarlo`
provider (credentials from the CLI profile) for this data source alone.

```hcl
variable "aws_region" { type = string }
variable "deployment_name" { type = string } # from the customer
provider "aws" { region = var.aws_region }

# Monte Carlo's AWS account, which assumes the role.
data "montecarlo_hosting_private_link" "this" {}

resource "montecarlo_deployment" "store" {
  name             = var.deployment_name
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
      Principal = { AWS = "arn:aws:iam::${data.montecarlo_hosting_private_link.this.aws.account_id}:root" }
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

Monte Carlo managed Snowflake key pair (the key is read from a file kept out of version control).
Every input comes from the customer, per the connection-inputs reference: the variables carry no
`default`, so `terraform plan` asks for any value not set in an uncommitted `*.tfvars`.

```hcl
variable "snowflake_account" { type = string }          # e.g. CURRENT_ACCOUNT() + region, from the customer
variable "snowflake_user" { type = string }             # the user the public key is set on
variable "snowflake_warehouse" { type = string }        # API-optional; queries fail without one
variable "snowflake_private_key_path" { type = string } # absolute path; file() does not expand ~

resource "montecarlo_snowflake_credentials" "snowflake" {
  account   = var.snowflake_account
  user      = var.snowflake_user
  warehouse = var.snowflake_warehouse
  # Write-only: never stored in state or a plan. Changing the key alone plans nothing; bump the
  # version with it. Bumping either version sends the key and the passphrase together.
  private_key_wo         = file(var.snowflake_private_key_path) # PEM text, BEGIN/END lines included
  private_key_wo_version = 1
  # Only for an encrypted key; omit both otherwise.
  # private_key_passphrase_wo         = var.snowflake_key_passphrase
  # private_key_passphrase_wo_version = 1
}
```

### Snowflake service user, in the same configuration

Only when the customer asks Terraform to create the Snowflake side too (the service user does not
exist yet). It replaces the docs' setup script (https://docs.getmontecarlo.com/docs/snowflake): a
service user (`TYPE=SERVICE`), a role, a warehouse and the grants below. Without that request, keep
the hand-off: the customer runs the docs' script. Propose the docs' names (`MONTE_CARLO`,
`MONTE_CARLO_ROLE`, `MONTE_CARLO_WH`) as the values in `*.tfvars` and let the customer confirm or
change them; do not ask them to invent names. If one of these objects already exists, ask whether to
use another name or to `terraform import` it; a plain apply fails with "already exists".

- **The customer generates the key pair** locally (`openssl`, per the docs' key-pair section) and
  Terraform reads both files by path. **NEVER use `tls_private_key`**: it keeps the private key in
  state. The private key reaches the self-hosted secret only through `secret_string_wo` (or the
  managed variant's `private_key_wo`). The self-hosted secret needs an **unencrypted PKCS#8** key
  (`openssl pkcs8 -topk8 -nocrypt`); the preconditions below stop an encrypted or PKCS#1 key at plan.
- **The Snowflake provider signs in as the customer's admin**, by key pair from a file path: a role
  allowed to create users, roles and warehouses and to grant `IMPORTED PRIVILEGES` on `SNOWFLAKE`
  (`ACCOUNTADMIN`, or a custom role with `CREATE USER`, `CREATE ROLE`, `CREATE WAREHOUSE` and
  `MANAGE GRANTS`). Ask which login and role, and whether its key is encrypted; never for its key
  or passphrase. For an encrypted admin key the customer exports `SNOWFLAKE_PRIVATE_KEY_PASSPHRASE`
  in their shell, which the provider reads; never a variable or `*.tfvars`.
- **Databases** to monitor come from the customer; never grant on every database by default.
- **Schema-level future grants override database-level ones.** Before planning, have the customer
  run the docs' check (`SHOW FUTURE GRANTS IN SCHEMA …` for each schema) and send back only which
  schemas and object types it lists. Add an `in_schema` grant for exactly those, and add it to
  `terraform_data.snowflake_grants_ready`; never for object types it did not list.
- If the customer uses row access policies, tell them `MONTE_CARLO_ROLE` must be exempt from them,
  or monitors fail.
- **Key rotation:** the customer points both path variables at the new pair and applies. The
  secret's version is derived from the public key, so the new private key is sent in the same apply
  that sets the new public key; never a hand-bumped version that can fall out of step.

```hcl
# In required_providers: snowflake = { source = "snowflakedb/snowflake", version = ">= 2.22" }

variable "snowflake_organization_name" { type = string } # SELECT CURRENT_ORGANIZATION_NAME();
variable "snowflake_account_name" { type = string }      # SELECT CURRENT_ACCOUNT_NAME();
variable "snowflake_admin_user" { type = string }        # the login Terraform signs in with
variable "snowflake_admin_role" { type = string }        # e.g. ACCOUNTADMIN
variable "snowflake_admin_private_key_path" { type = string }
variable "snowflake_databases" { type = set(string) } # the databases Monte Carlo monitors
# Proposed values: MONTE_CARLO, MONTE_CARLO_ROLE, MONTE_CARLO_WH (the docs' names).
variable "snowflake_user_name" { type = string }
variable "snowflake_role_name" { type = string }
variable "snowflake_warehouse_name" { type = string }
# The new service user's key pair, generated by the customer; absolute paths (file() does not
# expand ~).
variable "snowflake_public_key_path" { type = string }
variable "snowflake_private_key_path" { type = string }

provider "snowflake" {
  organization_name = var.snowflake_organization_name
  account_name      = var.snowflake_account_name
  user              = var.snowflake_admin_user
  role              = var.snowflake_admin_role
  authenticator     = "SNOWFLAKE_JWT"
  private_key       = file(var.snowflake_admin_private_key_path) # provider config is not kept in state
  # Encrypted admin key: export SNOWFLAKE_PRIVATE_KEY_PASSPHRASE in the shell instead.
}

locals {
  # PEM body without the BEGIN/END lines: what rsa_public_key and the secret's private_key take.
  snowflake_key_body = { for k, path in {
    public  = var.snowflake_public_key_path
    private = var.snowflake_private_key_path
    } : k => join("", [
      for line in split("\n", file(path)) : trimspace(line) if !startswith(trimspace(line), "-----")
  ]) }
  # Changes whenever the key pair does, so a rotation always re-sends the private key.
  snowflake_key_version = parseint(substr(sha256(local.snowflake_key_body.public), 0, 12), 16)

  # Per object type: the docs' REFERENCES / MONITOR / SELECT grants, on existing and future objects.
  snowflake_object_privileges = {
    "TABLES"          = ["REFERENCES", "SELECT"]
    "VIEWS"           = ["REFERENCES", "SELECT"]
    "EXTERNAL TABLES" = ["REFERENCES", "SELECT"]
    "DYNAMIC TABLES"  = ["MONITOR", "SELECT"]
    "STREAMS"         = ["SELECT"]
  }
  snowflake_object_grants = { for g in flatten([
    for db in var.snowflake_databases : [
      for plural, privileges in local.snowflake_object_privileges : [
        for scope in ["all", "future"] : { database = db, plural = plural, privileges = privileges, scope = scope }
      ]
    ]
  ]) : "${g.database}/${g.plural}/${g.scope}" => g }
}

resource "snowflake_account_role" "monte_carlo" { name = var.snowflake_role_name }

resource "snowflake_warehouse" "monte_carlo" {
  name                = var.snowflake_warehouse_name
  warehouse_size      = "XSMALL"
  initially_suspended = true
  auto_suspend        = 300
  auto_resume         = "true"
}

resource "snowflake_service_user" "monte_carlo" {
  name              = var.snowflake_user_name
  default_role      = snowflake_account_role.monte_carlo.name
  default_warehouse = snowflake_warehouse.monte_carlo.name
  rsa_public_key    = local.snowflake_key_body.public

  lifecycle {
    precondition {
      condition     = strcontains(file(var.snowflake_public_key_path), "BEGIN PUBLIC KEY")
      error_message = "snowflake_public_key_path must be a PEM public key (openssl rsa -pubout)."
    }
  }
}

resource "snowflake_grant_account_role" "monte_carlo" {
  role_name = snowflake_account_role.monte_carlo.name
  user_name = snowflake_service_user.monte_carlo.name
}

resource "snowflake_grant_privileges_to_account_role" "warehouse" {
  account_role_name = snowflake_account_role.monte_carlo.name
  privileges        = ["OPERATE", "USAGE", "MONITOR"]
  on_account_object {
    object_type = "WAREHOUSE"
    object_name = snowflake_warehouse.monte_carlo.name
  }
}

# Query history, for query logs and lineage.
resource "snowflake_grant_privileges_to_account_role" "query_history" {
  account_role_name = snowflake_account_role.monte_carlo.name
  privileges        = ["IMPORTED PRIVILEGES"]
  on_account_object {
    object_type = "DATABASE"
    object_name = "SNOWFLAKE"
  }
}

resource "snowflake_grant_privileges_to_account_role" "database" {
  for_each          = var.snowflake_databases
  account_role_name = snowflake_account_role.monte_carlo.name
  privileges        = ["USAGE", "MONITOR"]
  on_account_object {
    object_type = "DATABASE"
    object_name = each.value
  }
}

resource "snowflake_grant_privileges_to_account_role" "all_schemas" {
  for_each          = var.snowflake_databases
  account_role_name = snowflake_account_role.monte_carlo.name
  privileges        = ["USAGE", "MONITOR"]
  on_schema { all_schemas_in_database = each.value }
}

resource "snowflake_grant_privileges_to_account_role" "future_schemas" {
  for_each          = var.snowflake_databases
  account_role_name = snowflake_account_role.monte_carlo.name
  privileges        = ["USAGE", "MONITOR"]
  on_schema { future_schemas_in_database = each.value }
}

resource "snowflake_grant_privileges_to_account_role" "objects" {
  for_each          = local.snowflake_object_grants
  account_role_name = snowflake_account_role.monte_carlo.name
  privileges        = each.value.privileges
  on_schema_object {
    dynamic "all" {
      for_each = each.value.scope == "all" ? [1] : []
      content {
        object_type_plural = each.value.plural
        in_database        = each.value.database
      }
    }
    dynamic "future" {
      for_each = each.value.scope == "future" ? [1] : []
      content {
        object_type_plural = each.value.plural
        in_database        = each.value.database
      }
    }
  }
}

# The one place that lists every grant: the connection depends on this. Add any in_schema grant here.
resource "terraform_data" "snowflake_grants_ready" {
  depends_on = [
    snowflake_grant_account_role.monte_carlo,
    snowflake_grant_privileges_to_account_role.warehouse,
    snowflake_grant_privileges_to_account_role.query_history,
    snowflake_grant_privileges_to_account_role.database,
    snowflake_grant_privileges_to_account_role.all_schemas,
    snowflake_grant_privileges_to_account_role.future_schemas,
    snowflake_grant_privileges_to_account_role.objects,
  ]
}
```

With the AWS agent, Terraform also writes the self-hosted secret. Use this in place of
`var.snowflake_secret_arn` in the Credentials example above, and point that example's policy at
`aws_secretsmanager_secret.snowflake.arn`:

```hcl
resource "aws_secretsmanager_secret" "snowflake" {
  name = "monte-carlo/${var.deployment_name}/snowflake"
}

resource "aws_secretsmanager_secret_version" "snowflake" {
  secret_id = aws_secretsmanager_secret.snowflake.id
  # Write-only: the private key never reaches state or a plan.
  secret_string_wo = jsonencode({
    connect_args = {
      account     = "${var.snowflake_organization_name}-${var.snowflake_account_name}"
      user        = snowflake_service_user.monte_carlo.name
      warehouse   = snowflake_warehouse.monte_carlo.name
      private_key = local.snowflake_key_body.private
    }
  })
  secret_string_wo_version = local.snowflake_key_version

  lifecycle {
    precondition {
      condition = (
        strcontains(file(var.snowflake_private_key_path), "-----BEGIN PRIVATE KEY-----") &&
        !strcontains(file(var.snowflake_private_key_path), "ENCRYPTED")
      )
      error_message = "snowflake_private_key_path must be an unencrypted PKCS#8 key (openssl pkcs8 -topk8 -nocrypt)."
    }
  }
}
```

**Test the credentials before creating the connection: two applies of the same configuration.**
Terraform cannot run Monte Carlo's validation in the middle of an apply, and SKILL.md's
*Validate before creating* still applies. So the Monte Carlo credential, warehouse and connection
are switched on by `create_connection`, which the customer sets in their `*.tfvars`:

1. Apply with `create_connection = false`: the Snowflake side, the deployment and agent, the
   secret and the agent's read grant. The customer sends back `validation_inputs`.
2. Run `validate_aws_secrets_manager_credentials(deployment_id, connection_type="snowflake",
   aws_secret=<secret_arn>)` and read the run with `get_validation_run`. It proves the agent reads
   the secret and signs in to Snowflake as the new user. Go on only when every validation passed;
   otherwise relay `friendly_message` and `resolution` and fix before creating anything in Monte Carlo.
3. The customer sets `create_connection = true` and applies again. Then validate the connection
   (Step 5).

**NEVER create the connection in the first apply**, and never set `create_connection = true` before
the credential validation passed. These blocks replace the Credentials example's credential
resource and the whole *Warehouse and connection* section below: do not also emit that section's
`locals` block or `created_ids` output, which refer to the resources without an index.

```hcl
variable "create_connection" { type = bool } # false for apply 1; true after the credentials validate
variable "warehouse_name" { type = string }  # from the customer
variable "connection_name" { type = string } # from the customer

output "validation_inputs" { # ids and an ARN only, for the credential validation
  value = {
    deployment_id = montecarlo_deployment.agent.id
    secret_arn    = aws_secretsmanager_secret.snowflake.arn
  }
}

resource "montecarlo_self_hosted_aws_credentials" "snowflake" {
  count           = var.create_connection ? 1 : 0
  connection_type = "snowflake"
  aws_secret      = aws_secretsmanager_secret.snowflake.arn
  depends_on      = [aws_iam_role_policy.agent_read_secret, aws_secretsmanager_secret_version.snowflake]
}

locals {
  snowflake_credentials_id = one(montecarlo_self_hosted_aws_credentials.snowflake[*].id)
}

resource "montecarlo_warehouse" "snowflake" {
  count         = var.create_connection ? 1 : 0
  name          = var.warehouse_name
  type          = "snowflake"
  deployment_id = montecarlo_deployment.agent.id
  depends_on    = [montecarlo_aws_collection_agent.agent]
}

resource "montecarlo_connection" "snowflake" {
  count          = var.create_connection ? 1 : 0
  name           = var.connection_name
  warehouse_id   = montecarlo_warehouse.snowflake[0].id
  credentials_id = local.snowflake_credentials_id
  # Collection never starts before the grants exist.
  depends_on = [terraform_data.snowflake_grants_ready]
}

output "created_ids" { # null for the credential, warehouse and connection after apply 1
  value = {
    deployment  = montecarlo_deployment.agent.id
    agent       = montecarlo_aws_collection_agent.agent.id
    credentials = local.snowflake_credentials_id
    warehouse   = one(montecarlo_warehouse.snowflake[*].id)
    connection  = one(montecarlo_connection.snowflake[*].id)
  }
}
```

**Managed key-pair variant** (Monte Carlo stores the key, for example on the Cloud deployment): no
AWS secret, policy or self-hosted credential. Replace those and the credential resource above with
the block below, keep the warehouse, connection and outputs, and drop `secret_arn` from
`validation_inputs`. The check between the applies is the CLI's (the key travels in the request, so
it is not an MCP tool): `montecarlo credentials validate snowflake --deployment-id <id> --account
<org>-<account> --user <user> --private-key @<private_key_path>`.

```hcl
resource "montecarlo_snowflake_credentials" "snowflake" {
  count                  = var.create_connection ? 1 : 0
  account                = "${var.snowflake_organization_name}-${var.snowflake_account_name}"
  user                   = snowflake_service_user.monte_carlo.name
  warehouse              = snowflake_warehouse.monte_carlo.name
  private_key_wo         = file(var.snowflake_private_key_path) # PEM text, BEGIN/END lines included
  private_key_wo_version = local.snowflake_key_version
}

locals {
  snowflake_credentials_id = one(montecarlo_snowflake_credentials.snowflake[*].id)
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
variable "warehouse_name" { type = string }  # from the customer, or an existing warehouse's
variable "connection_name" { type = string } # from the customer

resource "montecarlo_warehouse" "snowflake" {
  name          = var.warehouse_name
  type          = "snowflake" # or connection_type = "snowflake"; never both
  deployment_id = montecarlo_deployment.agent.id
  depends_on    = [montecarlo_aws_collection_agent.agent]
}

resource "montecarlo_connection" "snowflake" {
  name           = var.connection_name
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

### BI container, credentials and connection

A Tableau, Looker or Power BI connection goes on a `montecarlo_bi_container`, not a warehouse.
This example is Tableau with a personal access token on a verified deployment; every input comes
from the connection-inputs checklist and no variable has a `default`. For a password or a
connected app, set that method's arguments instead (`username` with `password_wo`, or `username`
with the `connected_app_*` arguments and `connected_app_secret_value_wo`); never two methods.

```hcl
variable "deployment_id" { type = string }       # verified in discovery
variable "bi_container_name" { type = string }   # from the customer
variable "connection_name" { type = string }     # from the customer
variable "tableau_server_name" { type = string } # https://…
variable "tableau_site_name" { type = string }   # omit the argument only for the default site
variable "tableau_token_name" { type = string }
variable "tableau_token_value_path" { type = string } # absolute path to a file holding the token

resource "montecarlo_bi_container" "tableau" {
  type          = "tableau" # looker | tableau | power-bi; one looker container for both Looker connections
  name          = var.bi_container_name
  deployment_id = var.deployment_id
}

resource "montecarlo_tableau_credentials" "tableau" {
  server_name = var.tableau_server_name
  site_name   = var.tableau_site_name
  token_name  = var.tableau_token_name
  # Write-only: never stored in state or a plan. Bump the version with a new token.
  token_value_wo         = trimspace(file(var.tableau_token_value_path))
  token_value_wo_version = 1
}

resource "montecarlo_connection" "tableau" {
  name            = var.connection_name
  bi_container_id = montecarlo_bi_container.tableau.id
  credentials_id  = montecarlo_tableau_credentials.tableau.id
}
```

The other BI credentials follow the same shape:

- `montecarlo_looker_credentials { base_url, api_client_id, api_client_secret_wo }`.
- `montecarlo_looker_git_clone_credentials { repo_url, ssh_key_wo }` for SSH (`file()` of the
  key, BEGIN/END lines included), or `{ repo_url, username, token_wo }` for HTTPS. Its connection
  takes the same `looker` container's id as the Looker API connection.
- `montecarlo_power_bi_credentials { tenant_id, app_client_id, auth_mode = "service_principal",
  app_client_secret_wo }`, or `auth_mode = "primary_user"` with `username` and `password_wo`.

Every `<field>_wo` has its `<field>_wo_version` (SKILL.md rule 7).

### Custom connector: container, credentials, connection, ingestion key

A custom ETL or BI connector goes on a `montecarlo_etl_container` (`custom-etl-connector`) or a
`montecarlo_bi_container` (`custom-bi-connector`); a custom warehouse connector on a
`montecarlo_warehouse` of type `custom-integration`. An agent-registered connector takes the
type's `deployment_id` from `list_custom_connector_types` and a self-hosted credential whose
`connection_type` is the type's id (the credentials resources above). A push-only one takes
neither, plus the ingestion key below. This example is push-only ETL.

```hcl
variable "etl_container_name" { type = string } # from the customer
variable "connection_name" { type = string }    # from the customer
variable "push_key_secret_name" { type = string } # where the customer's push job reads the key

resource "montecarlo_etl_container" "push" {
  type = "custom-etl-connector" # no deployment_id: push-only
  name = var.etl_container_name
}

resource "montecarlo_connection" "push" {
  name             = var.connection_name
  etl_container_id = montecarlo_etl_container.push.id # no credentials_id: push-only
}

# Returned once and held in this resource's state; never copied into chat or an output.
resource "montecarlo_ingestion_key" "push" {
  etl_container_id = montecarlo_etl_container.push.id
}

resource "aws_secretsmanager_secret" "push_key" {
  name = var.push_key_secret_name
}

resource "aws_secretsmanager_secret_version" "push_key" {
  secret_id = aws_secretsmanager_secret.push_key.id
  secret_string_wo = jsonencode({
    mcd_id    = montecarlo_ingestion_key.push.mcd_id
    mcd_token = montecarlo_ingestion_key.push.mcd_token
  })
  # Bump when the key is replaced, so the new token is written.
  secret_string_wo_version = 1
}
```

Use the customer's own secret store in place of Secrets Manager when they have another; the rule
is the same (SKILL.md rule 7).

### Remove what Terraform manages

Monte Carlo doesn't record which tool created a resource. To find out whether Terraform manages
one, the customer runs this in each Terraform directory that uses the provider. It prints the
address of the resource whose id this is, or nothing, and never the state, which can hold
generated secrets:

```bash
ID=<resource-id>
[ -n "${ID}" ] && terraform state list -id="${ID}"
```

Don't search the whole state for the id instead: a reused resource's id also appears as a
reference on the managed resources that use it, so a search reports it as managed when it isn't.
The guard matters because an empty `-id` lists every resource.

An address in the output means that directory manages it. Remove it the Terraform way: delete its
block (and whatever references it) from the configuration, run `terraform plan` and check that it
destroys only what is being removed, then `terraform apply`. `terraform destroy -target='<address>'`
also works, but the next apply creates it again while the block remains. To keep the resource in
Monte Carlo and stop managing it with Terraform, delete the block and run
`terraform state rm '<address>'`. Keep the address in single quotes: addresses such as
`module.x.res["key"]` or `res[0]` otherwise break in the shell.

## AWS CLI: customer-side AWS steps

### Deploy the AWS agent with CloudFormation

Parameter and output names come from the template itself
(`https://mcd-public-resources.s3.amazonaws.com/cloudformation/aws_apollo_agent.yaml`); if a
docs summary disagrees, the template is right, but don't tell the customer a docs page is wrong
unless you read that page yourself.

```bash
REGION=<region>
STACK=mcd-agent-<name>
TPL=https://mcd-public-resources.s3.amazonaws.com
TPL="${TPL}/cloudformation/aws_apollo_agent.yaml"
aws sts get-caller-identity --query Account --output text   # the account the agent runs in

cat > mcd-agent-params.json <<'EOF'
[
  {"ParameterKey": "ExternalId",        "ParameterValue": "<external-id>"},
  {"ParameterKey": "CloudAccountId",    "ParameterValue": "<Collection AWS account ID>"},
  {"ParameterKey": "ExistingVpcId",     "ParameterValue": "<vpc-id>"},
  {"ParameterKey": "ExistingSubnetIds", "ParameterValue": "<subnet-a>,<subnet-b>"}
]
EOF
aws cloudformation create-stack --region "$REGION" --stack-name "$STACK" \
  --template-url "$TPL" --capabilities CAPABILITY_IAM \
  --parameters file://mcd-agent-params.json
aws cloudformation wait stack-create-complete --region "$REGION" --stack-name "$STACK"
aws cloudformation describe-stacks --region "$REGION" --stack-name "$STACK" \
  --query "Stacks[0].Outputs[].[OutputKey,OutputValue]" --output table
```

Drop the two `Existing*` parameters when the agent doesn't need a VPC. The customer sends back
`FunctionArn` and `InvocationRoleArn` for `register_aws_collection_agent`, and checks that
`InvocationRoleExternalId` matches. The agent's execution role is the stack resource
`ExecutionRole`; its security group is the `SecurityGroupId` output.

### Grant the agent read access to a secret

Before validating a self-hosted reference (SKILL.md Step 2), the agent's execution role needs
`secretsmanager:GetSecretValue` on the secret (plus `kms:Decrypt` for a customer-managed key). Add
a **separate** inline policy per grant so existing grants are not rewritten, and list the role's
policies first: `put-role-policy` replaces a policy of the same name.

```bash
ROLE=$(aws cloudformation describe-stack-resource \
  --region "$REGION" --stack-name "$STACK" --logical-resource-id ExecutionRole \
  --query StackResourceDetail.PhysicalResourceId --output text)
SECRET_ARN=<secret-arn>
aws iam list-role-policies --role-name "$ROLE"

cat > secret-policy.json <<EOF
{"Version": "2012-10-17", "Statement": [{"Effect": "Allow",
  "Action": "secretsmanager:GetSecretValue", "Resource": "${SECRET_ARN}"}]}
EOF
aws iam put-role-policy --role-name "$ROLE" --policy-name <new-policy-name> \
  --policy-document file://secret-policy.json
```

To change an existing policy instead, back it up, edit with `jq`, review a diff, then apply:
`get-role-policy … --query PolicyDocument > backup.json` → `jq … > new.json` →
`diff <(jq -S . backup.json) <(jq -S . new.json)` → `put-role-policy … file://new.json`.

### Check the agent can read secrets

```bash
ROLE_ARN=$(aws iam get-role --role-name "$ROLE" --query Role.Arn --output text)
Q='EvaluationResults[].ResourceSpecificResults[]'
Q="${Q}.[EvalResourceName,EvalResourceDecision]"
aws iam simulate-principal-policy --policy-source-arn "$ROLE_ARN" \
  --action-names secretsmanager:GetSecretValue \
  --resource-arns <secret-arn-1> <secret-arn-2> \
  --query "$Q" --output text
```

With several `--resource-arns`, per-secret decisions are in `ResourceSpecificResults`; the
top-level `EvalResourceName` is a single grouped row with `${Region}` placeholders. Use the same
query for a single ARN: `EvalResourceDecision` exists only per resource, so
`EvaluationResults[].EvalResourceDecision` prints an empty line.

### Revoke the agent's access to one secret

When an integration is removed, take away the agent's read access to its secret, and only that.
Read the policy first: delete it only if it grants nothing but this secret; otherwise edit the
ARN out (back up, `jq`, the normalised diff above, `put-role-policy`).

```bash
SECRET_ARN=<secret-arn>
POLICY=<policy-name>
aws iam get-role-policy --role-name "$ROLE" --policy-name "$POLICY" \
  --query PolicyDocument --output json > "${POLICY}.backup.json"
jq -c '[.Statement[].Resource] | flatten' "${POLICY}.backup.json"
aws iam delete-role-policy --role-name "$ROLE" --policy-name "$POLICY"
```

Then run the check above with this secret and the agent's other secrets: this one should show
`implicitDeny`, every other `allowed`. To undo, `put-role-policy` with the backup.

### Remove an AWS agent

Monte Carlo first, in the summary's cleanup order (connections → warehouses → credentials →
agent → deployment), then the customer's side. The agent's storage bucket is versioned, and S3
refuses to delete a bucket that still holds **old versions or delete markers**, which
`list-objects-v2` doesn't show: both `terraform destroy` and `delete-stack` then fail (or stop)
with `BucketNotEmpty`. Empty it first, after confirming the bucket name belongs to the agent being
removed (CloudFormation: the `StorageArn` output; Terraform module:
`terraform state show module.mcd_agent.aws_s3_bucket.mcd_agent_store`):

```bash
B=<agent-bucket-name>
while :; do
  aws s3api list-object-versions --bucket "${B}" --max-items 1000 \
    --query '{Objects: [Versions, DeleteMarkers][][].{Key: Key, VersionId: VersionId}, Quiet: `true`}' \
    --output json > empty-bucket.json
  jq -e '.Objects | length > 0' empty-bucket.json > /dev/null || break
  aws s3api delete-objects --bucket "${B}" --delete file://empty-bucket.json > /dev/null
done
```

Then `terraform plan -destroy -out=destroy.tfplan` (review it lists only this agent's
resources) and `terraform apply destroy.tfplan`, or `aws cloudformation delete-stack` and
`wait stack-delete-complete` on the exact stack name (similarly named stacks are common). An agent
running in a VPC takes 15–40 minutes to delete while AWS releases the Lambda's network
interfaces; the wait isn't stuck.

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
montecarlo deployments create --type COLLECTION_AGENT --runtime-platform AWS --name <deployment_name> --output json
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
montecarlo credentials validate aws-secrets-manager --deployment-id <deployment_id> \
  --connection-type snowflake --aws-secret <arn-or-name>
# Create only if discovery found no matching reference:
montecarlo credentials create aws-secrets-manager --connection-type snowflake --aws-secret <arn-or-name>
# … or a key pair Monte Carlo stores (the key is read from a file, never typed into a chat);
# validate it against the deployment first, then create:
# (every <value> from the connection-inputs checklist; none has a default):
montecarlo credentials validate snowflake --deployment-id <deployment_id> \
  --account <snowflake_account> --user <snowflake_user> --private-key @<key_file.p8>
montecarlo credentials create snowflake --account <snowflake_account> --user <snowflake_user> \
  --warehouse <snowflake_warehouse> --private-key @<key_file.p8>

montecarlo warehouses list --output json
# Reuse the intended warehouse or create it if absent:
montecarlo warehouses create --name "<warehouse_name>" --type snowflake --deployment-id <deployment_id> --output json
montecarlo connections list --warehouse-id <warehouse_id> --output json
# Create only if the target connection is absent:
montecarlo connections create --name <connection_name> --warehouse-id <warehouse_id> --credentials-id <credentials_id> --output json

# BI tool (Tableau here): a BI container instead of a warehouse. Reuse one for the same instance:
montecarlo bi-containers list --output json
montecarlo bi-containers create --type tableau --name "<bi_container_name>" --deployment-id <deployment_id> --output json
# Exactly one sign-in method; the secret from a hidden prompt or a file, never a literal:
montecarlo credentials validate tableau --deployment-id <deployment_id> \
  --server-name <https://server> --site-name <site> --username <tableau_user> --password-prompt
montecarlo credentials create tableau --server-name <https://server> --site-name <site> \
  --username <tableau_user> --password-prompt --output json
# Other types: looker (--base-url --api-client-id --api-client-secret-prompt),
# looker-git-clone (--repo-url with --ssh-key @<key_file> or --username --token-prompt),
# power-bi (--tenant-id --app-client-id --auth-mode service_principal --app-client-secret-prompt).
montecarlo connections create --name <connection_name> --bi-container-id <bi_container_id> --credentials-id <credentials_id> --output json

# Custom connector: the type's id and deployment come from discovery, never chosen here.
montecarlo etl-containers create --type custom-etl-connector --name "<etl_container_name>" --deployment-id <type_deployment_id> --output json
# … then a self-hosted credential with --connection-type <type_id>, and
montecarlo connections create --name <connection_name> --etl-container-id <etl_container_id> --credentials-id <credentials_id> --output json
# Push-only: no --deployment-id on the container, no --credentials-id on the connection, then the
# ingestion key for that container (printed once, to the customer; store it where the push job reads it):
montecarlo integration-keys create ingestion --etl-container-id <etl_container_id> --output json
```

## Python script (`pycarlo2` SDK, mc-sdk-python)

`pip install git+https://github.com/monte-carlo-data/mc-sdk-python.git`. The client reads
`MCD_DEFAULT_API_ID` / `MCD_DEFAULT_API_TOKEN` or the CLI profile; only `endpoint` is required,
and it comes from `MCD_API_ENDPOINT` (the customer's environment's API base URL), never a literal.
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
stops the connection steps. Before creating a credential reference it validates it from the
deployment and stops, creating nothing, unless every validation passed. The script prints
created/reused IDs and the pending stage on exit.
It does not read secret contents; MCP-managed key pairs use the separate local CLI/Terraform path.

```python
import os
import sys
import time
import pycarlo2
from pycarlo2.paging import paginate


def main():
    client = pycarlo2.new_client(pycarlo2.Options(endpoint=os.environ["MCD_API_ENDPOINT"]))
    deployments = pycarlo2.DeploymentsApi(client)
    agents = pycarlo2.CollectionAgentsApi(client)
    credentials = pycarlo2.CredentialsApi(client)
    warehouses = pycarlo2.WarehousesApi(client)
    connections = pycarlo2.ConnectionsApi(client)
    validations = pycarlo2.ValidationsApi(client)
    created, reused = {}, {}
    pending = "Resolve inputs; no connection has been verified."

    def select(items, selected_id, label):
        matches = [x for x in items if not selected_id or x.id == selected_id]
        if selected_id and not matches:
            raise ValueError(f"{label} ID does not match the selected target")
        if len(matches) > 1:
            raise ValueError(f"Several {label} entries match; select a verified ID")
        return matches[0] if matches else None

    def check(run, label):
        # A run takes seconds to a few minutes; each validation carries its own verdict.
        deadline = time.monotonic() + 300
        while run.status != "completed":
            if time.monotonic() > deadline:
                raise ValueError(f"{label} validation {run.id} is still running; read it again later")
            time.sleep(10)
            run = validations.get_validation_run(run.id)
        failed = [v for v in run.validations if v.passed is not True]
        if failed:
            problems = "; ".join(
                f"{v.name}: " + (" ".join(f"{e.friendly_message} {e.resolution or ''}".strip()
                                          for e in v.errors)
                                 or ("failed" if v.passed is False else "no verdict"))
                for v in failed)
            raise ValueError(f"{label} validation {run.id} failed: {problems}")

    try:
        identity = pycarlo2.UsersApi(client).get_current_user()
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
            dep = deployments.create_deployment(pycarlo2.DeploymentIn(
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
            agent = agents.register_aws_collection_agent(pycarlo2.AwsCollectionAgentIn(
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
            # Check the reference from this deployment before storing it; the check creates nothing.
            check(credentials.validate_aws_secrets_manager_credentials(
                pycarlo2.AwsSecretsManagerCredentialsValidateIn(
                    deployment_id=dep.id, connection_type="snowflake", aws_secret=secret_arn)),
                "Credentials")
            creds = credentials.create_aws_secrets_manager_credentials(
                pycarlo2.AwsSecretsManagerCredentialsIn(connection_type="snowflake", aws_secret=secret_arn))
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
            wh = warehouses.create_warehouse(pycarlo2.WarehouseIn(
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
            conn = connections.create_connection(pycarlo2.ConnectionIn(
                name=connection_name, warehouse_id=wh.id, credentials_id=creds.id))
            created["connection"] = conn.id
        pending = f"Validate connection {conn.id} in the UI and confirm initial collection."
        return 0
    except (ValueError, KeyError) as error:
        print(f"Stopped: {error}", file=sys.stderr)
        return 1
    except pycarlo2.ApiException as error:
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
