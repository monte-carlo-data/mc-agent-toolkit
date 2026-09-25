# `collection-data-stores` tools

<!-- Rendered from the REST API v2 OpenAPI document by api-codegen; do not edit. -->

Monte Carlo REST API v2 tools of the `collection-data-stores` tag, as the Monte Carlo MCP server exposes
them. Each section is one tool; its name is the tool to call.

## `list_collection_data_stores`: List collection data stores

List the data stores in your account, on every platform.

Only data stores on deployments running Monte Carlo's current collection platform are
listed. Data stores on the older platform are managed separately and do not appear here.

Data stores are sorted by name, ignoring case. Data stores with no name come last.

- **Effect:** read-only.
- **Pairs with:** `register_aws_collection_data_store`, `get_aws_collection_data_store`, `get_azure_collection_data_store`, `get_gcp_collection_data_store`.

### Arguments

None.

### Response

Returns `items`. Response fields per item: id, name, deployment_id, storage_type, authentication_type, enabled, created_time, last_updated_time, platform, endpoint.

| Field | Description |
|---|---|
| `id` | Unique identifier of the data store. |
| `name` | Display name of the data store. Null when it has no name. |
| `deployment_id` | Identifier of the deployment this data store belongs to. |
| `storage_type` | Which kind of storage the data store keeps its data in. |
| `authentication_type` | How Monte Carlo authenticates when it reaches the data store. |
| `enabled` | Whether Monte Carlo is using this data store. One that is unregistered, or whose validation failed, is not enabled. |
| `created_time` | When the data store was created, which is when its deployment was provisioned. |
| `last_updated_time` | When the data store was last registered, renamed, or given different storage or credentials. Null until one of those has happened. |
| `platform` | Where the data store runs. Build the platform-specific path for any other operation on it from this. Null when Monte Carlo has not recorded a platform, and no platform-specific path addresses those. |
| `endpoint` | Address of the data store, in the form its platform uses. On AWS that is an S3 bucket name, on Azure the name of a blob container, and on GCP a Cloud Storage bucket name. Empty until it has been registered. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- An unexpected error prevented the request from being processed.

## `register_aws_collection_data_store`: Register an AWS collection data store

Register an S3 bucket as a data store, completing the deployment it was provisioned for. Provision the deployment with create_deployment first, then create the bucket in your AWS account. Takes the deployment's id, the bucket name, and the ARN of the role Monte Carlo assumes to access it.

- **Effect:** creates; repeating it creates again.
- **Pairs with:** `get_aws_collection_data_store`, `update_aws_collection_data_store`, `delete_aws_collection_data_store`, `list_collection_data_stores`, `list_deployments`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `deployment_id` | `str` | yes | Deployment to register the data store on. It must already hold an unregistered S3 data store. |
| `bucket_name` | `str` | yes | Name of the S3 bucket Monte Carlo should use. |
| `role_arn` | `str` | yes | ARN of the role Monte Carlo assumes to access the bucket. Its trust policy must already carry the deployment's external id. |
| `name` | `str` | no | Display name for the data store. Replaces the name its deployment gave it. Up to 200 characters. |

### Response

Returns the new collection data store. Response fields: id, name, deployment_id, storage_type, authentication_type, enabled, created_time, last_updated_time, bucket_name, external_id.

| Field | Description |
|---|---|
| `id` | Unique identifier of the data store. |
| `name` | Display name of the data store. Null when it has no name. |
| `deployment_id` | Identifier of the deployment this data store belongs to. |
| `storage_type` | Which kind of storage the data store keeps its data in. |
| `authentication_type` | How Monte Carlo authenticates when it reaches the data store. |
| `enabled` | Whether Monte Carlo is using this data store. One that is unregistered, or whose validation failed, is not enabled. |
| `created_time` | When the data store was created, which is when its deployment was provisioned. |
| `last_updated_time` | When the data store was last registered, renamed, or given different storage or credentials. Null until one of those has happened. |
| `bucket_name` | Name of the S3 bucket Monte Carlo uses. Empty until it has been registered. |
| `external_id` | Value to put in the trust policy of the role Monte Carlo assumes to access the bucket. Null before Monte Carlo has generated one, and for a caller who cannot register a data store. Also null if the value could not be read just now, so retry once before treating it as absent. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The collection data store does not exist, or is not visible to the caller.
- The change conflicts with the current state of the collection data store.
- An argument is invalid; the error names the field.
- Monte Carlo is busy or temporarily unavailable; the tool retries once after the wait Monte Carlo asks for.
- An unexpected error prevented the request from being processed.

## `get_aws_collection_data_store`: Get an AWS collection data store

Get one data store held in an S3 bucket, including its external id.

An id that names a data store on another platform, or no data store in your account,
returns 404.

- **Effect:** read-only.
- **Pairs with:** `register_aws_collection_data_store`, `update_aws_collection_data_store`, `delete_aws_collection_data_store`, `list_collection_data_stores`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `collection_data_store_id` | `str` | yes | Id of the collection data store, as returned by list_collection_data_stores. |

### Response

Response fields: id, name, deployment_id, storage_type, authentication_type, enabled, created_time, last_updated_time, bucket_name, external_id.

| Field | Description |
|---|---|
| `id` | Unique identifier of the data store. |
| `name` | Display name of the data store. Null when it has no name. |
| `deployment_id` | Identifier of the deployment this data store belongs to. |
| `storage_type` | Which kind of storage the data store keeps its data in. |
| `authentication_type` | How Monte Carlo authenticates when it reaches the data store. |
| `enabled` | Whether Monte Carlo is using this data store. One that is unregistered, or whose validation failed, is not enabled. |
| `created_time` | When the data store was created, which is when its deployment was provisioned. |
| `last_updated_time` | When the data store was last registered, renamed, or given different storage or credentials. Null until one of those has happened. |
| `bucket_name` | Name of the S3 bucket Monte Carlo uses. Empty until it has been registered. |
| `external_id` | Value to put in the trust policy of the role Monte Carlo assumes to access the bucket. Null before Monte Carlo has generated one, and for a caller who cannot register a data store. Also null if the value could not be read just now, so retry once before treating it as absent. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The collection data store does not exist, or is not visible to the caller.
- An unexpected error prevented the request from being processed.

## `update_aws_collection_data_store`: Update an AWS collection data store

Change the bucket, role or name of an S3 data store. A new bucket or role is revalidated; a rename is not.

- **Effect:** updates in place; idempotent.
- **Pairs with:** `register_aws_collection_data_store`, `get_aws_collection_data_store`, `delete_aws_collection_data_store`, `list_collection_data_stores`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `collection_data_store_id` | `str` | yes | Id of the collection data store, as returned by list_collection_data_stores. |
| `bucket_name` | `str` | no | Name of the S3 bucket Monte Carlo should use. |
| `role_arn` | `str` | no | ARN of the role Monte Carlo assumes to access the bucket. Its trust policy must already carry the deployment's external id. |
| `name` | `str` | no | Display name for the data store. Replaces the name its deployment gave it. Up to 200 characters. |

### Response

Returns the collection data store after the change. Response fields: id, name, deployment_id, storage_type, authentication_type, enabled, created_time, last_updated_time, bucket_name, external_id.

| Field | Description |
|---|---|
| `id` | Unique identifier of the data store. |
| `name` | Display name of the data store. Null when it has no name. |
| `deployment_id` | Identifier of the deployment this data store belongs to. |
| `storage_type` | Which kind of storage the data store keeps its data in. |
| `authentication_type` | How Monte Carlo authenticates when it reaches the data store. |
| `enabled` | Whether Monte Carlo is using this data store. One that is unregistered, or whose validation failed, is not enabled. |
| `created_time` | When the data store was created, which is when its deployment was provisioned. |
| `last_updated_time` | When the data store was last registered, renamed, or given different storage or credentials. Null until one of those has happened. |
| `bucket_name` | Name of the S3 bucket Monte Carlo uses. Empty until it has been registered. |
| `external_id` | Value to put in the trust policy of the role Monte Carlo assumes to access the bucket. Null before Monte Carlo has generated one, and for a caller who cannot register a data store. Also null if the value could not be read just now, so retry once before treating it as absent. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The collection data store does not exist, or is not visible to the caller.
- The change conflicts with the current state of the collection data store.
- An argument is invalid; the error names the field.
- Monte Carlo is busy or temporarily unavailable; the tool retries once after the wait Monte Carlo asks for.
- An unexpected error prevented the request from being processed.

## `delete_aws_collection_data_store`: Delete an AWS collection data store

Deregister an S3 data store. The deployment is left without a data store and cannot take another one from here; to register a replacement, delete the deployment with delete_deployment and provision a new one with create_deployment.

- **Effect:** deletes; destructive and idempotent.
- **Pairs with:** `register_aws_collection_data_store`, `get_aws_collection_data_store`, `update_aws_collection_data_store`, `list_collection_data_stores`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `collection_data_store_id` | `str` | yes | Id of the collection data store, as returned by list_collection_data_stores. |

### Response

Returns `collection_data_store_id` and `deleted: true` once the collection data store is gone.

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The collection data store does not exist, or is not visible to the caller.
- The change conflicts with the current state of the collection data store.
- Monte Carlo is busy or temporarily unavailable; try again after a moment.
- An unexpected error prevented the request from being processed.

## `get_azure_collection_data_store`: Get an Azure collection data store

Read one data store held in Azure Blob Storage.

An id that names a data store on another platform, or no data store in your account,
returns 404.

- **Effect:** read-only.
- **Pairs with:** `delete_azure_collection_data_store`, `list_collection_data_stores`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `collection_data_store_id` | `str` | yes | Id of the collection data store, as returned by list_collection_data_stores. |

### Response

Response fields: id, name, deployment_id, storage_type, authentication_type, enabled, created_time, last_updated_time, container_name.

| Field | Description |
|---|---|
| `id` | Unique identifier of the data store. |
| `name` | Display name of the data store. Null when it has no name. |
| `deployment_id` | Identifier of the deployment this data store belongs to. |
| `storage_type` | Which kind of storage the data store keeps its data in. |
| `authentication_type` | How Monte Carlo authenticates when it reaches the data store. |
| `enabled` | Whether Monte Carlo is using this data store. One that is unregistered, or whose validation failed, is not enabled. |
| `created_time` | When the data store was created, which is when its deployment was provisioned. |
| `last_updated_time` | When the data store was last registered, renamed, or given different storage or credentials. Null until one of those has happened. |
| `container_name` | Name of the blob container Monte Carlo uses. Empty until it has been registered. The storage account holding it is part of the credentials, so it is not returned. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The collection data store does not exist, or is not visible to the caller.
- An unexpected error prevented the request from being processed.

## `delete_azure_collection_data_store`: Delete an Azure collection data store

Deregister an Azure data store. The deployment is left without a data store and cannot take another one from here; to register a replacement, delete the deployment with delete_deployment and provision a new one with create_deployment.

- **Effect:** deletes; destructive and idempotent.
- **Pairs with:** `get_azure_collection_data_store`, `list_collection_data_stores`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `collection_data_store_id` | `str` | yes | Id of the collection data store, as returned by list_collection_data_stores. |

### Response

Returns `collection_data_store_id` and `deleted: true` once the collection data store is gone.

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The collection data store does not exist, or is not visible to the caller.
- The change conflicts with the current state of the collection data store.
- Monte Carlo is busy or temporarily unavailable; try again after a moment.
- An unexpected error prevented the request from being processed.

## `get_gcp_collection_data_store`: Get a GCP collection data store

Read one data store held in Google Cloud Storage.

An id that names a data store on another platform, or no data store in your account,
returns 404.

- **Effect:** read-only.
- **Pairs with:** `delete_gcp_collection_data_store`, `list_collection_data_stores`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `collection_data_store_id` | `str` | yes | Id of the collection data store, as returned by list_collection_data_stores. |

### Response

Response fields: id, name, deployment_id, storage_type, authentication_type, enabled, created_time, last_updated_time, bucket_name.

| Field | Description |
|---|---|
| `id` | Unique identifier of the data store. |
| `name` | Display name of the data store. Null when it has no name. |
| `deployment_id` | Identifier of the deployment this data store belongs to. |
| `storage_type` | Which kind of storage the data store keeps its data in. |
| `authentication_type` | How Monte Carlo authenticates when it reaches the data store. |
| `enabled` | Whether Monte Carlo is using this data store. One that is unregistered, or whose validation failed, is not enabled. |
| `created_time` | When the data store was created, which is when its deployment was provisioned. |
| `last_updated_time` | When the data store was last registered, renamed, or given different storage or credentials. Null until one of those has happened. |
| `bucket_name` | Name of the Cloud Storage bucket Monte Carlo uses. Empty until it has been registered. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The collection data store does not exist, or is not visible to the caller.
- An unexpected error prevented the request from being processed.

## `delete_gcp_collection_data_store`: Delete a GCP collection data store

Deregister a GCP data store. The deployment is left without a data store and cannot take another one from here; to register a replacement, delete the deployment with delete_deployment and provision a new one with create_deployment.

- **Effect:** deletes; destructive and idempotent.
- **Pairs with:** `get_gcp_collection_data_store`, `list_collection_data_stores`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `collection_data_store_id` | `str` | yes | Id of the collection data store, as returned by list_collection_data_stores. |

### Response

Returns `collection_data_store_id` and `deleted: true` once the collection data store is gone.

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The collection data store does not exist, or is not visible to the caller.
- The change conflicts with the current state of the collection data store.
- Monte Carlo is busy or temporarily unavailable; try again after a moment.
- An unexpected error prevented the request from being processed.
