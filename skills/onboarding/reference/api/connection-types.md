# `connection-types` tools

<!-- Rendered from the REST API v2 OpenAPI document by api-codegen; do not edit. -->

Monte Carlo REST API v2 tools of the `connection-types` tag, as the Monte Carlo MCP server exposes
them. Each section is one tool; its name is the tool to call.

## `list_connection_types`: List connection types

List the connection types this account can connect with these tools, and what each one takes. Call it before asking about deployments or credentials, to decide whether an integration can be connected here at all. A type that is not listed cannot be: hand the user off to the Monte Carlo app for it. Match what the user names against `name` and `connection_type`. Each entry gives the parent to reuse or create before create_connection: a warehouse of `warehouse_type` (create_warehouse), a BI container of `bi_container_type` (create_bi_container) or an ETL container of `etl_container_type` (create_etl_container). It says where the credentials can live. `self_hosted_credentials_storages` lists the stores the customer runs that can hold them, each referenced with create_<storage>_credentials, such as create_aws_secrets_manager_credentials. `mc_managed_credentials_operation` names the operation that stores them with Monte Carlo. When `mc_managed_credentials_secret` is true, that operation takes a secret and is not a tool here: the user runs it with the CLI or Terraform. A type with `credentials_required` false takes none. `requires_deployment` false means the parent takes no deployment, so there is no deployment to choose. `requires_one_of_connection_types` lists the connection the warehouse needs first. A custom type (`is_custom`) runs through the deployment of the agent that registered it: list_custom_connector_types gives that agent and deployment. Nothing here checks a particular deployment. create_connection still refuses one below the version a type needs.

- **Effect:** read-only.

### Arguments

None.

### Response

Returns `items`. Response fields per item: connection_type, name, parent, warehouse_type, bi_container_type, etl_container_type, credentials_required, mc_managed_credentials_operation, mc_managed_credentials_secret, self_hosted_credentials_storages, requires_deployment, requires_one_of_connection_types, job_types, is_custom.

| Field | Description |
|---|---|
| `connection_type` | The connection type. Credentials for it name this type, and the connection takes its type from them. |
| `name` | Display name of the connection type. |
| `parent` | What a connection of this type is added to. Create or reuse one first. |
| `warehouse_type` | The type of warehouse the connection goes on. Null unless `parent` is `warehouse`. |
| `bi_container_type` | The type of BI container the connection goes on. Null unless `parent` is `bi_container`. |
| `etl_container_type` | The type of ETL container the connection goes on. Null unless `parent` is `etl_container`. |
| `credentials_required` | Whether the connection needs credentials. False for a push-only type: its data is sent to Monte Carlo, and Monte Carlo reaches no system for it. |
| `mc_managed_credentials_operation` | The operation that stores this type's credentials with Monte Carlo. Null when Monte Carlo cannot store them. |
| `mc_managed_credentials_secret` | Whether storing the credentials with Monte Carlo sends a secret, such as a password or a private key. Null when Monte Carlo cannot store them. |
| `self_hosted_credentials_storages` | The stores you run that the credentials can be kept in, with Monte Carlo keeping only where they are. Empty when they cannot be. |
| `requires_deployment` | Whether the connection runs through its parent's deployment. False for a type that reports to Monte Carlo itself, such as Airflow, or whose data is pushed. |
| `requires_one_of_connection_types` | The warehouse needs a connection of one of these types before one of this type is added. Empty when it needs none. |
| `job_types` | The collection jobs a connection of this type can run. |
| `is_custom` | Whether a collection agent registered the type for your account. A custom type's connection runs through the deployment of that agent. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- An unexpected error prevented the request from being processed.
