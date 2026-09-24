# `credentials` tools

<!-- GENERATED STUB: api-codegen's `-mcp-reference` mode will replace this file whole from the
     REST API v2 OpenAPI document; do not hand-edit once that lands. Until then this stub lists the operations
     of the tag by `operationId`, which is the MCP tool name, with the arguments the spec declares. -->

Monte Carlo REST API v2 operations of the `credentials` tag. Each heading is the tool name once the Monte Carlo MCP
server exposes it. Operations marked **not an MCP tool** are reachable through the CLI, Terraform or the SDK only,
because their request or response carries a secret.

## `list_credentials`: List credentials

List the credentials in your account, of every kind, a page at a time.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `cursor` | `str` | no | Position to continue from, as returned in `next_cursor` by the previous page. |
| `limit` | `int` | no | Maximum number of items to return, between 1 and 100. |
| `with_count` | `bool` | no | Whether to also return the total number of items across every page, in `count`. |

### Response

Returns `items` (response fields per item: id, connection_type, storage_type, created_time), `next_cursor`, `has_more`, `count`; one page per call. `storage_type` is one of `mc_managed`, `aws_secrets_manager`, `gcp_secret_manager`, `azure_key_vault`, `env_var`, `file`.

## `create_snowflake_credentials`: Create Snowflake credentials

**Not an MCP tool.** Use the CLI, Terraform or the SDK.

Store a Snowflake key pair for connections to use.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `account` | `str` | yes | Snowflake account identifier, such as `xy12345.us-east-1`. |
| `user` | `str` | yes | Snowflake user the key pair belongs to. |
| `private_key` | `str` | yes | The private key of the pair, as PEM text including its BEGIN and END lines. |
| `private_key_passphrase` | `str` | no | Passphrase the private key is encrypted with. |
| `warehouse` | `str` | no | Snowflake virtual warehouse to run queries in. |

### Response

Response fields: id, connection_type, storage_type, created_time, account, user, warehouse.

## `get_snowflake_credentials`: Get Snowflake credentials

Get one set of Snowflake credentials, without the key.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned by list_credentials. |

### Response

Response fields: id, connection_type, storage_type, created_time, account, user, warehouse.

## `update_snowflake_credentials`: Update Snowflake credentials

**Not an MCP tool.** Use the CLI, Terraform or the SDK.

Change Snowflake credentials in place.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned by list_credentials. |
| `account` | `str` | no | New Snowflake account identifier, without the `.snowflakecomputing.com` suffix. |
| `user` | `str` | no | New Snowflake user. |
| `private_key` | `str` | no | New private key, as PEM text. |
| `private_key_passphrase` | `str` | no | Passphrase of the new private key. |
| `warehouse` | `str` | no | New Snowflake virtual warehouse. |

### Response

Response fields: id, connection_type, storage_type, created_time, account, user, warehouse.

## `delete_snowflake_credentials`: Delete Snowflake credentials

Delete Snowflake credentials no connection uses. Monte Carlo stops using the stored key. Rotate or revoke the key pair in Snowflake if the key itself must be retired.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned by list_credentials. |

### Response

Returns the path id and `deleted: true`.

## `create_aws_secrets_manager_credentials`: Create AWS Secrets Manager credentials

Store where a connection's credentials live in AWS Secrets Manager: the secret's name or ARN, its region and the role to assume, never the secret itself.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `connection_type` | `str` | yes | The connection type the credentials are for, such as `snowflake` or `bigquery`, or one of your custom connector types. |
| `bq_project_id` | `str` | no | BigQuery project the connection reads from. |
| `databricks_warehouse_id` | `str` | no | Databricks SQL warehouse the connection runs queries on. |
| `aws_secret` | `str` | yes | Name or ARN of the AWS Secrets Manager secret holding the connection's credentials. |
| `aws_region` | `str` | no | AWS region of the secret. |
| `assumable_role` | `str` | no | ARN of a role the deployment assumes to read the secret. |
| `external_id` | `str` | no | External id the assumed role's trust policy requires, if it requires one. |

### Response

Response fields: id, connection_type, storage_type, created_time, bq_project_id, databricks_warehouse_id, aws_secret, aws_region, assumable_role, external_id.

## `get_aws_secrets_manager_credentials`: Get AWS Secrets Manager credentials

Get one set of AWS Secrets Manager credentials.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned by list_credentials. |

### Response

Response fields: id, connection_type, storage_type, created_time, bq_project_id, databricks_warehouse_id, aws_secret, aws_region, assumable_role, external_id.

## `update_aws_secrets_manager_credentials`: Update AWS Secrets Manager credentials

Change where AWS Secrets Manager credentials point. Takes only the fields to change.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned by list_credentials. |
| `bq_project_id` | `str` | no | BigQuery project the connection reads from. |
| `databricks_warehouse_id` | `str` | no | Databricks SQL warehouse the connection runs queries on. |
| `aws_secret` | `str` | no | Name or ARN of the AWS Secrets Manager secret holding the connection's credentials. |
| `aws_region` | `str` | no | AWS region of the secret. |
| `assumable_role` | `str` | no | ARN of a role the deployment assumes to read the secret. |
| `external_id` | `str` | no | External id the assumed role's trust policy requires, if it requires one. |

### Response

Response fields: id, connection_type, storage_type, created_time, bq_project_id, databricks_warehouse_id, aws_secret, aws_region, assumable_role, external_id.

## `delete_aws_secrets_manager_credentials`: Delete AWS Secrets Manager credentials

Delete AWS Secrets Manager credentials no connection uses. The secret in AWS is untouched.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned by list_credentials. |

### Response

Returns the path id and `deleted: true`.

## `create_gcp_secret_manager_credentials`: Create GCP Secret Manager credentials

Store where a connection's credentials live in GCP Secret Manager: the secret's name, never the secret itself.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `connection_type` | `str` | yes | The connection type the credentials are for, such as `snowflake` or `bigquery`, or one of your custom connector types. |
| `bq_project_id` | `str` | no | BigQuery project the connection reads from. |
| `databricks_warehouse_id` | `str` | no | Databricks SQL warehouse the connection runs queries on. |
| `gcp_secret` | `str` | yes | Name of the GCP Secret Manager secret holding the connection's credentials. |

### Response

Response fields: id, connection_type, storage_type, created_time, bq_project_id, databricks_warehouse_id, gcp_secret.

## `get_gcp_secret_manager_credentials`: Get GCP Secret Manager credentials

Get one set of GCP Secret Manager credentials.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned by list_credentials. |

### Response

Response fields: id, connection_type, storage_type, created_time, bq_project_id, databricks_warehouse_id, gcp_secret.

## `update_gcp_secret_manager_credentials`: Update GCP Secret Manager credentials

Change where GCP Secret Manager credentials point. Takes only the fields to change.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned by list_credentials. |
| `bq_project_id` | `str` | no | BigQuery project the connection reads from. |
| `databricks_warehouse_id` | `str` | no | Databricks SQL warehouse the connection runs queries on. |
| `gcp_secret` | `str` | no | Name of the GCP Secret Manager secret holding the connection's credentials. |

### Response

Response fields: id, connection_type, storage_type, created_time, bq_project_id, databricks_warehouse_id, gcp_secret.

## `delete_gcp_secret_manager_credentials`: Delete GCP Secret Manager credentials

Delete GCP Secret Manager credentials no connection uses. The secret in GCP is untouched.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned by list_credentials. |

### Response

Returns the path id and `deleted: true`.

## `create_azure_key_vault_credentials`: Create Azure Key Vault credentials

Store where a connection's credentials live in Azure Key Vault: the vault and the secret's name, never the secret itself.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `connection_type` | `str` | yes | The connection type the credentials are for, such as `snowflake` or `bigquery`, or one of your custom connector types. |
| `bq_project_id` | `str` | no | BigQuery project the connection reads from. |
| `databricks_warehouse_id` | `str` | no | Databricks SQL warehouse the connection runs queries on. |
| `akv_secret` | `str` | yes | Name of the Azure Key Vault secret holding the connection's credentials. |
| `akv_vault_name` | `str` | no | Name of the key vault. |
| `akv_vault_url` | `str` | no | URL of the key vault. |

### Response

Response fields: id, connection_type, storage_type, created_time, bq_project_id, databricks_warehouse_id, akv_secret, akv_vault_name, akv_vault_url.

## `get_azure_key_vault_credentials`: Get Azure Key Vault credentials

Get one set of Azure Key Vault credentials.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned by list_credentials. |

### Response

Response fields: id, connection_type, storage_type, created_time, bq_project_id, databricks_warehouse_id, akv_secret, akv_vault_name, akv_vault_url.

## `update_azure_key_vault_credentials`: Update Azure Key Vault credentials

Change where Azure Key Vault credentials point. Takes only the fields to change.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned by list_credentials. |
| `bq_project_id` | `str` | no | BigQuery project the connection reads from. |
| `databricks_warehouse_id` | `str` | no | Databricks SQL warehouse the connection runs queries on. |
| `akv_secret` | `str` | no | Name of the Azure Key Vault secret holding the connection's credentials. |
| `akv_vault_name` | `str` | no | Name of the key vault. |
| `akv_vault_url` | `str` | no | URL of the key vault. |

### Response

Response fields: id, connection_type, storage_type, created_time, bq_project_id, databricks_warehouse_id, akv_secret, akv_vault_name, akv_vault_url.

## `delete_azure_key_vault_credentials`: Delete Azure Key Vault credentials

Delete Azure Key Vault credentials no connection uses. The secret in Azure is untouched.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned by list_credentials. |

### Response

Returns the path id and `deleted: true`.

## `create_env_var_credentials`: Create environment variable credentials

Store which environment variable of the deployment holds a connection's credentials, and the KMS key that encrypts it, never the value itself.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `connection_type` | `str` | yes | The connection type the credentials are for, such as `snowflake` or `bigquery`, or one of your custom connector types. |
| `bq_project_id` | `str` | no | BigQuery project the connection reads from. |
| `databricks_warehouse_id` | `str` | no | Databricks SQL warehouse the connection runs queries on. |
| `env_var_name` | `str` | yes | Name of the environment variable on the deployment that holds the connection's credentials. |
| `kms_key_id` | `str` | no | AWS KMS key the variable's value is encrypted with. |

### Response

Response fields: id, connection_type, storage_type, created_time, bq_project_id, databricks_warehouse_id, env_var_name, kms_key_id.

## `get_env_var_credentials`: Get environment variable credentials

Get one set of environment variable credentials.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned by list_credentials. |

### Response

Response fields: id, connection_type, storage_type, created_time, bq_project_id, databricks_warehouse_id, env_var_name, kms_key_id.

## `update_env_var_credentials`: Update environment variable credentials

Change which environment variable credentials point at. Takes only the fields to change.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned by list_credentials. |
| `bq_project_id` | `str` | no | BigQuery project the connection reads from. |
| `databricks_warehouse_id` | `str` | no | Databricks SQL warehouse the connection runs queries on. |
| `env_var_name` | `str` | no | Name of the environment variable on the deployment that holds the connection's credentials. |
| `kms_key_id` | `str` | no | AWS KMS key the variable's value is encrypted with. |

### Response

Response fields: id, connection_type, storage_type, created_time, bq_project_id, databricks_warehouse_id, env_var_name, kms_key_id.

## `delete_env_var_credentials`: Delete environment variable credentials

Delete environment variable credentials no connection uses. The variable on the deployment is untouched.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned by list_credentials. |

### Response

Returns the path id and `deleted: true`.

## `create_file_credentials`: Create file credentials

Store which file on the deployment holds a connection's credentials, never the contents.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `connection_type` | `str` | yes | The connection type the credentials are for, such as `snowflake` or `bigquery`, or one of your custom connector types. |
| `bq_project_id` | `str` | no | BigQuery project the connection reads from. |
| `databricks_warehouse_id` | `str` | no | Databricks SQL warehouse the connection runs queries on. |
| `file_path` | `str` | yes | Path of the file on the deployment that holds the connection's credentials. |

### Response

Response fields: id, connection_type, storage_type, created_time, bq_project_id, databricks_warehouse_id, file_path.

## `get_file_credentials`: Get file credentials

Get one set of file credentials.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned by list_credentials. |

### Response

Response fields: id, connection_type, storage_type, created_time, bq_project_id, databricks_warehouse_id, file_path.

## `update_file_credentials`: Update file credentials

Change which file credentials point at. Takes only the fields to change.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned by list_credentials. |
| `bq_project_id` | `str` | no | BigQuery project the connection reads from. |
| `databricks_warehouse_id` | `str` | no | Databricks SQL warehouse the connection runs queries on. |
| `file_path` | `str` | no | Path of the file on the deployment that holds the connection's credentials. |

### Response

Response fields: id, connection_type, storage_type, created_time, bq_project_id, databricks_warehouse_id, file_path.

## `delete_file_credentials`: Delete file credentials

Delete file credentials no connection uses. The file on the deployment is untouched.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned by list_credentials. |

### Response

Returns the path id and `deleted: true`.
