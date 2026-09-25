# `collection-agents` tools

<!-- Rendered from the REST API v2 OpenAPI document by api-codegen; do not edit. -->

Monte Carlo REST API v2 tools of the `collection-agents` tag, as the Monte Carlo MCP server exposes
them. Each section is one tool; its name is the tool to call.

## `list_collection_agents`: List collection agents

List the collection agents in your account, on every platform.

Only agents on deployments running Monte Carlo's current collection platform are listed.
Agents on the older platform are managed separately and do not appear here.

Agents are sorted by name, ignoring case. Agents with no name come last.

- **Effect:** read-only.
- **Pairs with:** `register_aws_collection_agent`, `get_aws_collection_agent`, `get_azure_collection_agent`, `get_gcp_collection_agent`, `register_generic_collection_agent`, `get_generic_collection_agent_oauth_client`, `get_generic_collection_agent_token`, `get_generic_collection_agent`.

### Arguments

None.

### Response

Returns `items`. Response fields per item: id, name, deployment_id, authentication_type, enabled, created_time, last_updated_time, image_build, image_version, is_remote_upgradeable, platform, endpoint.

| Field | Description |
|---|---|
| `id` | Unique identifier of the collection agent. |
| `name` | Display name of the collection agent. Null when it has no name. |
| `deployment_id` | Identifier of the deployment this collection agent runs on. |
| `authentication_type` | How Monte Carlo authenticates when it calls the collection agent. Null for an agent that connects out instead, such as a generic one. |
| `enabled` | Whether Monte Carlo is using this collection agent. An agent Monte Carlo has not validated is not enabled, either because it has not been registered yet or because validation failed. |
| `created_time` | When the collection agent was created. That is when its deployment was provisioned, which is before you register the agent. |
| `last_updated_time` | When the collection agent was last changed. Registering it, renaming it, changing how Monte Carlo reaches it, and Monte Carlo picking up a new image version all update this. Null until any of those has happened. |
| `image_build` | Build of the image the collection agent is running. Null until Monte Carlo has contacted the agent. |
| `image_version` | Version of the image the collection agent is running. Null until Monte Carlo has contacted the agent. |
| `is_remote_upgradeable` | Whether Monte Carlo can update the collection agent's image for you. |
| `platform` | Where the collection agent runs. Use it to build the platform-specific path for any other operation on this agent. Null for an agent whose platform Monte Carlo has not recorded, and no platform-specific path can address one of those. |
| `endpoint` | Address Monte Carlo reaches the collection agent at, in whatever form its platform uses. On AWS that is the ARN of a Lambda function, on Azure the URL of a function app, and on GCP the URL of a Cloud Run service. Empty until the agent has been registered. Null for a generic or Snowflake agent, which connect to Monte Carlo rather than being reached. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- An unexpected error prevented the request from being processed.

## `register_aws_collection_agent`: Register an AWS collection agent

Register a collection agent you have deployed on AWS, completing the deployment it was provisioned for. Provision the deployment with create_deployment first, then deploy the agent in your AWS account. Needs the deployment's id, the agent's Lambda function ARN, and the ARN of the role Monte Carlo assumes to invoke it. The deployment's external id must already be in that role's trust policy.

- **Effect:** creates; repeating it creates again.
- **Pairs with:** `get_aws_collection_agent`, `update_aws_collection_agent`, `delete_aws_collection_agent`, `list_collection_agents`, `list_deployments`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `deployment_id` | `str` | yes | Deployment to register the collection agent on. It must already hold an unregistered AWS collection agent. |
| `lambda_function_arn` | `str` | yes | ARN of the Lambda function Monte Carlo should invoke. |
| `role_arn` | `str` | yes | ARN of the role Monte Carlo assumes to invoke the function. Its trust policy must already carry the deployment's external id. |
| `name` | `str` | no | Display name for the collection agent. Replaces the name it currently has. Up to 200 characters. |

### Response

Returns the new collection agent. Response fields: id, name, deployment_id, authentication_type, enabled, created_time, last_updated_time, image_build, image_version, is_remote_upgradeable, lambda_function_arn, external_id.

| Field | Description |
|---|---|
| `id` | Unique identifier of the collection agent. |
| `name` | Display name of the collection agent. Null when it has no name. |
| `deployment_id` | Identifier of the deployment this collection agent runs on. |
| `authentication_type` | How Monte Carlo authenticates when it calls the collection agent. Null for an agent that connects out instead, such as a generic one. |
| `enabled` | Whether Monte Carlo is using this collection agent. An agent Monte Carlo has not validated is not enabled, either because it has not been registered yet or because validation failed. |
| `created_time` | When the collection agent was created. That is when its deployment was provisioned, which is before you register the agent. |
| `last_updated_time` | When the collection agent was last changed. Registering it, renaming it, changing how Monte Carlo reaches it, and Monte Carlo picking up a new image version all update this. Null until any of those has happened. |
| `image_build` | Build of the image the collection agent is running. Null until Monte Carlo has contacted the agent. |
| `image_version` | Version of the image the collection agent is running. Null until Monte Carlo has contacted the agent. |
| `is_remote_upgradeable` | Whether Monte Carlo can update the collection agent's image for you. |
| `lambda_function_arn` | ARN of the Lambda function Monte Carlo invokes. Empty until the agent has been registered. |
| `external_id` | Value to supply in the trust policy of the role Monte Carlo assumes to invoke the function. Null until Monte Carlo has generated one, for a caller who is not permitted to register an agent, and if the value could not be read just now. Retry the request in that last case. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The collection agent does not exist, or is not visible to the caller.
- The change conflicts with the current state of the collection agent.
- An argument is invalid; the error names the field.
- Monte Carlo is busy or temporarily unavailable; the tool retries once after the wait Monte Carlo asks for.
- An unexpected error prevented the request from being processed.

## `get_aws_collection_agent`: Get an AWS collection agent

Get one collection agent running on AWS, including its external id.

An id that names an agent on another platform, or no agent in your account, returns 404.

- **Effect:** read-only.
- **Pairs with:** `register_aws_collection_agent`, `update_aws_collection_agent`, `delete_aws_collection_agent`, `list_collection_agents`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `collection_agent_id` | `str` | yes | Id of the collection agent, as returned by list_collection_agents. |

### Response

Response fields: id, name, deployment_id, authentication_type, enabled, created_time, last_updated_time, image_build, image_version, is_remote_upgradeable, lambda_function_arn, external_id.

| Field | Description |
|---|---|
| `id` | Unique identifier of the collection agent. |
| `name` | Display name of the collection agent. Null when it has no name. |
| `deployment_id` | Identifier of the deployment this collection agent runs on. |
| `authentication_type` | How Monte Carlo authenticates when it calls the collection agent. Null for an agent that connects out instead, such as a generic one. |
| `enabled` | Whether Monte Carlo is using this collection agent. An agent Monte Carlo has not validated is not enabled, either because it has not been registered yet or because validation failed. |
| `created_time` | When the collection agent was created. That is when its deployment was provisioned, which is before you register the agent. |
| `last_updated_time` | When the collection agent was last changed. Registering it, renaming it, changing how Monte Carlo reaches it, and Monte Carlo picking up a new image version all update this. Null until any of those has happened. |
| `image_build` | Build of the image the collection agent is running. Null until Monte Carlo has contacted the agent. |
| `image_version` | Version of the image the collection agent is running. Null until Monte Carlo has contacted the agent. |
| `is_remote_upgradeable` | Whether Monte Carlo can update the collection agent's image for you. |
| `lambda_function_arn` | ARN of the Lambda function Monte Carlo invokes. Empty until the agent has been registered. |
| `external_id` | Value to supply in the trust policy of the role Monte Carlo assumes to invoke the function. Null until Monte Carlo has generated one, for a caller who is not permitted to register an agent, and if the value could not be read just now. Retry the request in that last case. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The collection agent does not exist, or is not visible to the caller.
- An unexpected error prevented the request from being processed.

## `update_aws_collection_agent`: Update an AWS collection agent

Change the Lambda function, role or name of an AWS collection agent. Monte Carlo revalidates it and re-enables it if it was disabled. Changing only the name skips revalidation.

- **Effect:** updates in place; idempotent.
- **Pairs with:** `register_aws_collection_agent`, `get_aws_collection_agent`, `delete_aws_collection_agent`, `list_collection_agents`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `collection_agent_id` | `str` | yes | Id of the collection agent, as returned by list_collection_agents. |
| `lambda_function_arn` | `str` | no | ARN of the Lambda function Monte Carlo should invoke. |
| `role_arn` | `str` | no | ARN of the role Monte Carlo assumes to invoke the function. Its trust policy must already carry the deployment's external id. |
| `name` | `str` | no | Display name for the collection agent. Replaces the name it currently has. Up to 200 characters. |

### Response

Returns the collection agent after the change. Response fields: id, name, deployment_id, authentication_type, enabled, created_time, last_updated_time, image_build, image_version, is_remote_upgradeable, lambda_function_arn, external_id.

| Field | Description |
|---|---|
| `id` | Unique identifier of the collection agent. |
| `name` | Display name of the collection agent. Null when it has no name. |
| `deployment_id` | Identifier of the deployment this collection agent runs on. |
| `authentication_type` | How Monte Carlo authenticates when it calls the collection agent. Null for an agent that connects out instead, such as a generic one. |
| `enabled` | Whether Monte Carlo is using this collection agent. An agent Monte Carlo has not validated is not enabled, either because it has not been registered yet or because validation failed. |
| `created_time` | When the collection agent was created. That is when its deployment was provisioned, which is before you register the agent. |
| `last_updated_time` | When the collection agent was last changed. Registering it, renaming it, changing how Monte Carlo reaches it, and Monte Carlo picking up a new image version all update this. Null until any of those has happened. |
| `image_build` | Build of the image the collection agent is running. Null until Monte Carlo has contacted the agent. |
| `image_version` | Version of the image the collection agent is running. Null until Monte Carlo has contacted the agent. |
| `is_remote_upgradeable` | Whether Monte Carlo can update the collection agent's image for you. |
| `lambda_function_arn` | ARN of the Lambda function Monte Carlo invokes. Empty until the agent has been registered. |
| `external_id` | Value to supply in the trust policy of the role Monte Carlo assumes to invoke the function. Null until Monte Carlo has generated one, for a caller who is not permitted to register an agent, and if the value could not be read just now. Retry the request in that last case. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The collection agent does not exist, or is not visible to the caller.
- The change conflicts with the current state of the collection agent.
- An argument is invalid; the error names the field.
- Monte Carlo is busy or temporarily unavailable; the tool retries once after the wait Monte Carlo asks for.
- An unexpected error prevented the request from being processed.

## `delete_aws_collection_agent`: Delete an AWS collection agent

Deregister an AWS collection agent. The deployment is left without an agent and cannot take another one from here; to register a replacement, delete the deployment with delete_deployment and provision a new one with create_deployment.

- **Effect:** deletes; destructive and idempotent.
- **Pairs with:** `register_aws_collection_agent`, `get_aws_collection_agent`, `update_aws_collection_agent`, `list_collection_agents`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `collection_agent_id` | `str` | yes | Id of the collection agent, as returned by list_collection_agents. |

### Response

Returns `collection_agent_id` and `deleted: true` once the collection agent is gone.

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The collection agent does not exist, or is not visible to the caller.
- The change conflicts with the current state of the collection agent.
- Monte Carlo is busy or temporarily unavailable; try again after a moment.
- An unexpected error prevented the request from being processed.

## `get_azure_collection_agent`: Get an Azure collection agent

Get one collection agent running on Azure.

An id that names an agent on another platform, or no agent in your account, returns 404.

- **Effect:** read-only.
- **Pairs with:** `delete_azure_collection_agent`, `list_collection_agents`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `collection_agent_id` | `str` | yes | Id of the collection agent, as returned by list_collection_agents. |

### Response

Response fields: id, name, deployment_id, authentication_type, enabled, created_time, last_updated_time, image_build, image_version, is_remote_upgradeable, function_app_url.

| Field | Description |
|---|---|
| `id` | Unique identifier of the collection agent. |
| `name` | Display name of the collection agent. Null when it has no name. |
| `deployment_id` | Identifier of the deployment this collection agent runs on. |
| `authentication_type` | How Monte Carlo authenticates when it calls the collection agent. Null for an agent that connects out instead, such as a generic one. |
| `enabled` | Whether Monte Carlo is using this collection agent. An agent Monte Carlo has not validated is not enabled, either because it has not been registered yet or because validation failed. |
| `created_time` | When the collection agent was created. That is when its deployment was provisioned, which is before you register the agent. |
| `last_updated_time` | When the collection agent was last changed. Registering it, renaming it, changing how Monte Carlo reaches it, and Monte Carlo picking up a new image version all update this. Null until any of those has happened. |
| `image_build` | Build of the image the collection agent is running. Null until Monte Carlo has contacted the agent. |
| `image_version` | Version of the image the collection agent is running. Null until Monte Carlo has contacted the agent. |
| `is_remote_upgradeable` | Whether Monte Carlo can update the collection agent's image for you. |
| `function_app_url` | URL of the function app Monte Carlo calls. Empty until the agent has been registered. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The collection agent does not exist, or is not visible to the caller.
- An unexpected error prevented the request from being processed.

## `delete_azure_collection_agent`: Delete an Azure collection agent

Deregister an Azure collection agent. The deployment is left without an agent and cannot take another one from here; to register a replacement, delete the deployment with delete_deployment and provision a new one with create_deployment.

- **Effect:** deletes; destructive and idempotent.
- **Pairs with:** `get_azure_collection_agent`, `list_collection_agents`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `collection_agent_id` | `str` | yes | Id of the collection agent, as returned by list_collection_agents. |

### Response

Returns `collection_agent_id` and `deleted: true` once the collection agent is gone.

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The collection agent does not exist, or is not visible to the caller.
- The change conflicts with the current state of the collection agent.
- Monte Carlo is busy or temporarily unavailable; try again after a moment.
- An unexpected error prevented the request from being processed.

## `get_gcp_collection_agent`: Get a GCP collection agent

Get one collection agent running on GCP.

An id that names an agent on another platform, or no agent in your account, returns 404.

- **Effect:** read-only.
- **Pairs with:** `delete_gcp_collection_agent`, `list_collection_agents`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `collection_agent_id` | `str` | yes | Id of the collection agent, as returned by list_collection_agents. |

### Response

Response fields: id, name, deployment_id, authentication_type, enabled, created_time, last_updated_time, image_build, image_version, is_remote_upgradeable, cloud_run_url.

| Field | Description |
|---|---|
| `id` | Unique identifier of the collection agent. |
| `name` | Display name of the collection agent. Null when it has no name. |
| `deployment_id` | Identifier of the deployment this collection agent runs on. |
| `authentication_type` | How Monte Carlo authenticates when it calls the collection agent. Null for an agent that connects out instead, such as a generic one. |
| `enabled` | Whether Monte Carlo is using this collection agent. An agent Monte Carlo has not validated is not enabled, either because it has not been registered yet or because validation failed. |
| `created_time` | When the collection agent was created. That is when its deployment was provisioned, which is before you register the agent. |
| `last_updated_time` | When the collection agent was last changed. Registering it, renaming it, changing how Monte Carlo reaches it, and Monte Carlo picking up a new image version all update this. Null until any of those has happened. |
| `image_build` | Build of the image the collection agent is running. Null until Monte Carlo has contacted the agent. |
| `image_version` | Version of the image the collection agent is running. Null until Monte Carlo has contacted the agent. |
| `is_remote_upgradeable` | Whether Monte Carlo can update the collection agent's image for you. |
| `cloud_run_url` | URL of the Cloud Run service Monte Carlo calls. Empty until the agent has been registered. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The collection agent does not exist, or is not visible to the caller.
- An unexpected error prevented the request from being processed.

## `delete_gcp_collection_agent`: Delete a GCP collection agent

Deregister a GCP collection agent. The deployment is left without an agent and cannot take another one from here; to register a replacement, delete the deployment with delete_deployment and provision a new one with create_deployment.

- **Effect:** deletes; destructive and idempotent.
- **Pairs with:** `get_gcp_collection_agent`, `list_collection_agents`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `collection_agent_id` | `str` | yes | Id of the collection agent, as returned by list_collection_agents. |

### Response

Returns `collection_agent_id` and `deleted: true` once the collection agent is gone.

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The collection agent does not exist, or is not visible to the caller.
- The change conflicts with the current state of the collection agent.
- Monte Carlo is busy or temporarily unavailable; try again after a moment.
- An unexpected error prevented the request from being processed.

## `register_generic_collection_agent`: Register a generic collection agent

Enable the generic collection agent a deployment was provisioned for, once the agent is running and connected to Monte Carlo. Needs the deployment's id. Provision the deployment with create_deployment first. The token or OAuth client the agent starts with is created with the CLI or the API, not from here, because the response carries the secret; delete_generic_collection_agent_token and delete_generic_collection_agent_oauth_client remove one.

- **Effect:** creates; repeating it creates again.
- **Pairs with:** `get_generic_collection_agent`, `update_generic_collection_agent`, `delete_generic_collection_agent`, `list_collection_agents`, `list_deployments`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `deployment_id` | `str` | yes | Deployment whose generic collection agent to enable. It must have been provisioned for one, and the agent must be running with a credential created for this deployment. |
| `name` | `str` | no | Display name for the collection agent. Replaces the name it currently has. Up to 200 characters. |

### Response

Returns the new collection agent. Response fields: id, name, deployment_id, authentication_type, enabled, created_time, last_updated_time, image_build, image_version, is_remote_upgradeable.

| Field | Description |
|---|---|
| `id` | Unique identifier of the collection agent. |
| `name` | Display name of the collection agent. Null when it has no name. |
| `deployment_id` | Identifier of the deployment this collection agent runs on. |
| `authentication_type` | How Monte Carlo authenticates when it calls the collection agent. Null for an agent that connects out instead, such as a generic one. |
| `enabled` | Whether Monte Carlo is using this collection agent. An agent Monte Carlo has not validated is not enabled, either because it has not been registered yet or because validation failed. |
| `created_time` | When the collection agent was created. That is when its deployment was provisioned, which is before you register the agent. |
| `last_updated_time` | When the collection agent was last changed. Registering it, renaming it, changing how Monte Carlo reaches it, and Monte Carlo picking up a new image version all update this. Null until any of those has happened. |
| `image_build` | Build of the image the collection agent is running. Null until Monte Carlo has contacted the agent. |
| `image_version` | Version of the image the collection agent is running. Null until Monte Carlo has contacted the agent. |
| `is_remote_upgradeable` | Whether Monte Carlo can update the collection agent's image for you. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The collection agent does not exist, or is not visible to the caller.
- The change conflicts with the current state of the collection agent.
- An argument is invalid; the error names the field.
- Monte Carlo is busy or temporarily unavailable; the tool retries once after the wait Monte Carlo asks for.
- An unexpected error prevented the request from being processed.

## `list_generic_collection_agent_credentials`: List generic collection agent credentials

List the credentials your generic collection agents present, of both kinds.

No secret is part of the list. Credentials are sorted oldest first.

The list is not paged. A deployment holds a credential or two in normal use, so the list
stays short, but nothing caps how many you can create.

- **Effect:** read-only.
- **Pairs with:** `get_generic_collection_agent_oauth_client`, `get_generic_collection_agent_token`, `list_deployments`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `deployment_id` | `str` | no | Only the credentials of this deployment's agent. |

### Response

Returns `items`. Response fields per item: id, deployment_id, type, description, created_time, mcd_id, client_id, scopes, expiration_time.

| Field | Description |
|---|---|
| `id` | Unique identifier of the credential. For a token this is also its key id; for an OAuth client, its client id. |
| `deployment_id` | Identifier of the deployment whose agent presents this credential. |
| `type` | Which kind of credential this is. |
| `description` | What this credential is for. |
| `created_time` | When the credential was created. |
| `mcd_id` | Key id the agent presents. Set for a `TOKEN`, null otherwise. |
| `client_id` | Client id the agent presents. Set for an `OAUTH_CLIENT`, null otherwise. |
| `scopes` | OAuth scopes the client is granted. Set for an `OAUTH_CLIENT`, null otherwise. |
| `expiration_time` | When an `OAUTH_CLIENT` stops being accepted. Null for one that does not expire, and for a `TOKEN`. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- An unexpected error prevented the request from being processed.

## `get_generic_collection_agent_oauth_client`: Get a generic collection agent OAuth client

Get one OAuth client. The secret is not part of it.

An id that names another kind of credential, or no credential in your account, returns 404.

- **Effect:** read-only.
- **Pairs with:** `delete_generic_collection_agent_oauth_client`, `list_generic_collection_agent_credentials`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credential_id` | `str` | yes | Id of the credential, as returned by list_generic_collection_agent_credentials. |

### Response

Response fields: id, deployment_id, type, description, created_time, client_id, scopes, expiration_time.

| Field | Description |
|---|---|
| `id` | Unique identifier of the credential. For a token this is also its key id; for an OAuth client, its client id. |
| `deployment_id` | Identifier of the deployment whose agent presents this credential. |
| `type` | Which kind of credential this is. |
| `description` | What this credential is for. |
| `created_time` | When the credential was created. |
| `client_id` | Client id the agent presents, as `client_id` in its configuration. The same value as `id`. |
| `scopes` | OAuth scopes the client is granted. |
| `expiration_time` | When the client stops being accepted. Null for a client that does not expire. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The credential does not exist, or is not visible to the caller.
- An unexpected error prevented the request from being processed.

## `delete_generic_collection_agent_oauth_client`: Delete a generic collection agent OAuth client

Delete an OAuth client a generic collection agent presents. An agent still running with it stops being able to get new access tokens; ones already issued last until they expire.

- **Effect:** deletes; destructive and idempotent.
- **Pairs with:** `get_generic_collection_agent_oauth_client`, `list_generic_collection_agent_credentials`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credential_id` | `str` | yes | Id of the credential, as returned by list_generic_collection_agent_credentials. |

### Response

Returns `credential_id` and `deleted: true` once the credential is gone.

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- Monte Carlo is busy or temporarily unavailable; try again after a moment.
- An unexpected error prevented the request from being processed.

## `get_generic_collection_agent_token`: Get a generic collection agent token

Get one token. The secret is not part of it.

An id that names another kind of credential, or no credential in your account, returns 404.

- **Effect:** read-only.
- **Pairs with:** `delete_generic_collection_agent_token`, `list_generic_collection_agent_credentials`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credential_id` | `str` | yes | Id of the credential, as returned by list_generic_collection_agent_credentials. |

### Response

Response fields: id, deployment_id, type, description, created_time, mcd_id.

| Field | Description |
|---|---|
| `id` | Unique identifier of the credential. For a token this is also its key id; for an OAuth client, its client id. |
| `deployment_id` | Identifier of the deployment whose agent presents this credential. |
| `type` | Which kind of credential this is. |
| `description` | What this credential is for. |
| `created_time` | When the credential was created. |
| `mcd_id` | Key id the agent presents, as `mcd_id` in its configuration. The same value as `id`. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The credential does not exist, or is not visible to the caller.
- An unexpected error prevented the request from being processed.

## `delete_generic_collection_agent_token`: Delete a generic collection agent token

Delete a token a generic collection agent presents. An agent still running with it stops being able to connect.

- **Effect:** deletes; destructive and idempotent.
- **Pairs with:** `get_generic_collection_agent_token`, `list_generic_collection_agent_credentials`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credential_id` | `str` | yes | Id of the credential, as returned by list_generic_collection_agent_credentials. |

### Response

Returns `credential_id` and `deleted: true` once the credential is gone.

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- Monte Carlo is busy or temporarily unavailable; try again after a moment.
- An unexpected error prevented the request from being processed.

## `get_generic_collection_agent`: Get a generic collection agent

Get one generic collection agent.

An id that names an agent on another platform, or no agent in your account, returns 404.

- **Effect:** read-only.
- **Pairs with:** `register_generic_collection_agent`, `update_generic_collection_agent`, `delete_generic_collection_agent`, `list_collection_agents`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `collection_agent_id` | `str` | yes | Id of the collection agent, as returned by list_collection_agents. |

### Response

Response fields: id, name, deployment_id, authentication_type, enabled, created_time, last_updated_time, image_build, image_version, is_remote_upgradeable.

| Field | Description |
|---|---|
| `id` | Unique identifier of the collection agent. |
| `name` | Display name of the collection agent. Null when it has no name. |
| `deployment_id` | Identifier of the deployment this collection agent runs on. |
| `authentication_type` | How Monte Carlo authenticates when it calls the collection agent. Null for an agent that connects out instead, such as a generic one. |
| `enabled` | Whether Monte Carlo is using this collection agent. An agent Monte Carlo has not validated is not enabled, either because it has not been registered yet or because validation failed. |
| `created_time` | When the collection agent was created. That is when its deployment was provisioned, which is before you register the agent. |
| `last_updated_time` | When the collection agent was last changed. Registering it, renaming it, changing how Monte Carlo reaches it, and Monte Carlo picking up a new image version all update this. Null until any of those has happened. |
| `image_build` | Build of the image the collection agent is running. Null until Monte Carlo has contacted the agent. |
| `image_version` | Version of the image the collection agent is running. Null until Monte Carlo has contacted the agent. |
| `is_remote_upgradeable` | Whether Monte Carlo can update the collection agent's image for you. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The collection agent does not exist, or is not visible to the caller.
- An unexpected error prevented the request from being processed.

## `update_generic_collection_agent`: Update a generic collection agent

Rename a generic collection agent. The name is the only field this takes.

- **Effect:** updates in place; idempotent.
- **Pairs with:** `register_generic_collection_agent`, `get_generic_collection_agent`, `delete_generic_collection_agent`, `list_collection_agents`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `collection_agent_id` | `str` | yes | Id of the collection agent, as returned by list_collection_agents. |
| `name` | `str` | no | Display name for the collection agent. Replaces the name it currently has. Up to 200 characters. |

### Response

Returns the collection agent after the change. Response fields: id, name, deployment_id, authentication_type, enabled, created_time, last_updated_time, image_build, image_version, is_remote_upgradeable.

| Field | Description |
|---|---|
| `id` | Unique identifier of the collection agent. |
| `name` | Display name of the collection agent. Null when it has no name. |
| `deployment_id` | Identifier of the deployment this collection agent runs on. |
| `authentication_type` | How Monte Carlo authenticates when it calls the collection agent. Null for an agent that connects out instead, such as a generic one. |
| `enabled` | Whether Monte Carlo is using this collection agent. An agent Monte Carlo has not validated is not enabled, either because it has not been registered yet or because validation failed. |
| `created_time` | When the collection agent was created. That is when its deployment was provisioned, which is before you register the agent. |
| `last_updated_time` | When the collection agent was last changed. Registering it, renaming it, changing how Monte Carlo reaches it, and Monte Carlo picking up a new image version all update this. Null until any of those has happened. |
| `image_build` | Build of the image the collection agent is running. Null until Monte Carlo has contacted the agent. |
| `image_version` | Version of the image the collection agent is running. Null until Monte Carlo has contacted the agent. |
| `is_remote_upgradeable` | Whether Monte Carlo can update the collection agent's image for you. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The collection agent does not exist, or is not visible to the caller.
- An argument is invalid; the error names the field.
- Monte Carlo is busy or temporarily unavailable; the tool retries once after the wait Monte Carlo asks for.
- An unexpected error prevented the request from being processed.

## `delete_generic_collection_agent`: Delete a generic collection agent

Deregister a generic collection agent, deleting the credentials created for its deployment. The deployment is left without an agent and cannot take another one from here; to register a replacement, delete the deployment with delete_deployment and provision a new one with create_deployment.

- **Effect:** deletes; destructive and idempotent.
- **Pairs with:** `register_generic_collection_agent`, `get_generic_collection_agent`, `update_generic_collection_agent`, `list_collection_agents`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `collection_agent_id` | `str` | yes | Id of the collection agent, as returned by list_collection_agents. |

### Response

Returns `collection_agent_id` and `deleted: true` once the collection agent is gone.

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The collection agent does not exist, or is not visible to the caller.
- The change conflicts with the current state of the collection agent.
- Monte Carlo is busy or temporarily unavailable; try again after a moment.
- An unexpected error prevented the request from being processed.
