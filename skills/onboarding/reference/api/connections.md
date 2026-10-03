# `connections` tools

<!-- Rendered from the REST API v2 OpenAPI document by api-codegen; do not edit. -->

Monte Carlo REST API v2 tools of the `connections` tag, as the Monte Carlo MCP server exposes
them. Each section is one tool; its name is the tool to call.

## `list_connections`: List connections

List the connections in your account, a page at a time.

Connections are returned oldest first. Pass `warehouse_id` or `bi_container_id` to list
one warehouse's or one BI container's connections; an id you cannot see returns an empty
page. A caller whose asset access is restricted to certain domains sees only the
connections of warehouses holding assets in those domains, and every BI connection.

Connections that belong to an ETL integration are not listed here.

- **Effect:** read-only.
- **Pairs with:** `create_connection`, `get_connection`, `validate_connection`, `list_warehouses`, `list_bi_containers`.
- **Paging:** one page per call; pass `next_cursor` back as `cursor` for the next page.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `warehouse_id` | `str` | no | Only list connections on this warehouse. Omit it to list every connection in your account. |
| `bi_container_id` | `str` | no | Only list connections on this BI container. Omit it to list every connection in your account. |
| `cursor` | `str` | no | Position to continue from, as returned in `next_cursor` by the previous page. Omit it to start from the first page. The value is opaque; do not build or modify one. |
| `limit` | `int` | no | Maximum number of items to return, between 1 and 100. |
| `with_count` | `bool` | no | Whether to also return the total number of items across every page, in `count`. Off by default: counting costs an extra query. |

### Response

Returns `items` (response fields per item: id, connection_type, name, warehouse_id, warehouse_name, bi_container_id, bi_container_name, deployment_id, deployment_name, credentials_id, credentials_storage_type, job_types, created_time), `next_cursor` (pass it as `cursor` for the next page; null on the last page), `has_more`, and `count` (the total across pages, only when `with_count` is true).

| Field | Description |
|---|---|
| `id` | Unique identifier of the connection. |
| `connection_type` | What the connection reaches, such as `snowflake`. Taken from the credentials the connection was created with, and fixed once created. |
| `name` | Display name of the connection. Null for a connection that was never named. |
| `warehouse_id` | The warehouse the connection belongs to. Null for a connection on a BI container. Fixed once created. |
| `warehouse_name` | Display name of that warehouse. Null for a warehouse that was never named, and for a connection on a BI container. |
| `bi_container_id` | The BI container the connection belongs to. Null for a connection on a warehouse. Fixed once created. |
| `bi_container_name` | Display name of that BI container. Null for a container that was never named, and for a connection on a warehouse. |
| `deployment_id` | The deployment the connection runs through, taken from its warehouse or BI container. Null when that has no deployment. The id may name a deployment on Monte Carlo's older collection platform, which the deployments endpoints do not list. |
| `deployment_name` | Display name of that deployment. Null when there is no deployment to name. |
| `credentials_id` | The credentials the connection reads with. Null for a connection created before credentials became their own resource, and for one created outside this API. |
| `credentials_storage_type` | Where that secret lives. Null when there are no credentials to describe. |
| `job_types` | The jobs Monte Carlo runs on this connection, such as `metadata`. |
| `created_time` | When the connection was created. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- An argument is invalid; the error names the field.
- An unexpected error prevented the request from being processed.

## `create_connection`: Create a connection

Add a connection to a warehouse or a BI container from credentials that already exist. Takes the name, the credentials id, and either the warehouse id or, for Tableau, Looker or Power BI credentials, the BI container id from create_bi_container. The connection type comes from the credentials. The connection runs through its parent's deployment, so call list_deployments and list_warehouses or list_bi_containers first and reuse a parent on the right deployment: the cloud deployment hosted by Monte Carlo, or one with a collection agent or data store registered. Create a deployment only for an agent or a data store, never one with nothing behind it. Some types need another connection on the warehouse first. A databricks-sql-warehouse connection goes on a data-lake warehouse that already has a databricks-metastore-sql-warehouse connection, so add the metastore first. Credentials that reference a store you run are created from here with create_aws_secrets_manager_credentials, create_gcp_secret_manager_credentials, create_azure_key_vault_credentials, create_env_var_credentials or create_file_credentials. Credentials whose secret has to be sent in the request, such as a Snowflake key pair, a BigQuery service account key, a database password, a Databricks token or a BI tool's password or client secret, are created with the CLI or Terraform, not from here.

- **Effect:** creates; repeating it creates again.
- **Pairs with:** `list_connections`, `get_connection`, `update_connection`, `delete_connection`, `list_credentials`, `list_warehouses`, `list_bi_containers`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `name` | `str` | yes | Display name for the connection. Unique among the connections of its warehouse or BI container. Between 1 and 200 characters. |
| `credentials_id` | `str` | yes | The credentials the connection reads with. They also decide the connection's type. Create them first, through one of the credentials endpoints. |
| `warehouse_id` | `str` | no | The warehouse to add the connection to. Its type has to match what the credentials are for. Send this or `bi_container_id`, not both. |
| `bi_container_id` | `str` | no | The BI container to add the connection to, for Tableau, Looker or Power BI credentials. Its type has to match what the credentials are for: a `looker` container takes both `looker` and `looker-git-clone` credentials. Send this or `warehouse_id`, not both. |
| `job_types` | `list[str]` | no | The jobs to run on this connection. Omit it to run what the connection type runs by default, which is what the app does. Which values are accepted depends on the connection type. An empty list is not accepted; omit the field to take the defaults. At least 1 items. |

### Response

Returns the new connection. Response fields: id, connection_type, name, warehouse_id, warehouse_name, bi_container_id, bi_container_name, deployment_id, deployment_name, credentials_id, credentials_storage_type, job_types, created_time.

| Field | Description |
|---|---|
| `id` | Unique identifier of the connection. |
| `connection_type` | What the connection reaches, such as `snowflake`. Taken from the credentials the connection was created with, and fixed once created. |
| `name` | Display name of the connection. Null for a connection that was never named. |
| `warehouse_id` | The warehouse the connection belongs to. Null for a connection on a BI container. Fixed once created. |
| `warehouse_name` | Display name of that warehouse. Null for a warehouse that was never named, and for a connection on a BI container. |
| `bi_container_id` | The BI container the connection belongs to. Null for a connection on a warehouse. Fixed once created. |
| `bi_container_name` | Display name of that BI container. Null for a container that was never named, and for a connection on a warehouse. |
| `deployment_id` | The deployment the connection runs through, taken from its warehouse or BI container. Null when that has no deployment. The id may name a deployment on Monte Carlo's older collection platform, which the deployments endpoints do not list. |
| `deployment_name` | Display name of that deployment. Null when there is no deployment to name. |
| `credentials_id` | The credentials the connection reads with. Null for a connection created before credentials became their own resource, and for one created outside this API. |
| `credentials_storage_type` | Where that secret lives. Null when there are no credentials to describe. |
| `job_types` | The jobs Monte Carlo runs on this connection, such as `metadata`. |
| `created_time` | When the connection was created. |

### What can fail

- Authentication credentials are missing or invalid.
- The caller is not allowed to do this, or the account is paused.
- The connection does not exist, or is not visible to the caller.
- The change conflicts with the current state of the connection.
- An argument is invalid; the error names the field.
- Monte Carlo is busy or temporarily unavailable; the tool retries once after the wait Monte Carlo asks for.
- An unexpected error prevented the request from being processed.

## `get_connection`: Get a connection

Get one connection.

An id that does not exist, belongs to another account, or names a connection your domain
restrictions hide from you returns 404.

- **Effect:** read-only.
- **Pairs with:** `list_connections`, `create_connection`, `update_connection`, `delete_connection`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `connection_id` | `str` | yes | Id of the connection, as returned when it is created or listed. |

### Response

Response fields: id, connection_type, name, warehouse_id, warehouse_name, bi_container_id, bi_container_name, deployment_id, deployment_name, credentials_id, credentials_storage_type, job_types, created_time.

| Field | Description |
|---|---|
| `id` | Unique identifier of the connection. |
| `connection_type` | What the connection reaches, such as `snowflake`. Taken from the credentials the connection was created with, and fixed once created. |
| `name` | Display name of the connection. Null for a connection that was never named. |
| `warehouse_id` | The warehouse the connection belongs to. Null for a connection on a BI container. Fixed once created. |
| `warehouse_name` | Display name of that warehouse. Null for a warehouse that was never named, and for a connection on a BI container. |
| `bi_container_id` | The BI container the connection belongs to. Null for a connection on a warehouse. Fixed once created. |
| `bi_container_name` | Display name of that BI container. Null for a container that was never named, and for a connection on a warehouse. |
| `deployment_id` | The deployment the connection runs through, taken from its warehouse or BI container. Null when that has no deployment. The id may name a deployment on Monte Carlo's older collection platform, which the deployments endpoints do not list. |
| `deployment_name` | Display name of that deployment. Null when there is no deployment to name. |
| `credentials_id` | The credentials the connection reads with. Null for a connection created before credentials became their own resource, and for one created outside this API. |
| `credentials_storage_type` | Where that secret lives. Null when there are no credentials to describe. |
| `job_types` | The jobs Monte Carlo runs on this connection, such as `metadata`. |
| `created_time` | When the connection was created. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The connection does not exist, or is not visible to the caller.
- An unexpected error prevented the request from being processed.

## `update_connection`: Update a connection

Rename a connection. The name is the only field this takes; the type, the warehouse or BI container and the credentials are fixed once the connection exists.

- **Effect:** updates in place; idempotent.
- **Pairs with:** `list_connections`, `create_connection`, `get_connection`, `delete_connection`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `connection_id` | `str` | yes | Id of the connection, as returned when it is created or listed. |
| `name` | `str` | no | New display name for the connection. Omit it to leave the name unchanged. An explicit null is ignored, the same as omitting the field. Between 1 and 200 characters. |

### Response

Returns the connection after the change. Response fields: id, connection_type, name, warehouse_id, warehouse_name, bi_container_id, bi_container_name, deployment_id, deployment_name, credentials_id, credentials_storage_type, job_types, created_time.

| Field | Description |
|---|---|
| `id` | Unique identifier of the connection. |
| `connection_type` | What the connection reaches, such as `snowflake`. Taken from the credentials the connection was created with, and fixed once created. |
| `name` | Display name of the connection. Null for a connection that was never named. |
| `warehouse_id` | The warehouse the connection belongs to. Null for a connection on a BI container. Fixed once created. |
| `warehouse_name` | Display name of that warehouse. Null for a warehouse that was never named, and for a connection on a BI container. |
| `bi_container_id` | The BI container the connection belongs to. Null for a connection on a warehouse. Fixed once created. |
| `bi_container_name` | Display name of that BI container. Null for a container that was never named, and for a connection on a warehouse. |
| `deployment_id` | The deployment the connection runs through, taken from its warehouse or BI container. Null when that has no deployment. The id may name a deployment on Monte Carlo's older collection platform, which the deployments endpoints do not list. |
| `deployment_name` | Display name of that deployment. Null when there is no deployment to name. |
| `credentials_id` | The credentials the connection reads with. Null for a connection created before credentials became their own resource, and for one created outside this API. |
| `credentials_storage_type` | Where that secret lives. Null when there are no credentials to describe. |
| `job_types` | The jobs Monte Carlo runs on this connection, such as `metadata`. |
| `created_time` | When the connection was created. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The connection does not exist, or is not visible to the caller.
- The change conflicts with the current state of the connection.
- An argument is invalid; the error names the field.
- Monte Carlo is busy or temporarily unavailable; the tool retries once after the wait Monte Carlo asks for.
- An unexpected error prevented the request from being processed.

## `delete_connection`: Delete a connection

Delete a connection. Its warehouse or BI container and its credentials are left in place, but its own schedules, monitors and rules are deleted with it. Refused when it is the warehouse's last connection and deleting it would also take monitors, rules or use cases that belong to the warehouse as a whole, and for a custom BI connector, whose container would go with it.

- **Effect:** deletes; destructive and idempotent.
- **Pairs with:** `list_connections`, `create_connection`, `get_connection`, `update_connection`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `connection_id` | `str` | yes | Id of the connection, as returned when it is created or listed. |

### Response

Returns `connection_id` and `deleted: true` once the connection is gone.

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The connection does not exist, or is not visible to the caller.
- The change conflicts with the current state of the connection.
- Monte Carlo is busy or temporarily unavailable; try again after a moment.
- An unexpected error prevented the request from being processed.

## `validate_connection`: Validate a connection

Check whether an existing connection can still reach the system it reads from, using the credentials it already has. Changes nothing. Returns a run that is still going: poll `get_validation_run` with its id until the status is `completed`, then read each validation's own verdict.

- **Effect:** creates; repeating it creates again.
- **Pairs with:** `list_connections`.
- **Runs in the background:** the response is the accepted request; poll it to completion.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `connection_id` | `str` | yes | Id of the connection, as returned when it is created or listed. |

### Response

Returns the accepted request as-is. Response fields: id, status, revision, target_type, target_id, validations_passed, validations_total, started_at, finished_at, expires_at, validations.

| Field | Description |
|---|---|
| `id` | Identifier of the run. Poll `GET /validations/{run_id}` with it. |
| `status` | Whether the run is still going. Every validation is final once it is not. |
| `revision` | Moves forward every time a validation changes. Pass it as `since` on the next poll to get only the validations that changed after this response. |
| `target_type` | What the run validates. |
| `target_id` | Identifier of what is being validated. Null for candidate values, which are not stored anywhere. |
| `validations_passed` | How many validations reached a passing verdict. One that was skipped or never reached a verdict is not counted here, but is still in `validations_total`. |
| `validations_total` | How many validations the run covers. |
| `started_at` | When the run started. |
| `finished_at` | When the run finished. Null while it is still going. |
| `expires_at` | When the run stops being readable. Measured from the start, not the finish, and never extended, so a slow run is readable for less time after it ends. |
| `validations` | The run's validations, in the order they are declared. A validation stays `pending` until it starts. It can wait on a prerequisite, or for earlier validations to finish. A read with `since` lists only the validations that changed after that revision, and may list none. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The connection does not exist, or is not visible to the caller.
- The change conflicts with the current state of the connection.
- Monte Carlo is busy or temporarily unavailable; the tool retries once after the wait Monte Carlo asks for.
- An unexpected error prevented the request from being processed.
