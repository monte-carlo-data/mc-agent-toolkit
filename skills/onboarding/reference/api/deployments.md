# `deployments` tools

<!-- GENERATED STUB (YET-2891): api-codegen's `-mcp-reference` mode will replace this file whole from the
     REST API v2 OpenAPI document; do not hand-edit once that lands. Until then this copy is hand-filled
     from the ten v2 tools the Monte Carlo MCP server already serves, so the onboarding skill can run. -->

Monte Carlo REST API v2 tools of the `deployments` tag, as the Monte Carlo MCP server exposes
them. Each section is one tool; its name is the tool to call.

## `list_deployments`: List deployments

List the deployments in your account.

A deployment is the infrastructure that connects Monte Carlo to your environment. Each
one hosts a collection agent or a data store, or is hosted by Monte Carlo itself.

Only deployments on Monte Carlo's current collection platform are listed. Deployments on
the older platform are managed separately and do not appear here.

Deployments are sorted by name, ignoring case.

A deployment's external id is returned by the single-deployment read, not by this list.

- **Effect:** read-only.
- **Pairs with:** `create_deployment`, `get_deployment`.

### Arguments

None.

### Response

Returns `items`. Response fields per item: id, name, type, runtime_platform, enabled, created_time, last_updated_time.

| Field | Description |
|---|---|
| `id` | Unique identifier of the deployment. |
| `name` | Display name of the deployment. |
| `type` | What the deployment hosts. Null when nothing is provisioned on it, in which case it has to be provisioned before it can be used. |
| `runtime_platform` | Where the deployment's collection agent or data store runs. Null for a Monte Carlo hosted deployment, which runs neither, for one with nothing provisioned on it, and for one whose platform Monte Carlo has not recorded. |
| `enabled` | Whether the deployment can serve connections. A deployment still waiting for its collection agent or data store to be registered, or with nothing provisioned on it, is not enabled. |
| `created_time` | When the deployment was assigned to your account. Null when Monte Carlo has no record of that. |
| `last_updated_time` | When Monte Carlo last updated the infrastructure behind the deployment. Null when Monte Carlo has no record of an update. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- An unexpected error prevented the request from being processed.

## `create_deployment`: Create a deployment

Provision a deployment for a collection agent or a data store you will run in your own cloud. Call list_deployments first: it includes the cloud deployment Monte Carlo hosts for the account when it runs on the current collection platform, and this cannot create another one. Create a deployment only when a warehouse has to be reached from inside your network (a collection agent) or sampled rows have to stay in your storage (a data store). A deployment with nothing registered on it serves no connections, so never create one without an agent or data store to put on it. Takes the deployment type and the platform it will run on, and returns the external id when that platform needs one. Registering the agent or data store is a second call.

- **Effect:** creates; repeating it creates again.
- **Pairs with:** `list_deployments`, `get_deployment`, `update_deployment`, `delete_deployment`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `type` | one of `COLLECTION_AGENT`, `COLLECTION_DATA_STORE`, `CLOUD` | yes | What the deployment will host. Only `COLLECTION_AGENT` and `COLLECTION_DATA_STORE` can be provisioned today. Any other value is rejected. |
| `runtime_platform` | one of `AWS`, `AWS_PROXIED`, `AZURE`, `GCP`, `GCP_PROXIED`, `SNOWFLAKE`, `GENERIC` | yes | Where the deployment's collection agent or data store will run. Either can be provisioned on `AWS`, `AZURE` or `GCP`, and a collection agent also on `GENERIC`. Any other combination is rejected. |
| `name` | `str` | no | Display name for the deployment. Monte Carlo generates one if you leave it out. Up to 200 characters. |

### Response

Returns the new deployment. Response fields: id, name, type, runtime_platform, enabled, created_time, last_updated_time, aws_external_id.

| Field | Description |
|---|---|
| `id` | Unique identifier of the deployment. |
| `name` | Display name of the deployment. |
| `type` | What the deployment hosts. Null when nothing is provisioned on it, in which case it has to be provisioned before it can be used. |
| `runtime_platform` | Where the deployment's collection agent or data store runs. Null for a Monte Carlo hosted deployment, which runs neither, for one with nothing provisioned on it, and for one whose platform Monte Carlo has not recorded. |
| `enabled` | Whether the deployment can serve connections. A deployment still waiting for its collection agent or data store to be registered, or with nothing provisioned on it, is not enabled. |
| `created_time` | When the deployment was assigned to your account. Null when Monte Carlo has no record of that. |
| `last_updated_time` | When Monte Carlo last updated the infrastructure behind the deployment. Null when Monte Carlo has no record of an update. |
| `aws_external_id` | Value to supply when you register an AWS collection agent or data store on this deployment. It goes in the trust policy of the role Monte Carlo assumes. Null until Monte Carlo has generated one, for a deployment on another platform, for a caller who is not permitted to register one, and if the value could not be read just now. Retry the request in that last case. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The change conflicts with the current state of the deployment.
- An argument is invalid; the error names the field.
- Monte Carlo is busy or temporarily unavailable; the tool retries once after the wait Monte Carlo asks for.
- An unexpected error prevented the request from being processed.

## `get_deployment`: Get a deployment

Get one deployment. An AWS deployment includes the external id needed to register on it.

An id that does not exist, belongs to another account, or names a deployment on Monte
Carlo's older collection platform all return 404.

- **Effect:** read-only.
- **Pairs with:** `list_deployments`, `create_deployment`, `update_deployment`, `delete_deployment`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `deployment_id` | `str` | yes | Id of the deployment, as returned by list_deployments. |

### Response

Response fields: id, name, type, runtime_platform, enabled, created_time, last_updated_time, aws_external_id.

| Field | Description |
|---|---|
| `id` | Unique identifier of the deployment. |
| `name` | Display name of the deployment. |
| `type` | What the deployment hosts. Null when nothing is provisioned on it, in which case it has to be provisioned before it can be used. |
| `runtime_platform` | Where the deployment's collection agent or data store runs. Null for a Monte Carlo hosted deployment, which runs neither, for one with nothing provisioned on it, and for one whose platform Monte Carlo has not recorded. |
| `enabled` | Whether the deployment can serve connections. A deployment still waiting for its collection agent or data store to be registered, or with nothing provisioned on it, is not enabled. |
| `created_time` | When the deployment was assigned to your account. Null when Monte Carlo has no record of that. |
| `last_updated_time` | When Monte Carlo last updated the infrastructure behind the deployment. Null when Monte Carlo has no record of an update. |
| `aws_external_id` | Value to supply when you register an AWS collection agent or data store on this deployment. It goes in the trust policy of the role Monte Carlo assumes. Null until Monte Carlo has generated one, for a deployment on another platform, for a caller who is not permitted to register one, and if the value could not be read just now. Retry the request in that last case. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The deployment does not exist, or is not visible to the caller.
- An unexpected error prevented the request from being processed.

## `update_deployment`: Update a deployment

Rename a deployment. The name is the only field this takes. Nothing about the infrastructure behind the deployment changes.

- **Effect:** updates in place; idempotent.
- **Pairs with:** `list_deployments`, `create_deployment`, `get_deployment`, `delete_deployment`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `deployment_id` | `str` | yes | Id of the deployment, as returned by list_deployments. |
| `name` | `str` | no | New display name for the deployment. Left out, the name is unchanged. Between 1 and 200 characters. |

### Response

Returns the deployment after the change. Response fields: id, name, type, runtime_platform, enabled, created_time, last_updated_time, aws_external_id.

| Field | Description |
|---|---|
| `id` | Unique identifier of the deployment. |
| `name` | Display name of the deployment. |
| `type` | What the deployment hosts. Null when nothing is provisioned on it, in which case it has to be provisioned before it can be used. |
| `runtime_platform` | Where the deployment's collection agent or data store runs. Null for a Monte Carlo hosted deployment, which runs neither, for one with nothing provisioned on it, and for one whose platform Monte Carlo has not recorded. |
| `enabled` | Whether the deployment can serve connections. A deployment still waiting for its collection agent or data store to be registered, or with nothing provisioned on it, is not enabled. |
| `created_time` | When the deployment was assigned to your account. Null when Monte Carlo has no record of that. |
| `last_updated_time` | When Monte Carlo last updated the infrastructure behind the deployment. Null when Monte Carlo has no record of an update. |
| `aws_external_id` | Value to supply when you register an AWS collection agent or data store on this deployment. It goes in the trust policy of the role Monte Carlo assumes. Null until Monte Carlo has generated one, for a deployment on another platform, for a caller who is not permitted to register one, and if the value could not be read just now. Retry the request in that last case. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The deployment does not exist, or is not visible to the caller.
- An argument is invalid; the error names the field.
- Monte Carlo is busy or temporarily unavailable; the tool retries once after the wait Monte Carlo asks for.
- An unexpected error prevented the request from being processed.

## `delete_deployment`: Delete a deployment

Delete a deployment and release the infrastructure Monte Carlo runs for it. Refused while it has an enabled collection agent or data store, connections running through it, or objects in its storage. The cloud deployment hosted by Monte Carlo cannot be deleted.

- **Effect:** deletes; destructive and idempotent.
- **Pairs with:** `list_deployments`, `create_deployment`, `get_deployment`, `update_deployment`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `deployment_id` | `str` | yes | Id of the deployment, as returned by list_deployments. |

### Response

Returns `deployment_id` and `deleted: true` once the deployment is gone.

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The deployment does not exist, or is not visible to the caller.
- The change conflicts with the current state of the deployment.
- An unexpected error prevented the request from being processed.
- Monte Carlo is busy or temporarily unavailable; try again after a moment.
