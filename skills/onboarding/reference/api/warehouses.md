# `warehouses` tools

<!-- GENERATED STUB: api-codegen's `-mcp-reference` mode will replace this file whole from the
     REST API v2 OpenAPI document; do not hand-edit once that lands. Until then this copy is hand-filled
     from the live v2 tools the Monte Carlo MCP server already serves, so the onboarding skill can run. -->

Monte Carlo REST API v2 tools of the `warehouses` tag, as the Monte Carlo MCP server exposes
them. Each section is one tool; its name is the tool to call.

## `list_warehouses`: List warehouses

List the warehouses in your account, a page at a time.

Warehouses are returned oldest first. A caller whose asset access is restricted to
certain domains sees only the warehouses holding assets in those domains.

- **Effect:** read-only.
- **Pairs with:** `create_warehouse`, `get_warehouse`.
- **Paging:** one page per call; pass `next_cursor` back as `cursor` for the next page.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `cursor` | `str` | no | Position to continue from, as returned in `next_cursor` by the previous page. Omit it to start from the first page. The value is opaque; do not build or modify one. |
| `limit` | `int` | no | Maximum number of items to return, between 1 and 100. |
| `with_count` | `bool` | no | Whether to also return the total number of items across every page, in `count`. Off by default: counting costs an extra query. |

### Response

Returns `items` (response fields per item: id, name, type, deployment_id, created_time), `next_cursor` (pass it as `cursor` for the next page; null on the last page), `has_more`, and `count` (the total across pages, only when `with_count` is true).

| Field | Description |
|---|---|
| `id` | Unique identifier of the warehouse. |
| `name` | Display name of the warehouse. Null for a warehouse that was never named. |
| `type` | The kind of data platform the warehouse represents. Fixed once created. |
| `deployment_id` | The deployment the warehouse's connections run through. Null for a warehouse that has no deployment. The id may name a deployment on Monte Carlo's older collection platform. The deployments endpoints do not list those. |
| `created_time` | When the warehouse was created. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- An argument is invalid; the error names the field.
- An unexpected error prevented the request from being processed.

## `create_warehouse`: Create a warehouse

Create an empty warehouse on a deployment, to add connections to. Call list_deployments first and pick the deployment its connections will run through: the cloud deployment Monte Carlo hosts for the account, when the list shows one, or one with a collection agent or data store already registered. Create a new deployment with create_deployment only when the warehouse needs a collection agent inside your network or a data store on your side, never one with nothing behind it. Takes the name, the deployment id, and either the warehouse type or a connection type to derive it from.

- **Effect:** creates; repeating it creates again.
- **Pairs with:** `list_warehouses`, `get_warehouse`, `update_warehouse`, `delete_warehouse`, `list_deployments`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `name` | `str` | yes | Display name for the warehouse. Unique among your warehouses of the same type. Between 1 and 200 characters. |
| `deployment_id` | `str` | yes | The deployment the warehouse's connections will run through. Pick one from the deployments list. Only a deployment on Monte Carlo's current collection platform is accepted. |
| `type` | one of `bigquery`, `clickhouse`, `custom-connector`, `custom-integration`, `data-lake`, `db2`, `dremio`, `etl`, `microsoft-fabric`, `mysql`, `oracle`, `pinecone`, `redshift`, `s3-metadata-events`, `salesforce-crm`, `salesforce-data-cloud`, `snowflake`, `starburst-enterprise`, `starburst-galaxy`, `teradata`, `transactional-db` | no | The kind of data platform the warehouse represents. Every connection added to it has to fit. Cannot be changed after the warehouse is created. Send this or `connection_type`, not both. |
| `connection_type` | `str` | no | The type of the first connection you plan to add. The warehouse type is taken from it and returned as `type`. Send this or `type`, not both. A connection type no warehouse type can be taken from is refused, custom connectors included. So is one this account does not have. Between 1 and 200 characters. |

### Response

Returns the new warehouse. Response fields: id, name, type, deployment_id, created_time.

| Field | Description |
|---|---|
| `id` | Unique identifier of the warehouse. |
| `name` | Display name of the warehouse. Null for a warehouse that was never named. |
| `type` | The kind of data platform the warehouse represents. Fixed once created. |
| `deployment_id` | The deployment the warehouse's connections run through. Null for a warehouse that has no deployment. The id may name a deployment on Monte Carlo's older collection platform. The deployments endpoints do not list those. |
| `created_time` | When the warehouse was created. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The warehouse does not exist, or is not visible to the caller.
- The change conflicts with the current state of the warehouse.
- An argument is invalid; the error names the field.
- Monte Carlo is busy or temporarily unavailable; the tool retries once after the wait Monte Carlo asks for.
- An unexpected error prevented the request from being processed.

## `get_warehouse`: Get a warehouse

Get one warehouse.

An id that does not exist, belongs to another account, or names a warehouse your domain
restrictions hide from you returns 404.

- **Effect:** read-only.
- **Pairs with:** `list_warehouses`, `create_warehouse`, `update_warehouse`, `delete_warehouse`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `warehouse_id` | `str` | yes | Id of the warehouse, as returned by list_warehouses. |

### Response

Response fields: id, name, type, deployment_id, created_time.

| Field | Description |
|---|---|
| `id` | Unique identifier of the warehouse. |
| `name` | Display name of the warehouse. Null for a warehouse that was never named. |
| `type` | The kind of data platform the warehouse represents. Fixed once created. |
| `deployment_id` | The deployment the warehouse's connections run through. Null for a warehouse that has no deployment. The id may name a deployment on Monte Carlo's older collection platform. The deployments endpoints do not list those. |
| `created_time` | When the warehouse was created. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The warehouse does not exist, or is not visible to the caller.
- An unexpected error prevented the request from being processed.

## `update_warehouse`: Update a warehouse

Rename a warehouse. The name is the only field this takes; the type and the deployment are fixed once the warehouse exists.

- **Effect:** updates in place; idempotent.
- **Pairs with:** `list_warehouses`, `create_warehouse`, `get_warehouse`, `delete_warehouse`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `warehouse_id` | `str` | yes | Id of the warehouse, as returned by list_warehouses. |
| `name` | `str` | no | New display name for the warehouse. Omit it to leave the name unchanged. An explicit null is ignored, the same as omitting the field. Between 1 and 200 characters. |

### Response

Returns the warehouse after the change. Response fields: id, name, type, deployment_id, created_time.

| Field | Description |
|---|---|
| `id` | Unique identifier of the warehouse. |
| `name` | Display name of the warehouse. Null for a warehouse that was never named. |
| `type` | The kind of data platform the warehouse represents. Fixed once created. |
| `deployment_id` | The deployment the warehouse's connections run through. Null for a warehouse that has no deployment. The id may name a deployment on Monte Carlo's older collection platform. The deployments endpoints do not list those. |
| `created_time` | When the warehouse was created. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The warehouse does not exist, or is not visible to the caller.
- The change conflicts with the current state of the warehouse.
- An argument is invalid; the error names the field.
- Monte Carlo is busy or temporarily unavailable; the tool retries once after the wait Monte Carlo asks for.
- An unexpected error prevented the request from being processed.

## `delete_warehouse`: Delete a warehouse

Delete an empty warehouse. Refused while it still has connections, or while other warehouses consume from it.

- **Effect:** deletes; destructive and idempotent.
- **Pairs with:** `list_warehouses`, `create_warehouse`, `get_warehouse`, `update_warehouse`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `warehouse_id` | `str` | yes | Id of the warehouse, as returned by list_warehouses. |

### Response

Returns `warehouse_id` and `deleted: true` once the warehouse is gone.

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The warehouse does not exist, or is not visible to the caller.
- The change conflicts with the current state of the warehouse.
- Monte Carlo is busy or temporarily unavailable; try again after a moment.
- An unexpected error prevented the request from being processed.
