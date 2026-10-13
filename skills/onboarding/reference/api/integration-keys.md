# `integration-keys` tools

<!-- Rendered from the REST API v2 OpenAPI document by api-codegen; do not edit. -->

Monte Carlo REST API v2 tools of the `integration-keys` tag, as the Monte Carlo MCP server exposes
them. Each section is one tool; its name is the tool to call.

## `list_integration_keys`: List integration keys

List your account's ingestion and Airflow callbacks keys.

No secret is part of the list. Keys are sorted oldest first.

The list is not paged. A warehouse or container holds a key or two in normal use.

- **Effect:** read-only.
- **Pairs with:** `get_airflow_callbacks_key`, `get_ingestion_key`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `scope` | one of `INGESTION`, `AIRFLOW_CALLBACKS` | no | Only keys of this scope. |
| `parent_id` | `str` | no | Only keys scoped to this warehouse, BI container or ETL container. |

### Response

Returns `items`. Response fields per item: id, description, created_time, scope, warehouse_id, bi_container_id, etl_container_id.

| Field | Description |
|---|---|
| `id` | Unique identifier of the key. |
| `description` | What this key is for. |
| `created_time` | When the key was created. |
| `scope` | What the key lets its holder do. |
| `warehouse_id` | The warehouse the key is scoped to, if it is scoped to one. |
| `bi_container_id` | The BI container the key is scoped to, if it is scoped to one. |
| `etl_container_id` | The ETL container the key is scoped to, if it is scoped to one. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- An unexpected error prevented the request from being processed.

## `get_airflow_callbacks_key`: Get an Airflow callbacks key

Get one Airflow callbacks key. The secret is not part of it.

An id that names a key of another scope, or no key in your account, returns 404.

- **Effect:** read-only.
- **Pairs with:** `delete_airflow_callbacks_key`, `list_integration_keys`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `key_id` | `str` | yes | Id of the integration key, as returned when it is created or listed. |

### Response

Response fields: id, description, created_time, etl_container_id, mcd_id.

| Field | Description |
|---|---|
| `id` | Unique identifier of the key. |
| `description` | What this key is for. |
| `created_time` | When the key was created. |
| `etl_container_id` | The Airflow ETL container the key reports to. Null when the key names no warehouse or container, several of them, or one you cannot see. A key created outside this API with no scope at all is accepted for any of your account's resources, so replace it with a scoped one. |
| `mcd_id` | Key id to present, as the `x-mcd-id` header or a client's `mcd_id` setting. The same value as `id`. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The key does not exist, or is not visible to the caller.
- An unexpected error prevented the request from being processed.

## `delete_airflow_callbacks_key`: Delete an Airflow callbacks key

Delete an Airflow callbacks key. An Airflow environment still reporting with it is refused from then on.

- **Effect:** deletes; destructive and idempotent.
- **Pairs with:** `get_airflow_callbacks_key`, `list_integration_keys`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `key_id` | `str` | yes | Id of the integration key, as returned when it is created or listed. |

### Response

Returns `key_id` and `deleted: true` once the key is gone.

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- Monte Carlo is busy or temporarily unavailable; try again after a moment.
- An unexpected error prevented the request from being processed.

## `get_ingestion_key`: Get an ingestion key

Get one ingestion key. The secret is not part of it.

An id that names a key of another scope, or no key in your account, returns 404.

- **Effect:** read-only.
- **Pairs with:** `delete_ingestion_key`, `list_integration_keys`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `key_id` | `str` | yes | Id of the integration key, as returned when it is created or listed. |

### Response

Response fields: id, description, created_time, warehouse_id, bi_container_id, etl_container_id, mcd_id.

| Field | Description |
|---|---|
| `id` | Unique identifier of the key. |
| `description` | What this key is for. |
| `created_time` | When the key was created. |
| `warehouse_id` | The warehouse the key pushes metadata, lineage and query logs to. Null when the key is scoped to a container. |
| `bi_container_id` | The BI container the key pushes BI assets to. Null when the key is scoped to something else. |
| `etl_container_id` | The ETL container the key pushes ETL jobs and runs to. Null when the key is scoped to something else. |
| `mcd_id` | Key id to present, as the `x-mcd-id` header or a client's `mcd_id` setting. The same value as `id`. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The key does not exist, or is not visible to the caller.
- An unexpected error prevented the request from being processed.

## `delete_ingestion_key`: Delete an ingestion key

Delete an ingestion key. Data pushed with it is refused from then on, so delete it only once whatever pushes with it has a new key.

- **Effect:** deletes; destructive and idempotent.
- **Pairs with:** `get_ingestion_key`, `list_integration_keys`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `key_id` | `str` | yes | Id of the integration key, as returned when it is created or listed. |

### Response

Returns `key_id` and `deleted: true` once the key is gone.

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- Monte Carlo is busy or temporarily unavailable; try again after a moment.
- An unexpected error prevented the request from being processed.
