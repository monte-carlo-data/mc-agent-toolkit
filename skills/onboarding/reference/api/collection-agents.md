# `collection-agents` tools

<!-- GENERATED STUB: api-codegen's `-mcp-reference` mode will replace this file whole from the
     REST API v2 OpenAPI document; do not hand-edit once that lands. Until then this stub lists the operations
     of the tag by `operationId`, which is the MCP tool name, with the arguments the spec declares. -->

Monte Carlo REST API v2 operations of the `collection-agents` tag. Each heading is the tool name once the Monte Carlo MCP
server exposes it. Operations marked **not an MCP tool** are reachable through the CLI, Terraform or the SDK only,
because their request or response carries a secret.

## `list_collection_agents`: List collection agents

List the collection agents in your account, on every platform.

### Arguments

None.

### Response

Returns `items`. Response fields per item: id, name, deployment_id, authentication_type, enabled, created_time, last_updated_time, image_build, image_version, is_remote_upgradeable, platform, endpoint.

## `get_aws_collection_agent`: Get an AWS collection agent

Get one collection agent running on AWS, including its external id.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `collection_agent_id` | `str` | yes | Id of the collection agent, as returned by list_collection_agents. |

### Response

Response fields: id, name, deployment_id, authentication_type, enabled, created_time, last_updated_time, image_build, image_version, is_remote_upgradeable, lambda_function_arn, external_id.

## `update_aws_collection_agent`: Update an AWS collection agent

Change the Lambda function, role or name of an AWS collection agent. Monte Carlo revalidates it and re-enables it if it was disabled. Changing only the name skips revalidation.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `collection_agent_id` | `str` | yes | Id of the collection agent, as returned by list_collection_agents. |
| `lambda_function_arn` | `str` | no | ARN of the Lambda function Monte Carlo should invoke. |
| `role_arn` | `str` | no | ARN of the role Monte Carlo assumes to invoke the function. |
| `name` | `str` | no | Display name for the collection agent. |

### Response

Response fields: id, name, deployment_id, authentication_type, enabled, created_time, last_updated_time, image_build, image_version, is_remote_upgradeable, lambda_function_arn, external_id.

## `delete_aws_collection_agent`: Delete an AWS collection agent

Deregister an AWS collection agent. The deployment is left without an agent and cannot take another one from here; to register a replacement, delete the deployment with delete_deployment and provision a new one with create_deployment.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `collection_agent_id` | `str` | yes | Id of the collection agent, as returned by list_collection_agents. |

### Response

Returns the path id and `deleted: true`.

## `register_aws_collection_agent`: Register an AWS collection agent

Register a collection agent you have deployed on AWS, completing the deployment it was provisioned for. Provision the deployment with create_deployment first, then deploy the agent in your AWS account. Needs the deployment's id, the agent's Lambda function ARN, and the ARN of the role Monte Carlo assumes to invoke it. The deployment's external id must already be in that role's trust policy.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `deployment_id` | `str` | yes | Deployment to register the collection agent on. |
| `lambda_function_arn` | `str` | yes | ARN of the Lambda function Monte Carlo should invoke. |
| `role_arn` | `str` | yes | ARN of the role Monte Carlo assumes to invoke the function. |
| `name` | `str` | no | Display name for the collection agent. |

### Response

Response fields: id, name, deployment_id, authentication_type, enabled, created_time, last_updated_time, image_build, image_version, is_remote_upgradeable, lambda_function_arn, external_id.

## `get_azure_collection_agent`: Get an Azure collection agent

Get one collection agent running on Azure.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `collection_agent_id` | `str` | yes | Id of the collection agent, as returned by list_collection_agents. |

### Response

Response fields: id, name, deployment_id, authentication_type, enabled, created_time, last_updated_time, image_build, image_version, is_remote_upgradeable, function_app_url.

## `update_azure_collection_agent`: Update an Azure collection agent

**Not an MCP tool.** Use the CLI, Terraform or the SDK.

Change the function app, credentials, authentication type or name of an Azure collection agent. Monte Carlo revalidates it and re-enables it if it was disabled. Changing only the name skips revalidation.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `collection_agent_id` | `str` | yes | Id of the collection agent, as returned by list_collection_agents. |
| `function_app_key` | object | no | Credentials for `AZURE_FUNCTION_APP_KEY`. |
| `service_principal` | object | no | Credentials for `AZURE_FUNCTION_SERVICE_PRINCIPAL`. |
| `function_app_url` | `str` | no | URL of the function app Monte Carlo should call. |
| `name` | `str` | no | Display name for the collection agent. |
| `authentication_type` | object | no | How Monte Carlo authenticates when it calls the agent. |

### Response

Response fields: id, name, deployment_id, authentication_type, enabled, created_time, last_updated_time, image_build, image_version, is_remote_upgradeable, function_app_url.

## `delete_azure_collection_agent`: Delete an Azure collection agent

Deregister an Azure collection agent. The deployment is left without an agent and cannot take another one from here; to register a replacement, delete the deployment with delete_deployment and provision a new one with create_deployment.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `collection_agent_id` | `str` | yes | Id of the collection agent, as returned by list_collection_agents. |

### Response

Returns the path id and `deleted: true`.

## `register_azure_collection_agent`: Register an Azure collection agent

**Not an MCP tool.** Use the CLI, Terraform or the SDK.

Register a collection agent you have deployed on Azure, completing the deployment it was provisioned for. Needs the deployment's id, the function app's URL, and either an app key or a service principal, named by authentication_type.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `function_app_key` | object | no | Credentials for `AZURE_FUNCTION_APP_KEY`. |
| `service_principal` | object | no | Credentials for `AZURE_FUNCTION_SERVICE_PRINCIPAL`. |
| `authentication_type` | one of `AZURE_FUNCTION_APP_KEY`, `AZURE_FUNCTION_SERVICE_PRINCIPAL` | yes | How Monte Carlo authenticates when it calls the agent. |
| `deployment_id` | `str` | yes | Deployment to register the collection agent on. |
| `function_app_url` | `str` | yes | URL of the function app Monte Carlo should call. |
| `name` | `str` | no | Display name for the collection agent. |

### Response

Response fields: id, name, deployment_id, authentication_type, enabled, created_time, last_updated_time, image_build, image_version, is_remote_upgradeable, function_app_url.

## `get_gcp_collection_agent`: Get a GCP collection agent

Get one collection agent running on GCP.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `collection_agent_id` | `str` | yes | Id of the collection agent, as returned by list_collection_agents. |

### Response

Response fields: id, name, deployment_id, authentication_type, enabled, created_time, last_updated_time, image_build, image_version, is_remote_upgradeable, cloud_run_url.

## `update_gcp_collection_agent`: Update a GCP collection agent

**Not an MCP tool.** Use the CLI, Terraform or the SDK.

Change the Cloud Run service, credentials, authentication type or name of a GCP collection agent. Monte Carlo revalidates it and re-enables it if it was disabled. Changing only the name skips revalidation.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `collection_agent_id` | `str` | yes | Id of the collection agent, as returned by list_collection_agents. |
| `service_account_key` | `str` | no | Credentials for `GCP_JSON_SERVICE_ACCOUNT_KEY`, as the contents of the JSON key file Google issued for the service account. |
| `auth_headers` | object | no | Credentials for `CUSTOM_AUTH_HEADERS`. |
| `cloud_run_url` | `str` | no | URL of the Cloud Run service Monte Carlo should call. |
| `name` | `str` | no | Display name for the collection agent. |
| `authentication_type` | object | no | How Monte Carlo authenticates when it calls the agent. |

### Response

Response fields: id, name, deployment_id, authentication_type, enabled, created_time, last_updated_time, image_build, image_version, is_remote_upgradeable, cloud_run_url.

## `delete_gcp_collection_agent`: Delete a GCP collection agent

Deregister a GCP collection agent. The deployment is left without an agent and cannot take another one from here; to register a replacement, delete the deployment with delete_deployment and provision a new one with create_deployment.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `collection_agent_id` | `str` | yes | Id of the collection agent, as returned by list_collection_agents. |

### Response

Returns the path id and `deleted: true`.

## `register_gcp_collection_agent`: Register a GCP collection agent

**Not an MCP tool.** Use the CLI, Terraform or the SDK.

Register a collection agent you have deployed on GCP, completing the deployment it was provisioned for. Needs the deployment's id, the Cloud Run service's URL, and either a service account key or auth headers, named by authentication_type.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `service_account_key` | `str` | no | Credentials for `GCP_JSON_SERVICE_ACCOUNT_KEY`, as the contents of the JSON key file Google issued for the service account. |
| `auth_headers` | object | no | Credentials for `CUSTOM_AUTH_HEADERS`. |
| `authentication_type` | one of `GCP_JSON_SERVICE_ACCOUNT_KEY`, `CUSTOM_AUTH_HEADERS` | yes | How Monte Carlo authenticates when it calls the agent. |
| `deployment_id` | `str` | yes | Deployment to register the collection agent on. |
| `cloud_run_url` | `str` | yes | URL of the Cloud Run service Monte Carlo should call. |
| `name` | `str` | no | Display name for the collection agent. |

### Response

Response fields: id, name, deployment_id, authentication_type, enabled, created_time, last_updated_time, image_build, image_version, is_remote_upgradeable, cloud_run_url.

## `get_generic_collection_agent`: Get a generic collection agent

Get one generic collection agent.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `collection_agent_id` | `str` | yes | Id of the collection agent, as returned by list_collection_agents. |

### Response

Response fields: id, name, deployment_id, authentication_type, enabled, created_time, last_updated_time, image_build, image_version, is_remote_upgradeable.

## `update_generic_collection_agent`: Update a generic collection agent

Rename a generic collection agent. The name is the only field this takes.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `collection_agent_id` | `str` | yes | Id of the collection agent, as returned by list_collection_agents. |
| `name` | `str` | no | Display name for the collection agent. |

### Response

Response fields: id, name, deployment_id, authentication_type, enabled, created_time, last_updated_time, image_build, image_version, is_remote_upgradeable.

## `delete_generic_collection_agent`: Delete a generic collection agent

Deregister a generic collection agent, deleting the credentials created for its deployment. The deployment is left without an agent and cannot take another one from here; to register a replacement, delete the deployment with delete_deployment and provision a new one with create_deployment.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `collection_agent_id` | `str` | yes | Id of the collection agent, as returned by list_collection_agents. |

### Response

Returns the path id and `deleted: true`.

## `register_generic_collection_agent`: Register a generic collection agent

Enable the generic collection agent a deployment was provisioned for, once the agent is running and connected to Monte Carlo. Needs the deployment's id. Provision the deployment with create_deployment first. The token or OAuth client the agent starts with is created with the CLI or the API, not from here, because the response carries the secret; delete_generic_collection_agent_token and delete_generic_collection_agent_oauth_client remove one.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `deployment_id` | `str` | yes | Deployment whose generic collection agent to enable. |
| `name` | `str` | no | Display name for the collection agent. |

### Response

Response fields: id, name, deployment_id, authentication_type, enabled, created_time, last_updated_time, image_build, image_version, is_remote_upgradeable.

## `list_generic_collection_agent_credentials`: List generic collection agent credentials

List the credentials your generic collection agents present, of both kinds.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `deployment_id` | `str` | no | Only the credentials of this deployment's agent. |

### Response

Returns `items`. Response fields per item: id, deployment_id, type, description, created_time, mcd_id, client_id, scopes, expiration_time.

## `create_generic_collection_agent_token`: Create a token for a generic collection agent

**Not an MCP tool.** Use the CLI, Terraform or the SDK.

Create a key and secret for a deployment's generic collection agent.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `deployment_id` | `str` | yes | Deployment whose generic collection agent will present this credential. |
| `description` | `str` | no | What this credential is for. |

### Response

Response fields: id, deployment_id, type, description, created_time, mcd_id, mcd_token.

## `get_generic_collection_agent_token`: Get a generic collection agent token

Get one token. The secret is not part of it.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credential_id` | `str` | yes | Id of the credential, as returned by list_generic_collection_agent_credentials. |

### Response

Response fields: id, deployment_id, type, description, created_time, mcd_id.

## `delete_generic_collection_agent_token`: Delete a generic collection agent token

Delete a token a generic collection agent presents. An agent still running with it stops being able to connect.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credential_id` | `str` | yes | Id of the credential, as returned by list_generic_collection_agent_credentials. |

### Response

Returns the path id and `deleted: true`.

## `create_generic_collection_agent_oauth_client`: Create an OAuth client for a generic collection agent

**Not an MCP tool.** Use the CLI, Terraform or the SDK.

Create an OAuth 2.0 client for a deployment's generic collection agent.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `deployment_id` | `str` | yes | Deployment whose generic collection agent will present this credential. |
| `description` | `str` | no | What this credential is for. |
| `expiration_days` | `int` | no | Days until the client stops being accepted. |

### Response

Response fields: id, deployment_id, type, description, created_time, client_id, scopes, expiration_time, client_secret, secret_id.

## `get_generic_collection_agent_oauth_client`: Get a generic collection agent OAuth client

Get one OAuth client. The secret is not part of it.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credential_id` | `str` | yes | Id of the credential, as returned by list_generic_collection_agent_credentials. |

### Response

Response fields: id, deployment_id, type, description, created_time, client_id, scopes, expiration_time.

## `delete_generic_collection_agent_oauth_client`: Delete a generic collection agent OAuth client

Delete an OAuth client a generic collection agent presents. An agent still running with it stops being able to get new access tokens; ones already issued last until they expire.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credential_id` | `str` | yes | Id of the credential, as returned by list_generic_collection_agent_credentials. |

### Response

Returns the path id and `deleted: true`.
