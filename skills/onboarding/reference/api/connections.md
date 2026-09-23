# `connections` tools

<!-- GENERATED STUB (YET-2891): api-codegen's `-mcp-reference` mode will replace this file whole from the
     REST API v2 OpenAPI document; do not hand-edit once that lands. Until then this stub lists the operations
     of the tag by `operationId`, which is the MCP tool name, with the arguments the spec declares. -->

Monte Carlo REST API v2 operations of the `connections` tag. Each heading is the tool name once the Monte Carlo MCP
server exposes it. Operations marked **not an MCP tool** are reachable through the CLI, Terraform or the SDK only,
because their request or response carries a secret.

## `list_connections`: List connections

List the connections in your account, a page at a time.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `warehouse_id` | `str` | no | Only list connections on this warehouse. |
| `cursor` | `str` | no | Position to continue from, as returned in `next_cursor` by the previous page. |
| `limit` | `int` | no | Maximum number of items to return, between 1 and 100. |
| `with_count` | `bool` | no | Whether to also return the total number of items across every page, in `count`. |

### Response

Returns `items`, `next_cursor`, `has_more`, `count`; one page per call.

## `create_connection`: Create a connection

Add a connection to a warehouse from credentials that already exist. Takes the name, the warehouse id and the credentials id; the connection type comes from the credentials. The connection runs through the warehouse's deployment, so call list_deployments and list_warehouses first and reuse a warehouse on the right deployment: the cloud deployment hosted by Monte Carlo, or one with a collection agent or data store registered. Create a deployment only for an agent or a data store, never one with nothing behind it. Credentials that reference a store you run are created from here with create_aws_secrets_manager_credentials, create_gcp_secret_manager_credentials, create_azure_key_vault_credentials, create_env_var_credentials or create_file_credentials. Credentials whose secret has to be sent in the request, such as a Snowflake key pair, are created with the CLI or Terraform, not from here.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `name` | `str` | yes | Display name for the connection. |
| `warehouse_id` | `str` | yes | The warehouse to add the connection to. |
| `credentials_id` | `str` | yes | The credentials the connection reads with. |
| `job_types` | `list[str]` | no | The jobs to run on this connection. |

### Response

Response fields: id, connection_type, name, warehouse_id, warehouse_name, deployment_id, deployment_name, credentials_id, credentials_storage_type, job_types, created_time.

## `get_connection`: Get a connection

Get one connection.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `connection_id` | `str` | yes | Id of the connection, as returned by list_connections. |

### Response

Response fields: id, connection_type, name, warehouse_id, warehouse_name, deployment_id, deployment_name, credentials_id, credentials_storage_type, job_types, created_time.

## `update_connection`: Update a connection

Rename a connection. The name is the only field this takes; the type, the warehouse and the credentials are fixed once the connection exists.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `connection_id` | `str` | yes | Id of the connection, as returned by list_connections. |
| `name` | `str` | no | New display name for the connection. |

### Response

Response fields: id, connection_type, name, warehouse_id, warehouse_name, deployment_id, deployment_name, credentials_id, credentials_storage_type, job_types, created_time.

## `delete_connection`: Delete a connection

Delete a connection. Its warehouse and its credentials are left in place, but its own schedules, monitors and rules are deleted with it. Refused when it is the warehouse's last connection and deleting it would also take monitors, rules or use cases that belong to the warehouse as a whole.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `connection_id` | `str` | yes | Id of the connection, as returned by list_connections. |

### Response

Returns the path id and `deleted: true`.
