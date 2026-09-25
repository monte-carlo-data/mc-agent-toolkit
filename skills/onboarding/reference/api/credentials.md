# `credentials` tools

<!-- Rendered from the REST API v2 OpenAPI document by api-codegen; do not edit. -->

Monte Carlo REST API v2 tools of the `credentials` tag, as the Monte Carlo MCP server exposes
them. Each section is one tool; its name is the tool to call.

## `list_credentials`: List credentials

List the credentials in your account, of every kind, a page at a time.

Credentials are returned oldest first. Each entry says what connection type it is for and
where its secret lives; read the typed endpoint for that kind to see its other fields.

- **Effect:** read-only.
- **Pairs with:** `create_aws_secrets_manager_credentials`, `validate_aws_secrets_manager_credentials`, `get_aws_secrets_manager_credentials`, `create_azure_key_vault_credentials`, `validate_azure_key_vault_credentials`, `get_azure_key_vault_credentials`, `create_env_var_credentials`, `validate_env_var_credentials`, `get_env_var_credentials`, `create_file_credentials`, `validate_file_credentials`, `get_file_credentials`, `create_gcp_secret_manager_credentials`, `validate_gcp_secret_manager_credentials`, `get_gcp_secret_manager_credentials`, `get_snowflake_credentials`.
- **Paging:** one page per call; pass `next_cursor` back as `cursor` for the next page.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `cursor` | `str` | no | Position to continue from, as returned in `next_cursor` by the previous page. Omit it to start from the first page. The value is opaque; do not build or modify one. |
| `limit` | `int` | no | Maximum number of items to return, between 1 and 100. |
| `with_count` | `bool` | no | Whether to also return the total number of items across every page, in `count`. Off by default: counting costs an extra query. |

### Response

Returns `items` (response fields per item: id, connection_type, storage_type, created_time), `next_cursor` (pass it as `cursor` for the next page; null on the last page), `has_more`, and `count` (the total across pages, only when `with_count` is true).

| Field | Description |
|---|---|
| `id` | Unique identifier of the credentials. |
| `connection_type` | The connection type the credentials are for, such as `snowflake`. Fixed once created. |
| `storage_type` | Where the secret lives. Fixed once created. |
| `created_time` | When the credentials were created. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- An argument is invalid; the error names the field.
- An unexpected error prevented the request from being processed.

## `create_aws_secrets_manager_credentials`: Create AWS Secrets Manager credentials

Store where a connection's credentials live in AWS Secrets Manager: the secret's name or ARN, its region and the role to assume, never the secret itself.

- **Effect:** creates; repeating it creates again.
- **Pairs with:** `get_aws_secrets_manager_credentials`, `update_aws_secrets_manager_credentials`, `delete_aws_secrets_manager_credentials`, `list_credentials`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `connection_type` | `str` | yes | The connection type the credentials are for, such as `snowflake` or `bigquery`, or one of your custom connector types. Fixed once created. Between 1 and 200 characters. |
| `aws_secret` | `str` | yes | Name or ARN of the AWS Secrets Manager secret holding the connection's credentials. Between 1 and 2048 characters. |
| `bq_project_id` | `str` | no | BigQuery project the connection reads from. Only for a BigQuery connection. Between 1 and 200 characters. |
| `databricks_warehouse_id` | `str` | no | Databricks SQL warehouse the connection runs queries on. Required for a `databricks-sql-warehouse` or `databricks-metastore-sql-warehouse` connection. Between 1 and 200 characters. |
| `aws_region` | `str` | no | AWS region of the secret. Omit it to use the deployment's own region. Between 1 and 200 characters. |
| `assumable_role` | `str` | no | ARN of a role the deployment assumes to read the secret. Omit it to read as itself. Between 1 and 2048 characters. |
| `external_id` | `str` | no | External id the assumed role's trust policy requires, if it requires one. Between 1 and 1224 characters. |

### Response

Returns the new credentials. Response fields: id, connection_type, storage_type, created_time, bq_project_id, databricks_warehouse_id, aws_secret, aws_region, assumable_role, external_id.

| Field | Description |
|---|---|
| `id` | Unique identifier of the credentials. |
| `connection_type` | The connection type the credentials are for, such as `snowflake`. Fixed once created. |
| `storage_type` | Where the secret lives. Fixed once created. |
| `created_time` | When the credentials were created. |
| `bq_project_id` | BigQuery project the connection reads from. Null unless set. |
| `databricks_warehouse_id` | Databricks SQL warehouse the connection runs queries on. Null unless set. |
| `aws_secret` | Name or ARN of the AWS Secrets Manager secret holding the connection's credentials. |
| `aws_region` | AWS region of the secret. Null when unset. |
| `assumable_role` | ARN of the role the deployment assumes to read the secret. Null when unset. |
| `external_id` | External id presented when assuming the role. Null when unset. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The change conflicts with the current state of the credentials.
- An argument is invalid; the error names the field.
- Monte Carlo is busy or temporarily unavailable; the tool retries once after the wait Monte Carlo asks for.
- An unexpected error prevented the request from being processed.

## `validate_aws_secrets_manager_credentials`: Validate AWS Secrets Manager credentials

Check whether AWS Secrets Manager credentials work before creating them. Nothing is created and no credentials resource is written. Returns a run that is still going: poll `get_validation_run` with its id until the status is `completed`, then read each validation's own verdict.

- **Effect:** creates; repeating it creates again.
- **Pairs with:** `list_credentials`, `list_deployments`.
- **Runs in the background:** the response is the accepted request; poll it to completion.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `deployment_id` | `str` | yes | Deployment that runs the validations. It has to be one `GET /deployments` lists, and it has to be able to reach the system the credentials are for. |
| `connection_type` | `str` | yes | What the credentials are for, hyphenated, such as `snowflake` or `bigquery`. Decides which checks run. Between 1 and 100 characters. |
| `aws_secret` | `str` | yes | Name or ARN of the AWS Secrets Manager secret holding the connection's credentials. Between 1 and 2048 characters. |
| `bq_project_id` | `str` | no | BigQuery project the connection reads from. Only for a BigQuery connection. Between 1 and 200 characters. |
| `databricks_warehouse_id` | `str` | no | Databricks SQL warehouse the connection runs queries on. Required for a `databricks-sql-warehouse` or `databricks-metastore-sql-warehouse` connection. Between 1 and 200 characters. |
| `aws_region` | `str` | no | AWS region of the secret. Omit it to use the deployment's own region. Between 1 and 200 characters. |
| `assumable_role` | `str` | no | ARN of a role the deployment assumes to read the secret. Omit it to read as itself. Between 1 and 2048 characters. |
| `external_id` | `str` | no | External id the assumed role's trust policy requires, if it requires one. Between 1 and 1224 characters. |

### Response

Returns the accepted request as-is. Response fields: id, status, revision, target_type, target_id, validations_passed, validations_total, started_at, finished_at, expires_at, validations.

| Field | Description |
|---|---|
| `id` | Identifier of the run. Poll `GET /validations/{run_id}` with it. |
| `status` | Whether the run is still going. Every validation is final once it is not. |
| `revision` | Moves forward every time a validation changes. Pass it as `since` on the next poll to get only the validations that changed after this response. |
| `target_type` | What the run validates. |
| `target_id` | Identifier of what is being validated. Null for candidate values, which are not stored anywhere. |
| `validations_passed` | How many validations reached a passing verdict. One that was skipped or never reached a verdict is not counted here, but is still in `validations_total`. |
| `validations_total` | How many validations the run covers. |
| `started_at` | When the run started. |
| `finished_at` | When the run finished. Null while it is still going. |
| `expires_at` | When the run stops being readable. Measured from the start, not the finish, and never extended, so a slow run is readable for less time after it ends. |
| `validations` | The run's validations, in the order they are declared. Validations waiting on a prerequisite are listed before they start. A read with `since` lists only the validations that changed after that revision, and may list none. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The credentials does not exist, or is not visible to the caller.
- The change conflicts with the current state of the credentials.
- An argument is invalid; the error names the field.
- Monte Carlo is busy or temporarily unavailable; the tool retries once after the wait Monte Carlo asks for.
- An unexpected error prevented the request from being processed.

## `get_aws_secrets_manager_credentials`: Get AWS Secrets Manager credentials

Get one set of AWS Secrets Manager credentials.

An id that does not exist, belongs to another account, or names credentials of another
kind returns 404.

- **Effect:** read-only.
- **Pairs with:** `create_aws_secrets_manager_credentials`, `update_aws_secrets_manager_credentials`, `delete_aws_secrets_manager_credentials`, `list_credentials`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned by list_credentials. |

### Response

Response fields: id, connection_type, storage_type, created_time, bq_project_id, databricks_warehouse_id, aws_secret, aws_region, assumable_role, external_id.

| Field | Description |
|---|---|
| `id` | Unique identifier of the credentials. |
| `connection_type` | The connection type the credentials are for, such as `snowflake`. Fixed once created. |
| `storage_type` | Where the secret lives. Fixed once created. |
| `created_time` | When the credentials were created. |
| `bq_project_id` | BigQuery project the connection reads from. Null unless set. |
| `databricks_warehouse_id` | Databricks SQL warehouse the connection runs queries on. Null unless set. |
| `aws_secret` | Name or ARN of the AWS Secrets Manager secret holding the connection's credentials. |
| `aws_region` | AWS region of the secret. Null when unset. |
| `assumable_role` | ARN of the role the deployment assumes to read the secret. Null when unset. |
| `external_id` | External id presented when assuming the role. Null when unset. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The credentials does not exist, or is not visible to the caller.
- An unexpected error prevented the request from being processed.
- Monte Carlo is busy or temporarily unavailable; try again after a moment.

## `update_aws_secrets_manager_credentials`: Update AWS Secrets Manager credentials

Change where AWS Secrets Manager credentials point. Takes only the fields to change.

- **Effect:** updates in place; idempotent.
- **Pairs with:** `create_aws_secrets_manager_credentials`, `get_aws_secrets_manager_credentials`, `delete_aws_secrets_manager_credentials`, `list_credentials`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned by list_credentials. |
| `bq_project_id` | `str` | no | BigQuery project the connection reads from. Only for a BigQuery connection. Between 1 and 200 characters. |
| `databricks_warehouse_id` | `str` | no | Databricks SQL warehouse the connection runs queries on. Required for a `databricks-sql-warehouse` or `databricks-metastore-sql-warehouse` connection. Between 1 and 200 characters. |
| `aws_secret` | `str` | no | Name or ARN of the AWS Secrets Manager secret holding the connection's credentials. Between 1 and 2048 characters. |
| `aws_region` | `str` | no | AWS region of the secret. Omit it to use the deployment's own region. Between 1 and 200 characters. |
| `assumable_role` | `str` | no | ARN of a role the deployment assumes to read the secret. Omit it to read as itself. Between 1 and 2048 characters. |
| `external_id` | `str` | no | External id the assumed role's trust policy requires, if it requires one. Between 1 and 1224 characters. |

### Response

Returns the credentials after the change. Response fields: id, connection_type, storage_type, created_time, bq_project_id, databricks_warehouse_id, aws_secret, aws_region, assumable_role, external_id.

| Field | Description |
|---|---|
| `id` | Unique identifier of the credentials. |
| `connection_type` | The connection type the credentials are for, such as `snowflake`. Fixed once created. |
| `storage_type` | Where the secret lives. Fixed once created. |
| `created_time` | When the credentials were created. |
| `bq_project_id` | BigQuery project the connection reads from. Null unless set. |
| `databricks_warehouse_id` | Databricks SQL warehouse the connection runs queries on. Null unless set. |
| `aws_secret` | Name or ARN of the AWS Secrets Manager secret holding the connection's credentials. |
| `aws_region` | AWS region of the secret. Null when unset. |
| `assumable_role` | ARN of the role the deployment assumes to read the secret. Null when unset. |
| `external_id` | External id presented when assuming the role. Null when unset. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The credentials does not exist, or is not visible to the caller.
- An argument is invalid; the error names the field.
- Monte Carlo is busy or temporarily unavailable; the tool retries once after the wait Monte Carlo asks for.
- An unexpected error prevented the request from being processed.

## `delete_aws_secrets_manager_credentials`: Delete AWS Secrets Manager credentials

Delete AWS Secrets Manager credentials no connection uses. The secret in AWS is untouched.

- **Effect:** deletes; destructive and idempotent.
- **Pairs with:** `create_aws_secrets_manager_credentials`, `get_aws_secrets_manager_credentials`, `update_aws_secrets_manager_credentials`, `list_credentials`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned by list_credentials. |

### Response

Returns `credentials_id` and `deleted: true` once the credentials is gone.

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The credentials does not exist, or is not visible to the caller.
- The change conflicts with the current state of the credentials.
- Monte Carlo is busy or temporarily unavailable; try again after a moment.
- An unexpected error prevented the request from being processed.

## `create_azure_key_vault_credentials`: Create Azure Key Vault credentials

Store where a connection's credentials live in Azure Key Vault: the vault and the secret's name, never the secret itself.

- **Effect:** creates; repeating it creates again.
- **Pairs with:** `get_azure_key_vault_credentials`, `update_azure_key_vault_credentials`, `delete_azure_key_vault_credentials`, `list_credentials`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `connection_type` | `str` | yes | The connection type the credentials are for, such as `snowflake` or `bigquery`, or one of your custom connector types. Fixed once created. Between 1 and 200 characters. |
| `akv_secret` | `str` | yes | Name of the Azure Key Vault secret holding the connection's credentials. Between 1 and 200 characters. |
| `bq_project_id` | `str` | no | BigQuery project the connection reads from. Only for a BigQuery connection. Between 1 and 200 characters. |
| `databricks_warehouse_id` | `str` | no | Databricks SQL warehouse the connection runs queries on. Required for a `databricks-sql-warehouse` or `databricks-metastore-sql-warehouse` connection. Between 1 and 200 characters. |
| `akv_vault_name` | `str` | no | Name of the key vault. Send this, `akv_vault_url`, or both. Between 1 and 200 characters. |
| `akv_vault_url` | `str` | no | URL of the key vault. Send this, `akv_vault_name`, or both. Between 1 and 2048 characters. |

### Response

Returns the new credentials. Response fields: id, connection_type, storage_type, created_time, bq_project_id, databricks_warehouse_id, akv_secret, akv_vault_name, akv_vault_url.

| Field | Description |
|---|---|
| `id` | Unique identifier of the credentials. |
| `connection_type` | The connection type the credentials are for, such as `snowflake`. Fixed once created. |
| `storage_type` | Where the secret lives. Fixed once created. |
| `created_time` | When the credentials were created. |
| `bq_project_id` | BigQuery project the connection reads from. Null unless set. |
| `databricks_warehouse_id` | Databricks SQL warehouse the connection runs queries on. Null unless set. |
| `akv_secret` | Name of the Azure Key Vault secret holding the connection's credentials. |
| `akv_vault_name` | Name of the key vault. Null when unset. |
| `akv_vault_url` | URL of the key vault. Null when unset. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The change conflicts with the current state of the credentials.
- An argument is invalid; the error names the field.
- Monte Carlo is busy or temporarily unavailable; the tool retries once after the wait Monte Carlo asks for.
- An unexpected error prevented the request from being processed.

## `validate_azure_key_vault_credentials`: Validate Azure Key Vault credentials

Check whether Azure Key Vault credentials work before creating them. Nothing is created and no credentials resource is written. Returns a run that is still going: poll `get_validation_run` with its id until the status is `completed`, then read each validation's own verdict.

- **Effect:** creates; repeating it creates again.
- **Pairs with:** `list_credentials`, `list_deployments`.
- **Runs in the background:** the response is the accepted request; poll it to completion.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `deployment_id` | `str` | yes | Deployment that runs the validations. It has to be one `GET /deployments` lists, and it has to be able to reach the system the credentials are for. |
| `connection_type` | `str` | yes | What the credentials are for, hyphenated, such as `snowflake` or `bigquery`. Decides which checks run. Between 1 and 100 characters. |
| `akv_secret` | `str` | yes | Name of the Azure Key Vault secret holding the connection's credentials. Between 1 and 200 characters. |
| `bq_project_id` | `str` | no | BigQuery project the connection reads from. Only for a BigQuery connection. Between 1 and 200 characters. |
| `databricks_warehouse_id` | `str` | no | Databricks SQL warehouse the connection runs queries on. Required for a `databricks-sql-warehouse` or `databricks-metastore-sql-warehouse` connection. Between 1 and 200 characters. |
| `akv_vault_name` | `str` | no | Name of the key vault. Send this, `akv_vault_url`, or both. Between 1 and 200 characters. |
| `akv_vault_url` | `str` | no | URL of the key vault. Send this, `akv_vault_name`, or both. Between 1 and 2048 characters. |

### Response

Returns the accepted request as-is. Response fields: id, status, revision, target_type, target_id, validations_passed, validations_total, started_at, finished_at, expires_at, validations.

| Field | Description |
|---|---|
| `id` | Identifier of the run. Poll `GET /validations/{run_id}` with it. |
| `status` | Whether the run is still going. Every validation is final once it is not. |
| `revision` | Moves forward every time a validation changes. Pass it as `since` on the next poll to get only the validations that changed after this response. |
| `target_type` | What the run validates. |
| `target_id` | Identifier of what is being validated. Null for candidate values, which are not stored anywhere. |
| `validations_passed` | How many validations reached a passing verdict. One that was skipped or never reached a verdict is not counted here, but is still in `validations_total`. |
| `validations_total` | How many validations the run covers. |
| `started_at` | When the run started. |
| `finished_at` | When the run finished. Null while it is still going. |
| `expires_at` | When the run stops being readable. Measured from the start, not the finish, and never extended, so a slow run is readable for less time after it ends. |
| `validations` | The run's validations, in the order they are declared. Validations waiting on a prerequisite are listed before they start. A read with `since` lists only the validations that changed after that revision, and may list none. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The credentials does not exist, or is not visible to the caller.
- The change conflicts with the current state of the credentials.
- An argument is invalid; the error names the field.
- Monte Carlo is busy or temporarily unavailable; the tool retries once after the wait Monte Carlo asks for.
- An unexpected error prevented the request from being processed.

## `get_azure_key_vault_credentials`: Get Azure Key Vault credentials

Get one set of Azure Key Vault credentials.

An id that does not exist, belongs to another account, or names credentials of another
kind returns 404.

- **Effect:** read-only.
- **Pairs with:** `create_azure_key_vault_credentials`, `update_azure_key_vault_credentials`, `delete_azure_key_vault_credentials`, `list_credentials`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned by list_credentials. |

### Response

Response fields: id, connection_type, storage_type, created_time, bq_project_id, databricks_warehouse_id, akv_secret, akv_vault_name, akv_vault_url.

| Field | Description |
|---|---|
| `id` | Unique identifier of the credentials. |
| `connection_type` | The connection type the credentials are for, such as `snowflake`. Fixed once created. |
| `storage_type` | Where the secret lives. Fixed once created. |
| `created_time` | When the credentials were created. |
| `bq_project_id` | BigQuery project the connection reads from. Null unless set. |
| `databricks_warehouse_id` | Databricks SQL warehouse the connection runs queries on. Null unless set. |
| `akv_secret` | Name of the Azure Key Vault secret holding the connection's credentials. |
| `akv_vault_name` | Name of the key vault. Null when unset. |
| `akv_vault_url` | URL of the key vault. Null when unset. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The credentials does not exist, or is not visible to the caller.
- An unexpected error prevented the request from being processed.
- Monte Carlo is busy or temporarily unavailable; try again after a moment.

## `update_azure_key_vault_credentials`: Update Azure Key Vault credentials

Change where Azure Key Vault credentials point. Takes only the fields to change.

- **Effect:** updates in place; idempotent.
- **Pairs with:** `create_azure_key_vault_credentials`, `get_azure_key_vault_credentials`, `delete_azure_key_vault_credentials`, `list_credentials`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned by list_credentials. |
| `bq_project_id` | `str` | no | BigQuery project the connection reads from. Only for a BigQuery connection. Between 1 and 200 characters. |
| `databricks_warehouse_id` | `str` | no | Databricks SQL warehouse the connection runs queries on. Required for a `databricks-sql-warehouse` or `databricks-metastore-sql-warehouse` connection. Between 1 and 200 characters. |
| `akv_secret` | `str` | no | Name of the Azure Key Vault secret holding the connection's credentials. Between 1 and 200 characters. |
| `akv_vault_name` | `str` | no | Name of the key vault. Send this, `akv_vault_url`, or both. Between 1 and 200 characters. |
| `akv_vault_url` | `str` | no | URL of the key vault. Send this, `akv_vault_name`, or both. Between 1 and 2048 characters. |

### Response

Returns the credentials after the change. Response fields: id, connection_type, storage_type, created_time, bq_project_id, databricks_warehouse_id, akv_secret, akv_vault_name, akv_vault_url.

| Field | Description |
|---|---|
| `id` | Unique identifier of the credentials. |
| `connection_type` | The connection type the credentials are for, such as `snowflake`. Fixed once created. |
| `storage_type` | Where the secret lives. Fixed once created. |
| `created_time` | When the credentials were created. |
| `bq_project_id` | BigQuery project the connection reads from. Null unless set. |
| `databricks_warehouse_id` | Databricks SQL warehouse the connection runs queries on. Null unless set. |
| `akv_secret` | Name of the Azure Key Vault secret holding the connection's credentials. |
| `akv_vault_name` | Name of the key vault. Null when unset. |
| `akv_vault_url` | URL of the key vault. Null when unset. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The credentials does not exist, or is not visible to the caller.
- An argument is invalid; the error names the field.
- Monte Carlo is busy or temporarily unavailable; the tool retries once after the wait Monte Carlo asks for.
- An unexpected error prevented the request from being processed.

## `delete_azure_key_vault_credentials`: Delete Azure Key Vault credentials

Delete Azure Key Vault credentials no connection uses. The secret in Azure is untouched.

- **Effect:** deletes; destructive and idempotent.
- **Pairs with:** `create_azure_key_vault_credentials`, `get_azure_key_vault_credentials`, `update_azure_key_vault_credentials`, `list_credentials`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned by list_credentials. |

### Response

Returns `credentials_id` and `deleted: true` once the credentials is gone.

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The credentials does not exist, or is not visible to the caller.
- The change conflicts with the current state of the credentials.
- Monte Carlo is busy or temporarily unavailable; try again after a moment.
- An unexpected error prevented the request from being processed.

## `create_env_var_credentials`: Create environment variable credentials

Store which environment variable of the deployment holds a connection's credentials, and the KMS key that encrypts it, never the value itself.

- **Effect:** creates; repeating it creates again.
- **Pairs with:** `get_env_var_credentials`, `update_env_var_credentials`, `delete_env_var_credentials`, `list_credentials`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `connection_type` | `str` | yes | The connection type the credentials are for, such as `snowflake` or `bigquery`, or one of your custom connector types. Fixed once created. Between 1 and 200 characters. |
| `env_var_name` | `str` | yes | Name of the environment variable on the deployment that holds the connection's credentials. Must start with `MCD_`. Between 1 and 200 characters. |
| `bq_project_id` | `str` | no | BigQuery project the connection reads from. Only for a BigQuery connection. Between 1 and 200 characters. |
| `databricks_warehouse_id` | `str` | no | Databricks SQL warehouse the connection runs queries on. Required for a `databricks-sql-warehouse` or `databricks-metastore-sql-warehouse` connection. Between 1 and 200 characters. |
| `kms_key_id` | `str` | no | AWS KMS key the variable's value is encrypted with. Omit it for a value stored in the clear. Between 1 and 200 characters. |

### Response

Returns the new credentials. Response fields: id, connection_type, storage_type, created_time, bq_project_id, databricks_warehouse_id, env_var_name, kms_key_id.

| Field | Description |
|---|---|
| `id` | Unique identifier of the credentials. |
| `connection_type` | The connection type the credentials are for, such as `snowflake`. Fixed once created. |
| `storage_type` | Where the secret lives. Fixed once created. |
| `created_time` | When the credentials were created. |
| `bq_project_id` | BigQuery project the connection reads from. Null unless set. |
| `databricks_warehouse_id` | Databricks SQL warehouse the connection runs queries on. Null unless set. |
| `env_var_name` | Name of the environment variable on the deployment that holds the connection's credentials. Must start with `MCD_`. |
| `kms_key_id` | AWS KMS key the value is encrypted with. Null for a value in the clear. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The change conflicts with the current state of the credentials.
- An argument is invalid; the error names the field.
- Monte Carlo is busy or temporarily unavailable; the tool retries once after the wait Monte Carlo asks for.
- An unexpected error prevented the request from being processed.

## `validate_env_var_credentials`: Validate environment variable credentials

Check whether environment variable credentials work before creating them. Nothing is created and no credentials resource is written. Returns a run that is still going: poll `get_validation_run` with its id until the status is `completed`, then read each validation's own verdict.

- **Effect:** creates; repeating it creates again.
- **Pairs with:** `list_credentials`, `list_deployments`.
- **Runs in the background:** the response is the accepted request; poll it to completion.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `deployment_id` | `str` | yes | Deployment that runs the validations. It has to be one `GET /deployments` lists, and it has to be able to reach the system the credentials are for. |
| `connection_type` | `str` | yes | What the credentials are for, hyphenated, such as `snowflake` or `bigquery`. Decides which checks run. Between 1 and 100 characters. |
| `env_var_name` | `str` | yes | Name of the environment variable on the deployment that holds the connection's credentials. Must start with `MCD_`. Between 1 and 200 characters. |
| `bq_project_id` | `str` | no | BigQuery project the connection reads from. Only for a BigQuery connection. Between 1 and 200 characters. |
| `databricks_warehouse_id` | `str` | no | Databricks SQL warehouse the connection runs queries on. Required for a `databricks-sql-warehouse` or `databricks-metastore-sql-warehouse` connection. Between 1 and 200 characters. |
| `kms_key_id` | `str` | no | AWS KMS key the variable's value is encrypted with. Omit it for a value stored in the clear. Between 1 and 200 characters. |

### Response

Returns the accepted request as-is. Response fields: id, status, revision, target_type, target_id, validations_passed, validations_total, started_at, finished_at, expires_at, validations.

| Field | Description |
|---|---|
| `id` | Identifier of the run. Poll `GET /validations/{run_id}` with it. |
| `status` | Whether the run is still going. Every validation is final once it is not. |
| `revision` | Moves forward every time a validation changes. Pass it as `since` on the next poll to get only the validations that changed after this response. |
| `target_type` | What the run validates. |
| `target_id` | Identifier of what is being validated. Null for candidate values, which are not stored anywhere. |
| `validations_passed` | How many validations reached a passing verdict. One that was skipped or never reached a verdict is not counted here, but is still in `validations_total`. |
| `validations_total` | How many validations the run covers. |
| `started_at` | When the run started. |
| `finished_at` | When the run finished. Null while it is still going. |
| `expires_at` | When the run stops being readable. Measured from the start, not the finish, and never extended, so a slow run is readable for less time after it ends. |
| `validations` | The run's validations, in the order they are declared. Validations waiting on a prerequisite are listed before they start. A read with `since` lists only the validations that changed after that revision, and may list none. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The credentials does not exist, or is not visible to the caller.
- The change conflicts with the current state of the credentials.
- An argument is invalid; the error names the field.
- Monte Carlo is busy or temporarily unavailable; the tool retries once after the wait Monte Carlo asks for.
- An unexpected error prevented the request from being processed.

## `get_env_var_credentials`: Get environment variable credentials

Get one set of environment variable credentials.

An id that does not exist, belongs to another account, or names credentials of another
kind returns 404.

- **Effect:** read-only.
- **Pairs with:** `create_env_var_credentials`, `update_env_var_credentials`, `delete_env_var_credentials`, `list_credentials`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned by list_credentials. |

### Response

Response fields: id, connection_type, storage_type, created_time, bq_project_id, databricks_warehouse_id, env_var_name, kms_key_id.

| Field | Description |
|---|---|
| `id` | Unique identifier of the credentials. |
| `connection_type` | The connection type the credentials are for, such as `snowflake`. Fixed once created. |
| `storage_type` | Where the secret lives. Fixed once created. |
| `created_time` | When the credentials were created. |
| `bq_project_id` | BigQuery project the connection reads from. Null unless set. |
| `databricks_warehouse_id` | Databricks SQL warehouse the connection runs queries on. Null unless set. |
| `env_var_name` | Name of the environment variable on the deployment that holds the connection's credentials. Must start with `MCD_`. |
| `kms_key_id` | AWS KMS key the value is encrypted with. Null for a value in the clear. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The credentials does not exist, or is not visible to the caller.
- An unexpected error prevented the request from being processed.
- Monte Carlo is busy or temporarily unavailable; try again after a moment.

## `update_env_var_credentials`: Update environment variable credentials

Change which environment variable credentials point at. Takes only the fields to change.

- **Effect:** updates in place; idempotent.
- **Pairs with:** `create_env_var_credentials`, `get_env_var_credentials`, `delete_env_var_credentials`, `list_credentials`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned by list_credentials. |
| `bq_project_id` | `str` | no | BigQuery project the connection reads from. Only for a BigQuery connection. Between 1 and 200 characters. |
| `databricks_warehouse_id` | `str` | no | Databricks SQL warehouse the connection runs queries on. Required for a `databricks-sql-warehouse` or `databricks-metastore-sql-warehouse` connection. Between 1 and 200 characters. |
| `env_var_name` | `str` | no | Name of the environment variable on the deployment that holds the connection's credentials. Must start with `MCD_`. Between 1 and 200 characters. |
| `kms_key_id` | `str` | no | AWS KMS key the variable's value is encrypted with. Omit it for a value stored in the clear. Between 1 and 200 characters. |

### Response

Returns the credentials after the change. Response fields: id, connection_type, storage_type, created_time, bq_project_id, databricks_warehouse_id, env_var_name, kms_key_id.

| Field | Description |
|---|---|
| `id` | Unique identifier of the credentials. |
| `connection_type` | The connection type the credentials are for, such as `snowflake`. Fixed once created. |
| `storage_type` | Where the secret lives. Fixed once created. |
| `created_time` | When the credentials were created. |
| `bq_project_id` | BigQuery project the connection reads from. Null unless set. |
| `databricks_warehouse_id` | Databricks SQL warehouse the connection runs queries on. Null unless set. |
| `env_var_name` | Name of the environment variable on the deployment that holds the connection's credentials. Must start with `MCD_`. |
| `kms_key_id` | AWS KMS key the value is encrypted with. Null for a value in the clear. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The credentials does not exist, or is not visible to the caller.
- An argument is invalid; the error names the field.
- Monte Carlo is busy or temporarily unavailable; the tool retries once after the wait Monte Carlo asks for.
- An unexpected error prevented the request from being processed.

## `delete_env_var_credentials`: Delete environment variable credentials

Delete environment variable credentials no connection uses. The variable on the deployment is untouched.

- **Effect:** deletes; destructive and idempotent.
- **Pairs with:** `create_env_var_credentials`, `get_env_var_credentials`, `update_env_var_credentials`, `list_credentials`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned by list_credentials. |

### Response

Returns `credentials_id` and `deleted: true` once the credentials is gone.

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The credentials does not exist, or is not visible to the caller.
- The change conflicts with the current state of the credentials.
- Monte Carlo is busy or temporarily unavailable; try again after a moment.
- An unexpected error prevented the request from being processed.

## `create_file_credentials`: Create file credentials

Store which file on the deployment holds a connection's credentials, never the contents.

- **Effect:** creates; repeating it creates again.
- **Pairs with:** `get_file_credentials`, `update_file_credentials`, `delete_file_credentials`, `list_credentials`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `connection_type` | `str` | yes | The connection type the credentials are for, such as `snowflake` or `bigquery`, or one of your custom connector types. Fixed once created. Between 1 and 200 characters. |
| `file_path` | `str` | yes | Path of the file on the deployment that holds the connection's credentials. Between 1 and 1024 characters. |
| `bq_project_id` | `str` | no | BigQuery project the connection reads from. Only for a BigQuery connection. Between 1 and 200 characters. |
| `databricks_warehouse_id` | `str` | no | Databricks SQL warehouse the connection runs queries on. Required for a `databricks-sql-warehouse` or `databricks-metastore-sql-warehouse` connection. Between 1 and 200 characters. |

### Response

Returns the new credentials. Response fields: id, connection_type, storage_type, created_time, bq_project_id, databricks_warehouse_id, file_path.

| Field | Description |
|---|---|
| `id` | Unique identifier of the credentials. |
| `connection_type` | The connection type the credentials are for, such as `snowflake`. Fixed once created. |
| `storage_type` | Where the secret lives. Fixed once created. |
| `created_time` | When the credentials were created. |
| `bq_project_id` | BigQuery project the connection reads from. Null unless set. |
| `databricks_warehouse_id` | Databricks SQL warehouse the connection runs queries on. Null unless set. |
| `file_path` | Path of the file on the deployment that holds the connection's credentials. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The change conflicts with the current state of the credentials.
- An argument is invalid; the error names the field.
- Monte Carlo is busy or temporarily unavailable; the tool retries once after the wait Monte Carlo asks for.
- An unexpected error prevented the request from being processed.

## `validate_file_credentials`: Validate file credentials

Check whether file credentials work before creating them. Nothing is created and no credentials resource is written. Returns a run that is still going: poll `get_validation_run` with its id until the status is `completed`, then read each validation's own verdict.

- **Effect:** creates; repeating it creates again.
- **Pairs with:** `list_credentials`, `list_deployments`.
- **Runs in the background:** the response is the accepted request; poll it to completion.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `deployment_id` | `str` | yes | Deployment that runs the validations. It has to be one `GET /deployments` lists, and it has to be able to reach the system the credentials are for. |
| `connection_type` | `str` | yes | What the credentials are for, hyphenated, such as `snowflake` or `bigquery`. Decides which checks run. Between 1 and 100 characters. |
| `file_path` | `str` | yes | Path of the file on the deployment that holds the connection's credentials. Between 1 and 1024 characters. |
| `bq_project_id` | `str` | no | BigQuery project the connection reads from. Only for a BigQuery connection. Between 1 and 200 characters. |
| `databricks_warehouse_id` | `str` | no | Databricks SQL warehouse the connection runs queries on. Required for a `databricks-sql-warehouse` or `databricks-metastore-sql-warehouse` connection. Between 1 and 200 characters. |

### Response

Returns the accepted request as-is. Response fields: id, status, revision, target_type, target_id, validations_passed, validations_total, started_at, finished_at, expires_at, validations.

| Field | Description |
|---|---|
| `id` | Identifier of the run. Poll `GET /validations/{run_id}` with it. |
| `status` | Whether the run is still going. Every validation is final once it is not. |
| `revision` | Moves forward every time a validation changes. Pass it as `since` on the next poll to get only the validations that changed after this response. |
| `target_type` | What the run validates. |
| `target_id` | Identifier of what is being validated. Null for candidate values, which are not stored anywhere. |
| `validations_passed` | How many validations reached a passing verdict. One that was skipped or never reached a verdict is not counted here, but is still in `validations_total`. |
| `validations_total` | How many validations the run covers. |
| `started_at` | When the run started. |
| `finished_at` | When the run finished. Null while it is still going. |
| `expires_at` | When the run stops being readable. Measured from the start, not the finish, and never extended, so a slow run is readable for less time after it ends. |
| `validations` | The run's validations, in the order they are declared. Validations waiting on a prerequisite are listed before they start. A read with `since` lists only the validations that changed after that revision, and may list none. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The credentials does not exist, or is not visible to the caller.
- The change conflicts with the current state of the credentials.
- An argument is invalid; the error names the field.
- Monte Carlo is busy or temporarily unavailable; the tool retries once after the wait Monte Carlo asks for.
- An unexpected error prevented the request from being processed.

## `get_file_credentials`: Get file credentials

Get one set of file credentials.

An id that does not exist, belongs to another account, or names credentials of another
kind returns 404.

- **Effect:** read-only.
- **Pairs with:** `create_file_credentials`, `update_file_credentials`, `delete_file_credentials`, `list_credentials`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned by list_credentials. |

### Response

Response fields: id, connection_type, storage_type, created_time, bq_project_id, databricks_warehouse_id, file_path.

| Field | Description |
|---|---|
| `id` | Unique identifier of the credentials. |
| `connection_type` | The connection type the credentials are for, such as `snowflake`. Fixed once created. |
| `storage_type` | Where the secret lives. Fixed once created. |
| `created_time` | When the credentials were created. |
| `bq_project_id` | BigQuery project the connection reads from. Null unless set. |
| `databricks_warehouse_id` | Databricks SQL warehouse the connection runs queries on. Null unless set. |
| `file_path` | Path of the file on the deployment that holds the connection's credentials. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The credentials does not exist, or is not visible to the caller.
- An unexpected error prevented the request from being processed.
- Monte Carlo is busy or temporarily unavailable; try again after a moment.

## `update_file_credentials`: Update file credentials

Change which file credentials point at. Takes only the fields to change.

- **Effect:** updates in place; idempotent.
- **Pairs with:** `create_file_credentials`, `get_file_credentials`, `delete_file_credentials`, `list_credentials`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned by list_credentials. |
| `bq_project_id` | `str` | no | BigQuery project the connection reads from. Only for a BigQuery connection. Between 1 and 200 characters. |
| `databricks_warehouse_id` | `str` | no | Databricks SQL warehouse the connection runs queries on. Required for a `databricks-sql-warehouse` or `databricks-metastore-sql-warehouse` connection. Between 1 and 200 characters. |
| `file_path` | `str` | no | Path of the file on the deployment that holds the connection's credentials. Between 1 and 1024 characters. |

### Response

Returns the credentials after the change. Response fields: id, connection_type, storage_type, created_time, bq_project_id, databricks_warehouse_id, file_path.

| Field | Description |
|---|---|
| `id` | Unique identifier of the credentials. |
| `connection_type` | The connection type the credentials are for, such as `snowflake`. Fixed once created. |
| `storage_type` | Where the secret lives. Fixed once created. |
| `created_time` | When the credentials were created. |
| `bq_project_id` | BigQuery project the connection reads from. Null unless set. |
| `databricks_warehouse_id` | Databricks SQL warehouse the connection runs queries on. Null unless set. |
| `file_path` | Path of the file on the deployment that holds the connection's credentials. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The credentials does not exist, or is not visible to the caller.
- An argument is invalid; the error names the field.
- Monte Carlo is busy or temporarily unavailable; the tool retries once after the wait Monte Carlo asks for.
- An unexpected error prevented the request from being processed.

## `delete_file_credentials`: Delete file credentials

Delete file credentials no connection uses. The file on the deployment is untouched.

- **Effect:** deletes; destructive and idempotent.
- **Pairs with:** `create_file_credentials`, `get_file_credentials`, `update_file_credentials`, `list_credentials`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned by list_credentials. |

### Response

Returns `credentials_id` and `deleted: true` once the credentials is gone.

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The credentials does not exist, or is not visible to the caller.
- The change conflicts with the current state of the credentials.
- Monte Carlo is busy or temporarily unavailable; try again after a moment.
- An unexpected error prevented the request from being processed.

## `create_gcp_secret_manager_credentials`: Create GCP Secret Manager credentials

Store where a connection's credentials live in GCP Secret Manager: the secret's name, never the secret itself.

- **Effect:** creates; repeating it creates again.
- **Pairs with:** `get_gcp_secret_manager_credentials`, `update_gcp_secret_manager_credentials`, `delete_gcp_secret_manager_credentials`, `list_credentials`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `connection_type` | `str` | yes | The connection type the credentials are for, such as `snowflake` or `bigquery`, or one of your custom connector types. Fixed once created. Between 1 and 200 characters. |
| `gcp_secret` | `str` | yes | Name of the GCP Secret Manager secret holding the connection's credentials. Between 1 and 200 characters. |
| `bq_project_id` | `str` | no | BigQuery project the connection reads from. Only for a BigQuery connection. Between 1 and 200 characters. |
| `databricks_warehouse_id` | `str` | no | Databricks SQL warehouse the connection runs queries on. Required for a `databricks-sql-warehouse` or `databricks-metastore-sql-warehouse` connection. Between 1 and 200 characters. |

### Response

Returns the new credentials. Response fields: id, connection_type, storage_type, created_time, bq_project_id, databricks_warehouse_id, gcp_secret.

| Field | Description |
|---|---|
| `id` | Unique identifier of the credentials. |
| `connection_type` | The connection type the credentials are for, such as `snowflake`. Fixed once created. |
| `storage_type` | Where the secret lives. Fixed once created. |
| `created_time` | When the credentials were created. |
| `bq_project_id` | BigQuery project the connection reads from. Null unless set. |
| `databricks_warehouse_id` | Databricks SQL warehouse the connection runs queries on. Null unless set. |
| `gcp_secret` | Name of the GCP Secret Manager secret holding the connection's credentials. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The change conflicts with the current state of the credentials.
- An argument is invalid; the error names the field.
- Monte Carlo is busy or temporarily unavailable; the tool retries once after the wait Monte Carlo asks for.
- An unexpected error prevented the request from being processed.

## `validate_gcp_secret_manager_credentials`: Validate GCP Secret Manager credentials

Check whether GCP Secret Manager credentials work before creating them. Nothing is created and no credentials resource is written. Returns a run that is still going: poll `get_validation_run` with its id until the status is `completed`, then read each validation's own verdict.

- **Effect:** creates; repeating it creates again.
- **Pairs with:** `list_credentials`, `list_deployments`.
- **Runs in the background:** the response is the accepted request; poll it to completion.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `deployment_id` | `str` | yes | Deployment that runs the validations. It has to be one `GET /deployments` lists, and it has to be able to reach the system the credentials are for. |
| `connection_type` | `str` | yes | What the credentials are for, hyphenated, such as `snowflake` or `bigquery`. Decides which checks run. Between 1 and 100 characters. |
| `gcp_secret` | `str` | yes | Name of the GCP Secret Manager secret holding the connection's credentials. Between 1 and 200 characters. |
| `bq_project_id` | `str` | no | BigQuery project the connection reads from. Only for a BigQuery connection. Between 1 and 200 characters. |
| `databricks_warehouse_id` | `str` | no | Databricks SQL warehouse the connection runs queries on. Required for a `databricks-sql-warehouse` or `databricks-metastore-sql-warehouse` connection. Between 1 and 200 characters. |

### Response

Returns the accepted request as-is. Response fields: id, status, revision, target_type, target_id, validations_passed, validations_total, started_at, finished_at, expires_at, validations.

| Field | Description |
|---|---|
| `id` | Identifier of the run. Poll `GET /validations/{run_id}` with it. |
| `status` | Whether the run is still going. Every validation is final once it is not. |
| `revision` | Moves forward every time a validation changes. Pass it as `since` on the next poll to get only the validations that changed after this response. |
| `target_type` | What the run validates. |
| `target_id` | Identifier of what is being validated. Null for candidate values, which are not stored anywhere. |
| `validations_passed` | How many validations reached a passing verdict. One that was skipped or never reached a verdict is not counted here, but is still in `validations_total`. |
| `validations_total` | How many validations the run covers. |
| `started_at` | When the run started. |
| `finished_at` | When the run finished. Null while it is still going. |
| `expires_at` | When the run stops being readable. Measured from the start, not the finish, and never extended, so a slow run is readable for less time after it ends. |
| `validations` | The run's validations, in the order they are declared. Validations waiting on a prerequisite are listed before they start. A read with `since` lists only the validations that changed after that revision, and may list none. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The credentials does not exist, or is not visible to the caller.
- The change conflicts with the current state of the credentials.
- An argument is invalid; the error names the field.
- Monte Carlo is busy or temporarily unavailable; the tool retries once after the wait Monte Carlo asks for.
- An unexpected error prevented the request from being processed.

## `get_gcp_secret_manager_credentials`: Get GCP Secret Manager credentials

Get one set of GCP Secret Manager credentials.

An id that does not exist, belongs to another account, or names credentials of another
kind returns 404.

- **Effect:** read-only.
- **Pairs with:** `create_gcp_secret_manager_credentials`, `update_gcp_secret_manager_credentials`, `delete_gcp_secret_manager_credentials`, `list_credentials`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned by list_credentials. |

### Response

Response fields: id, connection_type, storage_type, created_time, bq_project_id, databricks_warehouse_id, gcp_secret.

| Field | Description |
|---|---|
| `id` | Unique identifier of the credentials. |
| `connection_type` | The connection type the credentials are for, such as `snowflake`. Fixed once created. |
| `storage_type` | Where the secret lives. Fixed once created. |
| `created_time` | When the credentials were created. |
| `bq_project_id` | BigQuery project the connection reads from. Null unless set. |
| `databricks_warehouse_id` | Databricks SQL warehouse the connection runs queries on. Null unless set. |
| `gcp_secret` | Name of the GCP Secret Manager secret holding the connection's credentials. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The credentials does not exist, or is not visible to the caller.
- An unexpected error prevented the request from being processed.
- Monte Carlo is busy or temporarily unavailable; try again after a moment.

## `update_gcp_secret_manager_credentials`: Update GCP Secret Manager credentials

Change where GCP Secret Manager credentials point. Takes only the fields to change.

- **Effect:** updates in place; idempotent.
- **Pairs with:** `create_gcp_secret_manager_credentials`, `get_gcp_secret_manager_credentials`, `delete_gcp_secret_manager_credentials`, `list_credentials`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned by list_credentials. |
| `bq_project_id` | `str` | no | BigQuery project the connection reads from. Only for a BigQuery connection. Between 1 and 200 characters. |
| `databricks_warehouse_id` | `str` | no | Databricks SQL warehouse the connection runs queries on. Required for a `databricks-sql-warehouse` or `databricks-metastore-sql-warehouse` connection. Between 1 and 200 characters. |
| `gcp_secret` | `str` | no | Name of the GCP Secret Manager secret holding the connection's credentials. Between 1 and 200 characters. |

### Response

Returns the credentials after the change. Response fields: id, connection_type, storage_type, created_time, bq_project_id, databricks_warehouse_id, gcp_secret.

| Field | Description |
|---|---|
| `id` | Unique identifier of the credentials. |
| `connection_type` | The connection type the credentials are for, such as `snowflake`. Fixed once created. |
| `storage_type` | Where the secret lives. Fixed once created. |
| `created_time` | When the credentials were created. |
| `bq_project_id` | BigQuery project the connection reads from. Null unless set. |
| `databricks_warehouse_id` | Databricks SQL warehouse the connection runs queries on. Null unless set. |
| `gcp_secret` | Name of the GCP Secret Manager secret holding the connection's credentials. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The credentials does not exist, or is not visible to the caller.
- An argument is invalid; the error names the field.
- Monte Carlo is busy or temporarily unavailable; the tool retries once after the wait Monte Carlo asks for.
- An unexpected error prevented the request from being processed.

## `delete_gcp_secret_manager_credentials`: Delete GCP Secret Manager credentials

Delete GCP Secret Manager credentials no connection uses. The secret in GCP is untouched.

- **Effect:** deletes; destructive and idempotent.
- **Pairs with:** `create_gcp_secret_manager_credentials`, `get_gcp_secret_manager_credentials`, `update_gcp_secret_manager_credentials`, `list_credentials`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned by list_credentials. |

### Response

Returns `credentials_id` and `deleted: true` once the credentials is gone.

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The credentials does not exist, or is not visible to the caller.
- The change conflicts with the current state of the credentials.
- Monte Carlo is busy or temporarily unavailable; try again after a moment.
- An unexpected error prevented the request from being processed.

## `get_snowflake_credentials`: Get Snowflake credentials

Get one set of Snowflake credentials, without the key.

An id that does not exist, belongs to another account, or names credentials of another
kind returns 404.

- **Effect:** read-only.
- **Pairs with:** `delete_snowflake_credentials`, `list_credentials`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned by list_credentials. |

### Response

Response fields: id, connection_type, storage_type, created_time, account, user, warehouse.

| Field | Description |
|---|---|
| `id` | Unique identifier of the credentials. |
| `connection_type` | The connection type the credentials are for, such as `snowflake`. Fixed once created. |
| `storage_type` | Where the secret lives. Fixed once created. |
| `created_time` | When the credentials were created. |
| `account` | Snowflake account identifier, without the host suffix. |
| `user` | Snowflake user the key pair belongs to. |
| `warehouse` | Snowflake virtual warehouse queries run in. Null when none is set. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The credentials does not exist, or is not visible to the caller.
- An unexpected error prevented the request from being processed.
- Monte Carlo is busy or temporarily unavailable; try again after a moment.

## `delete_snowflake_credentials`: Delete Snowflake credentials

Delete Snowflake credentials no connection uses. Monte Carlo stops using the stored key. Rotate or revoke the key pair in Snowflake if the key itself must be retired.

- **Effect:** deletes; destructive and idempotent.
- **Pairs with:** `get_snowflake_credentials`, `list_credentials`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned by list_credentials. |

### Response

Returns `credentials_id` and `deleted: true` once the credentials is gone.

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The credentials does not exist, or is not visible to the caller.
- The change conflicts with the current state of the credentials.
- Monte Carlo is busy or temporarily unavailable; try again after a moment.
- An unexpected error prevented the request from being processed.

## `delete_credentials`: Delete credentials

Delete credentials of any kind, by the id list_credentials or a connection returns. Refused while a connection still uses them. Call delete_connection first. Monte Carlo stops using them. Whatever they point at is untouched.

- **Effect:** deletes; destructive and idempotent.
- **Pairs with:** `list_credentials`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned by list_credentials. |

### Response

Returns `credentials_id` and `deleted: true` once the credentials is gone.

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The credentials does not exist, or is not visible to the caller.
- The change conflicts with the current state of the credentials.
- Monte Carlo is busy or temporarily unavailable; try again after a moment.
- An unexpected error prevented the request from being processed.
