# `etl-containers` tools

<!-- Rendered from the REST API v2 OpenAPI document by api-codegen; do not edit. -->

Monte Carlo REST API v2 tools of the `etl-containers` tag, as the Monte Carlo MCP server exposes
them. Each section is one tool; its name is the tool to call.

## `list_etl_containers`: List ETL containers

List every ETL container in your account, oldest first.

The list includes synthetic containers, which this API does not create or delete.

- **Effect:** read-only.
- **Pairs with:** `create_etl_container`, `get_etl_container`.

### Arguments

None.

### Response

Returns `items`. Response fields per item: id, type, name, is_synthetic, deployment_id, deployment_name, created_time.

| Field | Description |
|---|---|
| `id` | Unique identifier of the ETL container. |
| `type` | The ETL tool the container represents. Fixed once created. |
| `name` | Display name of the ETL container. |
| `is_synthetic` | True for a container this API does not create or delete. Most belong to another connection, such as a warehouse or BI connection, and go away with it. |
| `deployment_id` | The deployment the container's connection runs through. Null for a type that runs on none, such as `airflow`. The id may name a deployment on Monte Carlo's older collection platform. The deployments endpoints do not list those. |
| `deployment_name` | Display name of the deployment. Null exactly when `deployment_id` is. |
| `created_time` | When the ETL container was created. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- An unexpected error prevented the request from being processed.

## `create_etl_container`: Create an ETL container

Create an empty ETL container for Airflow, Azure Data Factory, Fivetran, GCP Dataform, Informatica or MuleSoft, to add that tool's connection to. Takes the ETL tool as type, a name, and a deployment id. Every type except airflow needs the deployment id: call list_deployments first and pick the deployment the connection will run through, the cloud deployment Monte Carlo hosts for the account when the list shows one, or one with a collection agent already registered. Send no deployment id for airflow. Refused when a container of the same type already has the name, and for a second fivetran container on one deployment.

- **Effect:** creates; repeating it creates again.
- **Pairs with:** `list_etl_containers`, `get_etl_container`, `update_etl_container`, `delete_etl_container`, `list_deployments`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `type` | one of `airflow`, `azure-data-factory`, `fivetran`, `gcp-dataform`, `informatica-v2`, `mulesoft` | yes | The ETL tool the container represents. Its connection has to be for this tool. Cannot be changed after the container is created. |
| `name` | `str` | yes | Display name for the ETL container. No two containers of the same type can share a name. Between 1 and 200 characters. |
| `deployment_id` | `str` | no | The deployment the container's connection will run through. Pick one from the deployments list. Only a deployment on Monte Carlo's current collection platform is accepted. Required for every type except `airflow`, which takes none. |

### Response

Returns the new etl container. Response fields: id, type, name, is_synthetic, deployment_id, deployment_name, created_time.

| Field | Description |
|---|---|
| `id` | Unique identifier of the ETL container. |
| `type` | The ETL tool the container represents. Fixed once created. |
| `name` | Display name of the ETL container. |
| `is_synthetic` | True for a container this API does not create or delete. Most belong to another connection, such as a warehouse or BI connection, and go away with it. |
| `deployment_id` | The deployment the container's connection runs through. Null for a type that runs on none, such as `airflow`. The id may name a deployment on Monte Carlo's older collection platform. The deployments endpoints do not list those. |
| `deployment_name` | Display name of the deployment. Null exactly when `deployment_id` is. |
| `created_time` | When the ETL container was created. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The etl container does not exist, or is not visible to the caller.
- The change conflicts with the current state of the etl container.
- An argument is invalid; the error names the field.
- Monte Carlo is busy or temporarily unavailable; the tool retries once after the wait Monte Carlo asks for.
- An unexpected error prevented the request from being processed.

## `get_etl_container`: Get an ETL container

Get one ETL container.

An id that does not exist or belongs to another account returns 404.

- **Effect:** read-only.
- **Pairs with:** `list_etl_containers`, `create_etl_container`, `update_etl_container`, `delete_etl_container`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `etl_container_id` | `str` | yes | Id of the etl container, as returned by list_etl_containers. |

### Response

Response fields: id, type, name, is_synthetic, deployment_id, deployment_name, created_time.

| Field | Description |
|---|---|
| `id` | Unique identifier of the ETL container. |
| `type` | The ETL tool the container represents. Fixed once created. |
| `name` | Display name of the ETL container. |
| `is_synthetic` | True for a container this API does not create or delete. Most belong to another connection, such as a warehouse or BI connection, and go away with it. |
| `deployment_id` | The deployment the container's connection runs through. Null for a type that runs on none, such as `airflow`. The id may name a deployment on Monte Carlo's older collection platform. The deployments endpoints do not list those. |
| `deployment_name` | Display name of the deployment. Null exactly when `deployment_id` is. |
| `created_time` | When the ETL container was created. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The etl container does not exist, or is not visible to the caller.
- An unexpected error prevented the request from being processed.

## `update_etl_container`: Update an ETL container

Rename an ETL container. The name is the only field this takes; the type and the deployment are fixed once the container exists. Refused when another container of the same type already has the name.

- **Effect:** updates in place; idempotent.
- **Pairs with:** `list_etl_containers`, `create_etl_container`, `get_etl_container`, `delete_etl_container`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `etl_container_id` | `str` | yes | Id of the etl container, as returned by list_etl_containers. |
| `name` | `str` | no | New display name for the ETL container. Omit it to leave the name unchanged. An explicit null is ignored, the same as omitting the field. Between 1 and 200 characters. |

### Response

Returns the etl container after the change. Response fields: id, type, name, is_synthetic, deployment_id, deployment_name, created_time.

| Field | Description |
|---|---|
| `id` | Unique identifier of the ETL container. |
| `type` | The ETL tool the container represents. Fixed once created. |
| `name` | Display name of the ETL container. |
| `is_synthetic` | True for a container this API does not create or delete. Most belong to another connection, such as a warehouse or BI connection, and go away with it. |
| `deployment_id` | The deployment the container's connection runs through. Null for a type that runs on none, such as `airflow`. The id may name a deployment on Monte Carlo's older collection platform. The deployments endpoints do not list those. |
| `deployment_name` | Display name of the deployment. Null exactly when `deployment_id` is. |
| `created_time` | When the ETL container was created. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The etl container does not exist, or is not visible to the caller.
- The change conflicts with the current state of the etl container.
- An argument is invalid; the error names the field.
- Monte Carlo is busy or temporarily unavailable; the tool retries once after the wait Monte Carlo asks for.
- An unexpected error prevented the request from being processed.

## `delete_etl_container`: Delete an ETL container

Delete an empty ETL container. Refused while it still has a connection, and for a synthetic container, which this API does not delete.

- **Effect:** deletes; destructive and idempotent.
- **Pairs with:** `list_etl_containers`, `create_etl_container`, `get_etl_container`, `update_etl_container`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `etl_container_id` | `str` | yes | Id of the etl container, as returned by list_etl_containers. |

### Response

Returns `etl_container_id` and `deleted: true` once the etl container is gone.

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The etl container does not exist, or is not visible to the caller.
- The change conflicts with the current state of the etl container.
- Monte Carlo is busy or temporarily unavailable; try again after a moment.
- An unexpected error prevented the request from being processed.
