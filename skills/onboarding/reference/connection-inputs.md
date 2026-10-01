# Connection inputs: what each path requires

Every value a deployment, credential, warehouse or connection needs is either **known** (the
customer said it, or discovery read it) or **missing**. There is no third state. This reference
lists the inputs per path and connection type, so the checklist is complete before anything is
created, emitted or handed over.

## Rules

- **CRITICAL: never fill a required input with a guess.** Not an example value from these
  references or the docs (`MONTE_CARLO`, `MONTE_CARLO_WH`, `xy12345.us-east-1`, `prod-vpc-agent`),
  not a conventional name, not a value inferred from another field. A wrong user or warehouse still
  creates the credentials and the connection; they only fail at validation, after everything exists.
- **CRITICAL: resolve the checklist before the first write.** Build the checklist for the chosen
  deployment, credential path and connection type from the tables below. Present it in the plan
  (rule 4) with each value and where it came from (customer / discovery). Ask for every missing
  entry in one message. Do not call a create tool, emit a create command, or hand over an artifact
  while any entry is missing.
- **IMPORTANT: "optional" in the API is not "optional for this customer".** The tables mark inputs
  that the API accepts without but that the connection needs to work (the Snowflake warehouse is the
  common one). Ask about those too; leave them out only when the customer confirms the fallback
  applies (for example, the Snowflake user has a default warehouse).
- **IMPORTANT: ask for names and references, never secret values.** For a secret, the input is
  where it lives (file path, secret name/ARN, variable name) and, for self-hosted secrets, whether
  its contents carry every required key. The customer checks the keys; you never see the values.
- **CRITICAL: NEVER give a credential field a default value, in any output mode.** This covers the
  account, user, warehouse, role, host, port, database, key file path and secret reference, and
  every other field of a credential or its connection. A missing value fails at once with an error
  that names the missing field, and the customer supplies it. A default value fails later, after the
  credentials and connection exist, with an error that does not point at the field (a wrong
  Snowflake user surfaces as `JWT token is invalid`), and someone has to work out which value was
  wrong. So a value the customer has not given stays missing:
  - Terraform: a `variable` with no `default`, so `terraform plan` stops and asks for it. No
    example value in `default`, in a committed `*.tfvars`, or in a `locals` block.
  - Script: `os.environ["NAME"]` (fails if unset), never `os.environ.get("NAME", "<value>")`.
  - CLI: a visible `<placeholder>` left for the customer, never a filled-in guess.
  - Tool call: no call until the customer gives the value.

  Values discovery verified (a reused `deployment_id`, an existing warehouse's name) may be written
  literally.

## Support: what these tools can connect, and how

Check every requested integration **before** asking about its deployment or credentials, and use
the same reads to tell the customer what can be added. Supported types change as the API grows,
so this section says how to discover them; it does not list them.

| Where the secret lives | How the credentials are created | Which types |
|---|---|---|
| The customer's own store, read by a collection agent | MCP tools: `create_aws_secrets_manager_credentials`, `create_gcp_secret_manager_credentials`, `create_azure_key_vault_credentials`, `create_env_var_credentials`, `create_file_credentials`. Only a reference is passed. | A type that is itself a value of `create_warehouse`'s `type` list in this session. Any other connection type is settled as described below the table. |
| Monte Carlo stores it (managed) | **Not an MCP tool**: the request carries the secret. A CLI or Terraform step the customer runs (rule 6). | A type with a `get_<type>_credentials` or `delete_<type>_credentials` tool in this session, or listed by `montecarlo credentials create --help` when the customer has mc-cli. |
| Neither | — | Hand off to the UI (Settings → Integrations). |

- **CRITICAL: discover types from this session, NEVER from memory or from examples in these
  references.** The managed getter/delete tools can lag the API; when they and the customer's
  `montecarlo credentials create --help` disagree, the CLI is newer.
- **CRITICAL: a connection type that is not itself a warehouse `type` is settled by the API, not
  by you.** The tools do not publish which warehouse type a connection type maps to, and several
  connection types share one. So such a type counts as supported only when one of these shows it:
  - an existing connection of that type in this account (`list_connections` returns
    `connection_type`), whose warehouse type is then known; or
  - the Monte Carlo docs page for that integration, read in this session, saying it connects
    through a collection agent with self-hosted credentials.

  Otherwise tell the customer support is unconfirmed. When the route **reuses** an existing
  deployment, it can proceed: `create_warehouse(connection_type=<type>)` refuses a type it cannot
  map and creates nothing, so that call is the check; on a refusal, hand off to the UI. When the
  route needs a **new** deployment or agent, NEVER provision it for an unconfirmed type; offer the
  UI instead. NEVER create a warehouse or connection only to probe support.
- **CRITICAL: the options above are the whole menu.** Offer them in customer language (for
  example "a file on your machine that a command you run reads", "a secret in your AWS Secrets
  Manager, by its name or ARN"). NEVER offer, accept or suggest typing a password, key or token
  into the chat, and NEVER offer to read one from a file, a secret store or anywhere else.
- **IMPORTANT: the credential choice can decide the deployment.** A self-hosted reference needs a
  collection agent; a secret file on the customer's machine means Monte Carlo-managed credentials,
  which only managed types have. Say which deployment an answer implies instead of asking the
  deployment question separately, and ask it only when both fit.
- **IMPORTANT: only some agent routes need no local Monte Carlo command.** When the customer
  wants to finish in the chat, or cannot run mc-cli or Terraform, recommend a collection agent
  with a self-hosted reference only when every remaining setup operation of that route is an MCP
  tool: reusing an enabled agent that fits, or a new AWS agent (registration is an MCP tool; the
  customer can deploy the stack with the CloudFormation template instead of the Terraform
  module). A new GCP or Azure agent (registration carries the agent's credentials) and a new
  Generic agent (its token or OAuth client is minted by an mc-cli or Terraform step) still need
  one. Check the whole route before recommending it. When none fits, hand the step off to the UI
  or to a teammate or admin who can run mc-cli or Terraform; NEVER create a deployment the
  customer cannot finish. Their own infrastructure step (deploying the agent, storing the secret)
  still runs on their side.
- NEVER provision a deployment or agent for an integration before it passes this check. An agent
  built for an unsupported type is a deployment with nothing behind it (SKILL.md rule 3).

## Deployment inputs

| Path | Required | Source and checks |
|---|---|---|
| Any | Target Monte Carlo account and environment | `get_current_user`. The artifact's credentials (CLI profile, provider `profile`, SDK env) must reach this same account: compare the account the customer's profile resolves to before carrying discovered ids into an artifact. |
| Reuse | `deployment_id` | Discovery (Step 1a). |
| AWS agent | Region | Customer or existing infrastructure. |
| AWS agent | Collection AWS account ID | Account information → Collection → AWS account ID, read by the customer. NEVER the AWS account the agent is deployed into. If both are equal, stop and re-check: registration then fails after several minutes with "Could not connect to Agent" because Monte Carlo is denied `sts:AssumeRole`. |
| AWS agent | External ID | `get_deployment` → `aws_external_id` (Step 1b). |
| AWS agent, private warehouse | Subnets that route to the warehouse | Customer. |
| GCP / Azure / Generic agent | The module or guide's required inputs | The linked module or official guide; ask for each one it marks required. |
| AWS data store | Region, bucket name | Customer; the bucket is created by the customer's step. |

## Credential inputs by path

### Monte Carlo-managed credentials

The inputs of a managed type are the parameters of its create operation: the flags of
`montecarlo credentials create <type> --help`, or the arguments of the Terraform resource
`montecarlo_<type>_credentials`. The secret fields are the ones with a `--<field>-prompt` flag in
the CLI and a `<field>_wo` argument in Terraform.

- **CRITICAL: a secret field is NEVER written as a literal value.** In the CLI it is `@<path>` (read
  from a file) or `--<field>-prompt` (hidden prompt); a literal is visible in the process list and
  shell history. In Terraform it is the `<field>_wo` argument (SKILL.md rule 7).
- Every other field follows the rules above: from the customer or discovery, never a default.

The Snowflake key pair below is the worked example; other managed types follow the same pattern.

#### Example: Snowflake key pair

| Input | Required | Notes |
|---|---|---|
| `account` | yes | The customer's Snowflake account identifier (`<locator>.<region>` or `<org>-<account>`). `SELECT CURRENT_ACCOUNT(), CURRENT_REGION();` confirms it. |
| `user` | yes | The Snowflake user **the public key is set on**. Snowflake rejects any other user with `JWT token is invalid`. The customer can compare `DESC USER <user>` → `RSA_PUBLIC_KEY_FP` with the key file's fingerprint locally. |
| Private key | yes | A file path on the customer's machine, PEM with BEGIN/END lines. Never its contents, and never open the file to check it: the customer's command reads it. |
| `warehouse` | **in practice** | API-optional. Without it, queries fail with "No active warehouse selected" unless the user has a default warehouse. Ask for it. |
| Passphrase | only for an encrypted key | Ask whether the key is encrypted; the passphrase itself stays with the customer (environment variable or prompt). |

The user also needs the grants from https://docs.getmontecarlo.com/docs/snowflake, including
`IMPORTED PRIVILEGES` on the `SNOWFLAKE` database for query logs. Confirm the grants script ran for
this user and warehouse.

### Self-hosted reference (the customer keeps the secret)

| Store | Required | Optional |
|---|---|---|
| AWS Secrets Manager | `connection_type`, `aws_secret` | `aws_region`, `assumable_role`, `external_id` |
| GCP Secret Manager | `connection_type`, `gcp_secret` | |
| Azure Key Vault | `connection_type`, `akv_secret`, and `akv_vault_name` or `akv_vault_url` | |
| Environment variable on the agent | `connection_type`, `env_var_name` | `kms_key_id` |
| File on the agent | `connection_type`, `file_path` | |

Add `bq_project_id` for BigQuery and `databricks_warehouse_id` for Databricks where the operation
takes them. Then confirm the **secret's contents** carry every key the connection type needs,
below. The customer checks; do not ask to see the secret.

### Required keys inside a self-hosted secret

From https://docs.getmontecarlo.com/docs/self-hosted-credentials; if the page and this table
disagree, the page is right. Keys sit inside `connect_args` unless noted.

| Connection type | Required | Optional or conditional |
|---|---|---|
| Snowflake | `user`, `private_key` (decrypted PKCS#8 body, no BEGIN/END lines), `account` | `warehouse` (**in practice**, as above) |
| BigQuery | `type`, `project_id`, `private_key_id`, `private_key`, `client_email`, `client_id`, `auth_uri`, `token_uri`, `auth_provider_x509_cert_url`, `client_x509_cert_url` (the service-account key file) | also pass `bq_project_id` on the credential |
| Databricks | the page marks no key required; ask which auth method the customer uses and confirm its keys: `databricks_workspace_url` with `databricks_token`, or with `databricks_client_id` + `databricks_client_secret` (plus `azure_tenant_id`, `azure_workspace_resource_id` on Azure) | the SQL warehouse id goes on the credential, not in the secret |
| Redshift | `host`, `dbname`, `port`, `user`, `password` | `autocommit` |
| Postgres | `dbname`, `user`, `password`, `host`, `port` | |
| MySQL | `host`, `port`, `user`, `password` | none: MySQL has no `database` key; schemas are discovered |
| SQL Server, Azure SQL Database, Azure Dedicated SQL Pool | `connect_args` (a connection string) | `login_timeout`, `query_timeout` (`query_timeout_in_seconds` for SQL Server) |
| Oracle | `dsn`, `user`, `password` | `ssl_options` |
| DB2 | `hostname`, `port`, `database`, `uid`, `pwd` | `ssl_options.ca_data` |
| SAP HANA | `address`, `port`, `user`, `password`, `databaseName` | |
| Teradata | `host`, `user`, `password`, `dbs_port`, `tmode`, `sslmode`, `logmech` | `request_timeout`, `logon_timeout`, `ssl_options` |
| ClickHouse | `host`, `port`, `username`, `password`, `database` | |
| Microsoft Fabric | `server`, `database`, `tenant_id`, `client_id`, `client_secret` | `port` |
| Starburst Enterprise | `host`, `port`, `user`, `password` | `ssl_options` |
| Starburst Galaxy | `host`, `user`, `password` | `port`, `catalog` |
| Dremio | `token` (top level), `connect_args.location` | |
| Motherduck | `connect_args` (`md:<database>?motherduck_token=<token>`) | |
| Salesforce CRM | token auth: `user`, `password`, `security_token`; or OAuth: `consumer_key`, `consumer_secret`, `domain` | |
| Salesforce Data Cloud | `domain`, `client_id`, `client_secret` | |
| Fivetran | `fivetran_api_key`, `fivetran_api_password` | |
| Informatica | `username`, `password`, `base_url` | |
| Looker | `client_id`, `client_secret`, `base_url` (top level) | |
| Looker Git | `repo_url`, `ssh_key` (top level) | |
| Power BI | `client_id`, `client_secret`, `tenant_id` (top level) | |
| Tableau | `username`, `client_id`, `secret_id`, `secret_value`, `server_name` (top level) | `site_name`, `verify_ssl`, `token_expiration_seconds` |

BI tools in this table (Looker, Looker Git, Power BI, Tableau) are not created by the onboarding
tools: `create_warehouse` has no BI type, and `list_connections` doesn't show BI connections. They
are connected in the UI; their rows list what a self-hosted secret for them holds.

For a type not listed, read its section on that page and apply the same rule before continuing.

## Warehouse and connection inputs

| Resource | Required | Source |
|---|---|---|
| Warehouse | `name`, `deployment_id`, and exactly one of `type` / `connection_type` | Name from the customer or an existing warehouse; never reuse a different target's warehouse because the type matches. |
| Connection | `name`, `warehouse_id`, `credentials_id` | Name from the customer; ids from the earlier steps. |

## Common mistakes

- Emitting `user = "MONTE_CARLO"` and `warehouse = "MONTE_CARLO_WH"` because the example shows
  them. The connection is created, then validation fails: `JWT token is invalid` for the user,
  "No active warehouse selected" for the warehouse.
- Setting the Collection AWS account ID to the account the agent runs in.
- Writing a Terraform variable with an example `default`, so `plan` never asks for the real value.
- Discovering over one Monte Carlo account and generating an artifact whose profile reaches another.
- Treating a secret reference as complete without confirming the secret carries the type's keys.
- Asking about deployments or credentials before checking the integration is supported, then
  discovering after an agent is provisioned that the type is UI-only on the chosen route.
- Telling the customer a type is unsupported (or supported) from memory instead of from this
  session's `create_warehouse` schema and managed credential tools.
- Writing a managed secret as a literal CLI value instead of `@<path>` or `--<field>-prompt`.
- Creating one deployment per integration when several fit the same one.
- Creating a second connection to an account or host that is already connected, on any
  deployment, without saying so: the same data is collected twice.
- Validating a self-hosted reference before the agent's read grant on the secret is applied: it
  only fails, and looks like a bad secret.
- Treating a failed **Tables** check on a database the customer just created as missing grants:
  an empty database fails it too. Ask whether it has tables yet.
