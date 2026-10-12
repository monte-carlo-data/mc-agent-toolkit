# `custom-connector-types` tools

<!-- Rendered from the REST API v2 OpenAPI document by api-codegen; do not edit. -->

Monte Carlo REST API v2 tools of the `custom-connector-types` tag, as the Monte Carlo MCP server exposes
them. Each section is one tool; its name is the tool to call.

## `list_custom_connector_types`: List custom connector types

List the custom connector types your collection agents registered, oldest first.

A type whose collection agent was removed outright is not listed.

- **Effect:** read-only.
- **Pairs with:** `get_custom_connector_type`, `list_collection_agents`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `asset_class` | one of `warehouse`, `etl`, `bi` | no | Only connector types of this asset class. |
| `collection_agent_id` | `str` | no | Only connector types this collection agent registered. |

### Response

Returns `items`. Response fields per item: id, name, asset_class, collection_agent_id, deployment_id, job_types, icon_url, terminology, capabilities, created_time, updated_time.

| Field | Description |
|---|---|
| `id` | Unique identifier of the custom connector type, used as a connection type. |
| `name` | Display name of the connector. Supplied by the collection agent that registered it, and not validated. |
| `asset_class` | What the connector connects to: a warehouse, an ETL tool or a BI tool. |
| `collection_agent_id` | The collection agent that registered the connector. It may name an agent the collection agents endpoints no longer list. |
| `deployment_id` | The deployment of the collection agent that registered the connector. Its connections run there. The id may name a deployment the deployments endpoints do not list. |
| `job_types` | The collection jobs the connector runs. |
| `icon_url` | Icon for the connector. Supplied by the collection agent, not validated, and never fetched by Monte Carlo. Null for a warehouse connector, or when none was supplied. |
| `terminology` | The connector's nouns for its tiers. Set only for an ETL connector. |
| `capabilities` | What the connector supports. Set only for a warehouse connector. |
| `created_time` | When the connector type was first registered. |
| `updated_time` | When the connector type was last registered. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- An argument is invalid; the error names the field.
- An unexpected error prevented the request from being processed.

## `get_custom_connector_type`: Get a custom connector type

Get one custom connector type.

An id that does not exist or belongs to another account returns 404.

- **Effect:** read-only.
- **Pairs with:** `list_custom_connector_types`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `custom_connector_type_id` | `str` | yes | Id of the custom connector type, as returned when it is listed. |

### Response

Response fields: id, name, asset_class, collection_agent_id, deployment_id, job_types, icon_url, terminology, capabilities, created_time, updated_time.

| Field | Description |
|---|---|
| `id` | Unique identifier of the custom connector type, used as a connection type. |
| `name` | Display name of the connector. Supplied by the collection agent that registered it, and not validated. |
| `asset_class` | What the connector connects to: a warehouse, an ETL tool or a BI tool. |
| `collection_agent_id` | The collection agent that registered the connector. It may name an agent the collection agents endpoints no longer list. |
| `deployment_id` | The deployment of the collection agent that registered the connector. Its connections run there. The id may name a deployment the deployments endpoints do not list. |
| `job_types` | The collection jobs the connector runs. |
| `icon_url` | Icon for the connector. Supplied by the collection agent, not validated, and never fetched by Monte Carlo. Null for a warehouse connector, or when none was supplied. |
| `terminology` | The connector's nouns for its tiers. Set only for an ETL connector. |
| `capabilities` | What the connector supports. Set only for a warehouse connector. |
| `created_time` | When the connector type was first registered. |
| `updated_time` | When the connector type was last registered. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The custom connector type does not exist, or is not visible to the caller.
- An unexpected error prevented the request from being processed.
