# `bi-containers` tools

<!-- Rendered from the REST API v2 OpenAPI document by api-codegen; do not edit. -->

Monte Carlo REST API v2 tools of the `bi-containers` tag, as the Monte Carlo MCP server exposes
them. Each section is one tool; its name is the tool to call.

## `list_bi_containers`: List BI containers

List every BI container in your account, oldest first.

- **Effect:** read-only.
- **Pairs with:** `create_bi_container`, `get_bi_container`.

### Arguments

None.

### Response

Returns `items`. Response fields per item: id, type, name, deployment_id, deployment_name, created_time.

| Field | Description |
|---|---|
| `id` | Unique identifier of the BI container. |
| `type` | The BI tool the container represents. Fixed once created. |
| `name` | Display name of the BI container. Null for a container that was never named. |
| `deployment_id` | The deployment the container's connections run through. Null for a container with no deployment, such as a push-only custom BI connector's. The id may name a deployment on Monte Carlo's older collection platform. The deployments endpoints do not list those. |
| `deployment_name` | Display name of the deployment. Null exactly when `deployment_id` is. |
| `created_time` | When the BI container was created. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- An unexpected error prevented the request from being processed.

## `create_bi_container`: Create a BI container

Create an empty BI container, to add Looker, Tableau, Power BI or custom BI connector connections to. Call list_deployments first and pick the deployment its connections will run through: the cloud deployment Monte Carlo hosts for the account, when the list shows one, or one with a collection agent already registered. Takes the BI tool as type, a name, and the deployment id. One looker container holds both the Looker API connection and the LookML git connection. A custom-bi-connector container goes on the deployment of the agent that registered the connector, or on none for a push-only connector, whose BI assets the customer pushes.

- **Effect:** creates; repeating it creates again.
- **Pairs with:** `list_bi_containers`, `get_bi_container`, `update_bi_container`, `delete_bi_container`, `list_deployments`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `type` | one of `looker`, `tableau`, `power-bi`, `custom-bi-connector` | yes | The BI tool the container represents. Every connection added to it has to be for this tool. Cannot be changed after the container is created. |
| `name` | `str` | yes | Display name for the BI container. Between 1 and 200 characters. |
| `deployment_id` | `str` | no | The deployment the container's connections will run through. Pick one from the deployments list. Only a deployment on Monte Carlo's current collection platform is accepted. `custom-bi-connector` takes the deployment of the agent that registered the connector, or none for a push-only connector. Every other type requires one. |

### Response

Returns the new bi container. Response fields: id, type, name, deployment_id, deployment_name, created_time.

| Field | Description |
|---|---|
| `id` | Unique identifier of the BI container. |
| `type` | The BI tool the container represents. Fixed once created. |
| `name` | Display name of the BI container. Null for a container that was never named. |
| `deployment_id` | The deployment the container's connections run through. Null for a container with no deployment, such as a push-only custom BI connector's. The id may name a deployment on Monte Carlo's older collection platform. The deployments endpoints do not list those. |
| `deployment_name` | Display name of the deployment. Null exactly when `deployment_id` is. |
| `created_time` | When the BI container was created. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The bi container does not exist, or is not visible to the caller.
- The change conflicts with the current state of the bi container.
- An argument is invalid; the error names the field.
- Monte Carlo is busy or temporarily unavailable; the tool retries once after the wait Monte Carlo asks for.
- An unexpected error prevented the request from being processed.

## `get_bi_container`: Get a BI container

Get one BI container.

An id that does not exist or belongs to another account returns 404.

- **Effect:** read-only.
- **Pairs with:** `list_bi_containers`, `create_bi_container`, `update_bi_container`, `delete_bi_container`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `bi_container_id` | `str` | yes | Id of the bi container, as returned by list_bi_containers. |

### Response

Response fields: id, type, name, deployment_id, deployment_name, created_time.

| Field | Description |
|---|---|
| `id` | Unique identifier of the BI container. |
| `type` | The BI tool the container represents. Fixed once created. |
| `name` | Display name of the BI container. Null for a container that was never named. |
| `deployment_id` | The deployment the container's connections run through. Null for a container with no deployment, such as a push-only custom BI connector's. The id may name a deployment on Monte Carlo's older collection platform. The deployments endpoints do not list those. |
| `deployment_name` | Display name of the deployment. Null exactly when `deployment_id` is. |
| `created_time` | When the BI container was created. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The bi container does not exist, or is not visible to the caller.
- An unexpected error prevented the request from being processed.

## `update_bi_container`: Update a BI container

Rename a BI container. The name is the only field this takes; the type and the deployment are fixed once the container exists.

- **Effect:** updates in place; idempotent.
- **Pairs with:** `list_bi_containers`, `create_bi_container`, `get_bi_container`, `delete_bi_container`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `bi_container_id` | `str` | yes | Id of the bi container, as returned by list_bi_containers. |
| `name` | `str` | no | New display name for the BI container. Omit it to leave the name unchanged. An explicit null is ignored, the same as omitting the field. Between 1 and 200 characters. |

### Response

Returns the bi container after the change. Response fields: id, type, name, deployment_id, deployment_name, created_time.

| Field | Description |
|---|---|
| `id` | Unique identifier of the BI container. |
| `type` | The BI tool the container represents. Fixed once created. |
| `name` | Display name of the BI container. Null for a container that was never named. |
| `deployment_id` | The deployment the container's connections run through. Null for a container with no deployment, such as a push-only custom BI connector's. The id may name a deployment on Monte Carlo's older collection platform. The deployments endpoints do not list those. |
| `deployment_name` | Display name of the deployment. Null exactly when `deployment_id` is. |
| `created_time` | When the BI container was created. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The bi container does not exist, or is not visible to the caller.
- An argument is invalid; the error names the field.
- Monte Carlo is busy or temporarily unavailable; the tool retries once after the wait Monte Carlo asks for.
- An unexpected error prevented the request from being processed.

## `delete_bi_container`: Delete a BI container

Delete an empty BI container, along with the BI assets Monte Carlo collected through it. Refused while it still has connections.

- **Effect:** deletes; destructive and idempotent.
- **Pairs with:** `list_bi_containers`, `create_bi_container`, `get_bi_container`, `update_bi_container`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `bi_container_id` | `str` | yes | Id of the bi container, as returned by list_bi_containers. |

### Response

Returns `bi_container_id` and `deleted: true` once the bi container is gone.

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The bi container does not exist, or is not visible to the caller.
- The change conflicts with the current state of the bi container.
- Monte Carlo is busy or temporarily unavailable; try again after a moment.
- An unexpected error prevented the request from being processed.
