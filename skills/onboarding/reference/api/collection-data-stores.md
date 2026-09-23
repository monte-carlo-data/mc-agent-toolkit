# `collection-data-stores` tools

<!-- GENERATED STUB (YET-2891): api-codegen's `-mcp-reference` mode will replace this file whole from the
     REST API v2 OpenAPI document; do not hand-edit once that lands. Until then this stub lists the operations
     of the tag by `operationId`, which is the MCP tool name, with the arguments the spec declares. -->

Monte Carlo REST API v2 operations of the `collection-data-stores` tag. Each heading is the tool name once the Monte Carlo MCP
server exposes it. Operations marked **not an MCP tool** are reachable through the CLI, Terraform or the SDK only,
because their request or response carries a secret.

## `list_collection_data_stores`: List collection data stores

List the data stores in your account, on every platform.

### Arguments

None.

### Response

Returns `items`. Response fields per item: id, name, deployment_id, storage_type, authentication_type, enabled, created_time, last_updated_time, platform, endpoint.

## `get_aws_collection_data_store`: Get an AWS collection data store

Get one data store held in an S3 bucket, including its external id.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `collection_data_store_id` | `str` | yes | Id of the data store, as returned by list_collection_data_stores. |

### Response

Response fields: id, name, deployment_id, storage_type, authentication_type, enabled, created_time, last_updated_time, bucket_name, external_id.

## `update_aws_collection_data_store`: Update an AWS collection data store

Change the bucket, role or name of an S3 data store. A new bucket or role is revalidated; a rename is not.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `collection_data_store_id` | `str` | yes | Id of the data store, as returned by list_collection_data_stores. |
| `bucket_name` | `str` | no | Name of the S3 bucket Monte Carlo should use. |
| `role_arn` | `str` | no | ARN of the role Monte Carlo assumes to access the bucket. |
| `name` | `str` | no | Display name for the data store. |

### Response

Response fields: id, name, deployment_id, storage_type, authentication_type, enabled, created_time, last_updated_time, bucket_name, external_id.

## `delete_aws_collection_data_store`: Delete an AWS collection data store

Deregister an S3 data store. The deployment is left without a data store and cannot take another one from here; to register a replacement, delete the deployment with delete_deployment and provision a new one with create_deployment.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `collection_data_store_id` | `str` | yes | Id of the data store, as returned by list_collection_data_stores. |

### Response

Returns the path id and `deleted: true`.

## `register_aws_collection_data_store`: Register an AWS collection data store

Register an S3 bucket as a data store, completing the deployment it was provisioned for. Provision the deployment with create_deployment first, then create the bucket in your AWS account. Takes the deployment's id, the bucket name, and the ARN of the role Monte Carlo assumes to access it.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `deployment_id` | `str` | yes | Deployment to register the data store on. |
| `bucket_name` | `str` | yes | Name of the S3 bucket Monte Carlo should use. |
| `role_arn` | `str` | yes | ARN of the role Monte Carlo assumes to access the bucket. |
| `name` | `str` | no | Display name for the data store. |

### Response

Response fields: id, name, deployment_id, storage_type, authentication_type, enabled, created_time, last_updated_time, bucket_name, external_id.

## `get_azure_collection_data_store`: Get an Azure collection data store

Read one data store held in Azure Blob Storage.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `collection_data_store_id` | `str` | yes | Id of the data store, as returned by list_collection_data_stores. |

### Response

Response fields: id, name, deployment_id, storage_type, authentication_type, enabled, created_time, last_updated_time, container_name.

## `update_azure_collection_data_store`: Update an Azure collection data store

**Not an MCP tool.** Use the CLI, Terraform or the SDK.

Change the container, credentials, authentication type or name of an Azure data store. Monte Carlo revalidates it and re-enables it if it was disabled. Changing only the name skips revalidation.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `collection_data_store_id` | `str` | yes | Id of the data store, as returned by list_collection_data_stores. |
| `storage_account_keys` | object | no | Credentials for `AZURE_STORAGE_ACCOUNT_KEYS`. |
| `service_principal` | object | no | Credentials for `AZURE_STORAGE_SERVICE_PRINCIPAL`. |
| `container_name` | `str` | no | Name of the blob container Monte Carlo should use. |
| `name` | `str` | no | Display name for the data store. |
| `authentication_type` | object | no | How Monte Carlo authenticates to the storage account. |

### Response

Response fields: id, name, deployment_id, storage_type, authentication_type, enabled, created_time, last_updated_time, container_name.

## `delete_azure_collection_data_store`: Delete an Azure collection data store

Deregister an Azure data store. The deployment is left without a data store and cannot take another one from here; to register a replacement, delete the deployment with delete_deployment and provision a new one with create_deployment.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `collection_data_store_id` | `str` | yes | Id of the data store, as returned by list_collection_data_stores. |

### Response

Returns the path id and `deleted: true`.

## `register_azure_collection_data_store`: Register an Azure collection data store

**Not an MCP tool.** Use the CLI, Terraform or the SDK.

Register an Azure Blob Storage container as a data store, completing the deployment it was provisioned for. Needs the deployment's id, the container name, and either a storage account connection string or a service principal, named by authentication_type.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `storage_account_keys` | object | no | Credentials for `AZURE_STORAGE_ACCOUNT_KEYS`. |
| `service_principal` | object | no | Credentials for `AZURE_STORAGE_SERVICE_PRINCIPAL`. |
| `authentication_type` | one of `AZURE_STORAGE_ACCOUNT_KEYS`, `AZURE_STORAGE_SERVICE_PRINCIPAL` | yes | How Monte Carlo authenticates to the storage account. |
| `deployment_id` | `str` | yes | Deployment to register the data store on. |
| `container_name` | `str` | yes | Name of the blob container Monte Carlo should use. |
| `name` | `str` | no | Display name for the data store. |

### Response

Response fields: id, name, deployment_id, storage_type, authentication_type, enabled, created_time, last_updated_time, container_name.

## `get_gcp_collection_data_store`: Get a GCP collection data store

Read one data store held in Google Cloud Storage.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `collection_data_store_id` | `str` | yes | Id of the data store, as returned by list_collection_data_stores. |

### Response

Response fields: id, name, deployment_id, storage_type, authentication_type, enabled, created_time, last_updated_time, bucket_name.

## `update_gcp_collection_data_store`: Update a GCP collection data store

**Not an MCP tool.** Use the CLI, Terraform or the SDK.

Change the bucket, service account key or name of a GCP data store. Monte Carlo revalidates it and re-enables it if it was disabled. Changing only the name skips revalidation.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `collection_data_store_id` | `str` | yes | Id of the data store, as returned by list_collection_data_stores. |
| `bucket_name` | `str` | no | Name of the Cloud Storage bucket Monte Carlo should use. |
| `service_account_key` | `str` | no | Service account key Monte Carlo reaches the bucket with, as the contents of the JSON key file Google issued for it. |
| `name` | `str` | no | Display name for the data store. |

### Response

Response fields: id, name, deployment_id, storage_type, authentication_type, enabled, created_time, last_updated_time, bucket_name.

## `delete_gcp_collection_data_store`: Delete a GCP collection data store

Deregister a GCP data store. The deployment is left without a data store and cannot take another one from here; to register a replacement, delete the deployment with delete_deployment and provision a new one with create_deployment.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `collection_data_store_id` | `str` | yes | Id of the data store, as returned by list_collection_data_stores. |

### Response

Returns the path id and `deleted: true`.

## `register_gcp_collection_data_store`: Register a GCP collection data store

**Not an MCP tool.** Use the CLI, Terraform or the SDK.

Register a Google Cloud Storage bucket as a data store, completing the deployment it was provisioned for. Needs the deployment's id, the bucket name and a service account key.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `deployment_id` | `str` | yes | Deployment to register the data store on. |
| `bucket_name` | `str` | yes | Name of the Cloud Storage bucket Monte Carlo should use. |
| `service_account_key` | `str` | yes | Service account key Monte Carlo reaches the bucket with, as the contents of the JSON key file Google issued for it. |
| `name` | `str` | no | Display name for the data store. |

### Response

Response fields: id, name, deployment_id, storage_type, authentication_type, enabled, created_time, last_updated_time, bucket_name.
