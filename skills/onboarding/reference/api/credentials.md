# `credentials` tools

<!-- Rendered from the REST API v2 OpenAPI document by api-codegen; do not edit. -->

Monte Carlo REST API v2 tools of the `credentials` tag, as the Monte Carlo MCP server exposes
them. Each section is one tool; its name is the tool to call.

## `list_credentials`: List credentials

List the credentials in your account, of every kind, a page at a time.

Credentials are returned oldest first. Each entry says what connection type it is for and
where its secret lives; read the typed endpoint for that kind to see its other fields.

- **Effect:** read-only.
- **Pairs with:** `get_azure_dedicated_sql_pool_credentials`, `get_azure_sql_database_credentials`, `get_bigquery_credentials`, `get_clickhouse_credentials`, `get_databricks_metastore_sql_warehouse_credentials`, `get_databricks_sql_warehouse_credentials`, `get_db2_credentials`, `get_looker_git_clone_credentials`, `get_looker_credentials`, `get_mariadb_credentials`, `get_mysql_credentials`, `get_oracle_credentials`, `get_postgres_credentials`, `get_power_bi_credentials`, `get_redshift_credentials`, `get_sap_hana_credentials`, `create_aws_secrets_manager_credentials`, `validate_aws_secrets_manager_credentials`, `get_aws_secrets_manager_credentials`, `create_azure_key_vault_credentials`, `validate_azure_key_vault_credentials`, `get_azure_key_vault_credentials`, `create_env_var_credentials`, `validate_env_var_credentials`, `get_env_var_credentials`, `create_file_credentials`, `validate_file_credentials`, `get_file_credentials`, `create_gcp_secret_manager_credentials`, `validate_gcp_secret_manager_credentials`, `get_gcp_secret_manager_credentials`, `get_snowflake_credentials`, `get_starburst_enterprise_credentials`, `get_starburst_galaxy_credentials`, `get_tableau_credentials`, `get_teradata_credentials`.
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

## `get_azure_dedicated_sql_pool_credentials`: Get Azure Dedicated SQL Pool credentials

Get one set of Azure Dedicated SQL Pool credentials, without the password.

An id that does not exist, belongs to another account, or names credentials of another
kind returns 404.

- **Effect:** read-only.
- **Pairs with:** `delete_azure_dedicated_sql_pool_credentials`, `list_credentials`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned when they are created or listed. |

### Response

Response fields: id, connection_type, storage_type, created_time, host, port, db_name, user.

| Field | Description |
|---|---|
| `id` | Unique identifier of the credentials. |
| `connection_type` | The connection type the credentials are for, such as `snowflake`. Fixed once created. |
| `storage_type` | Where the secret lives. Fixed once created. |
| `created_time` | When the credentials were created. |
| `host` | Hostname of the database endpoint. |
| `port` | Port the database listens on. |
| `db_name` | Database to connect to. |
| `user` | Database user Monte Carlo logs in as. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The credentials does not exist, or is not visible to the caller.
- An unexpected error prevented the request from being processed.
- Monte Carlo is busy or temporarily unavailable; try again after a moment.

## `delete_azure_dedicated_sql_pool_credentials`: Delete Azure Dedicated SQL Pool credentials

Delete Azure Dedicated SQL Pool credentials no connection uses. Monte Carlo stops using the stored password. Change the password in Azure Dedicated SQL Pool if the password itself must be retired.

- **Effect:** deletes; destructive and idempotent.
- **Pairs with:** `get_azure_dedicated_sql_pool_credentials`, `list_credentials`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned when they are created or listed. |

### Response

Returns `credentials_id` and `deleted: true` once the credentials is gone.

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The credentials does not exist, or is not visible to the caller.
- The change conflicts with the current state of the credentials.
- Monte Carlo is busy or temporarily unavailable; try again after a moment.
- An unexpected error prevented the request from being processed.

## `get_azure_sql_database_credentials`: Get Azure SQL Database credentials

Get one set of Azure SQL Database credentials, without the password.

An id that does not exist, belongs to another account, or names credentials of another
kind returns 404.

- **Effect:** read-only.
- **Pairs with:** `delete_azure_sql_database_credentials`, `list_credentials`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned when they are created or listed. |

### Response

Response fields: id, connection_type, storage_type, created_time, host, port, db_name, user.

| Field | Description |
|---|---|
| `id` | Unique identifier of the credentials. |
| `connection_type` | The connection type the credentials are for, such as `snowflake`. Fixed once created. |
| `storage_type` | Where the secret lives. Fixed once created. |
| `created_time` | When the credentials were created. |
| `host` | Hostname of the database endpoint. |
| `port` | Port the database listens on. |
| `db_name` | Database to connect to. |
| `user` | Database user Monte Carlo logs in as. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The credentials does not exist, or is not visible to the caller.
- An unexpected error prevented the request from being processed.
- Monte Carlo is busy or temporarily unavailable; try again after a moment.

## `delete_azure_sql_database_credentials`: Delete Azure SQL Database credentials

Delete Azure SQL Database credentials no connection uses. Monte Carlo stops using the stored password. Change the password in Azure SQL Database if the password itself must be retired.

- **Effect:** deletes; destructive and idempotent.
- **Pairs with:** `get_azure_sql_database_credentials`, `list_credentials`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned when they are created or listed. |

### Response

Returns `credentials_id` and `deleted: true` once the credentials is gone.

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The credentials does not exist, or is not visible to the caller.
- The change conflicts with the current state of the credentials.
- Monte Carlo is busy or temporarily unavailable; try again after a moment.
- An unexpected error prevented the request from being processed.

## `get_bigquery_credentials`: Get BigQuery credentials

Get one set of BigQuery credentials, without the key.

An id that does not exist, belongs to another account, or names credentials of another
kind returns 404.

- **Effect:** read-only.
- **Pairs with:** `delete_bigquery_credentials`, `list_credentials`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned when they are created or listed. |

### Response

Response fields: id, connection_type, storage_type, created_time, project_id, client_email.

| Field | Description |
|---|---|
| `id` | Unique identifier of the credentials. |
| `connection_type` | The connection type the credentials are for, such as `snowflake`. Fixed once created. |
| `storage_type` | Where the secret lives. Fixed once created. |
| `created_time` | When the credentials were created. |
| `project_id` | Google Cloud project the service account belongs to. |
| `client_email` | Email address of the service account. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The credentials does not exist, or is not visible to the caller.
- An unexpected error prevented the request from being processed.
- Monte Carlo is busy or temporarily unavailable; try again after a moment.

## `delete_bigquery_credentials`: Delete BigQuery credentials

Delete BigQuery credentials no connection uses. Monte Carlo stops using the stored service account key. Revoke the key in Google Cloud if the key itself must be retired.

- **Effect:** deletes; destructive and idempotent.
- **Pairs with:** `get_bigquery_credentials`, `list_credentials`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned when they are created or listed. |

### Response

Returns `credentials_id` and `deleted: true` once the credentials is gone.

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The credentials does not exist, or is not visible to the caller.
- The change conflicts with the current state of the credentials.
- Monte Carlo is busy or temporarily unavailable; try again after a moment.
- An unexpected error prevented the request from being processed.

## `get_clickhouse_credentials`: Get ClickHouse credentials

Get one set of ClickHouse credentials, without the password.

An id that does not exist, belongs to another account, or names credentials of another
kind returns 404.

- **Effect:** read-only.
- **Pairs with:** `delete_clickhouse_credentials`, `list_credentials`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned when they are created or listed. |

### Response

Response fields: id, connection_type, storage_type, created_time, host, port, db_name, user.

| Field | Description |
|---|---|
| `id` | Unique identifier of the credentials. |
| `connection_type` | The connection type the credentials are for, such as `snowflake`. Fixed once created. |
| `storage_type` | Where the secret lives. Fixed once created. |
| `created_time` | When the credentials were created. |
| `host` | Hostname of the database endpoint. |
| `port` | Port the database listens on. |
| `db_name` | Database to connect to. Null when none is set. |
| `user` | Database user Monte Carlo logs in as. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The credentials does not exist, or is not visible to the caller.
- An unexpected error prevented the request from being processed.
- Monte Carlo is busy or temporarily unavailable; try again after a moment.

## `delete_clickhouse_credentials`: Delete ClickHouse credentials

Delete ClickHouse credentials no connection uses. Monte Carlo stops using the stored password. Change the password in ClickHouse if the password itself must be retired.

- **Effect:** deletes; destructive and idempotent.
- **Pairs with:** `get_clickhouse_credentials`, `list_credentials`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned when they are created or listed. |

### Response

Returns `credentials_id` and `deleted: true` once the credentials is gone.

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The credentials does not exist, or is not visible to the caller.
- The change conflicts with the current state of the credentials.
- Monte Carlo is busy or temporarily unavailable; try again after a moment.
- An unexpected error prevented the request from being processed.

## `get_databricks_metastore_sql_warehouse_credentials`: Get Databricks metadata collection credentials

Get one set of Databricks metadata collection credentials, without the secrets.

An id that does not exist, belongs to another account, or names credentials of another
kind returns 404.

- **Effect:** read-only.
- **Pairs with:** `delete_databricks_metastore_sql_warehouse_credentials`, `list_credentials`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned when they are created or listed. |

### Response

Response fields: id, connection_type, storage_type, created_time, workspace_url, sql_warehouse_id, workspace_id, oauth_client_id, azure_tenant_id, azure_workspace_resource_id.

| Field | Description |
|---|---|
| `id` | Unique identifier of the credentials. |
| `connection_type` | The connection type the credentials are for, such as `snowflake`. Fixed once created. |
| `storage_type` | Where the secret lives. Fixed once created. |
| `created_time` | When the credentials were created. |
| `workspace_url` | URL of the Databricks workspace, or its host name. |
| `sql_warehouse_id` | ID of the Databricks SQL warehouse the connection runs on. |
| `workspace_id` | ID of the Databricks workspace. |
| `oauth_client_id` | Client ID of the OAuth service principal. Null for token credentials. |
| `azure_tenant_id` | Microsoft Entra ID tenant of the service principal. Null unless set. |
| `azure_workspace_resource_id` | Azure resource ID of the workspace. Null unless set. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The credentials does not exist, or is not visible to the caller.
- An unexpected error prevented the request from being processed.
- Monte Carlo is busy or temporarily unavailable; try again after a moment.

## `delete_databricks_metastore_sql_warehouse_credentials`: Delete Databricks metadata collection credentials

Delete Databricks metadata collection credentials no connection uses. Monte Carlo stops using the stored token or OAuth secret. Revoke it in Databricks, or in Microsoft Entra ID for a service principal Azure manages, if the secret itself must be retired.

- **Effect:** deletes; destructive and idempotent.
- **Pairs with:** `get_databricks_metastore_sql_warehouse_credentials`, `list_credentials`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned when they are created or listed. |

### Response

Returns `credentials_id` and `deleted: true` once the credentials is gone.

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The credentials does not exist, or is not visible to the caller.
- The change conflicts with the current state of the credentials.
- Monte Carlo is busy or temporarily unavailable; try again after a moment.
- An unexpected error prevented the request from being processed.

## `get_databricks_sql_warehouse_credentials`: Get Databricks query credentials

Get one set of Databricks query credentials, without the secrets.

An id that does not exist, belongs to another account, or names credentials of another
kind returns 404.

- **Effect:** read-only.
- **Pairs with:** `delete_databricks_sql_warehouse_credentials`, `list_credentials`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned when they are created or listed. |

### Response

Response fields: id, connection_type, storage_type, created_time, workspace_url, sql_warehouse_id, workspace_id, oauth_client_id, azure_tenant_id, azure_workspace_resource_id.

| Field | Description |
|---|---|
| `id` | Unique identifier of the credentials. |
| `connection_type` | The connection type the credentials are for, such as `snowflake`. Fixed once created. |
| `storage_type` | Where the secret lives. Fixed once created. |
| `created_time` | When the credentials were created. |
| `workspace_url` | URL of the Databricks workspace, or its host name. |
| `sql_warehouse_id` | ID of the Databricks SQL warehouse the connection runs on. |
| `workspace_id` | ID of the Databricks workspace. Null unless set. |
| `oauth_client_id` | Client ID of the OAuth service principal. Null for token credentials. |
| `azure_tenant_id` | Microsoft Entra ID tenant of the service principal. Null unless set. |
| `azure_workspace_resource_id` | Azure resource ID of the workspace. Null unless set. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The credentials does not exist, or is not visible to the caller.
- An unexpected error prevented the request from being processed.
- Monte Carlo is busy or temporarily unavailable; try again after a moment.

## `delete_databricks_sql_warehouse_credentials`: Delete Databricks query credentials

Delete Databricks query credentials no connection uses. Monte Carlo stops using the stored token or OAuth secret. Revoke it in Databricks, or in Microsoft Entra ID for a service principal Azure manages, if the secret itself must be retired.

- **Effect:** deletes; destructive and idempotent.
- **Pairs with:** `get_databricks_sql_warehouse_credentials`, `list_credentials`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned when they are created or listed. |

### Response

Returns `credentials_id` and `deleted: true` once the credentials is gone.

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The credentials does not exist, or is not visible to the caller.
- The change conflicts with the current state of the credentials.
- Monte Carlo is busy or temporarily unavailable; try again after a moment.
- An unexpected error prevented the request from being processed.

## `get_db2_credentials`: Get Db2 credentials

Get one set of Db2 credentials, without the password.

An id that does not exist, belongs to another account, or names credentials of another
kind returns 404.

- **Effect:** read-only.
- **Pairs with:** `delete_db2_credentials`, `list_credentials`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned when they are created or listed. |

### Response

Response fields: id, connection_type, storage_type, created_time, host, port, db_name, user, ssl_ca_data, ssl_disabled.

| Field | Description |
|---|---|
| `id` | Unique identifier of the credentials. |
| `connection_type` | The connection type the credentials are for, such as `snowflake`. Fixed once created. |
| `storage_type` | Where the secret lives. Fixed once created. |
| `created_time` | When the credentials were created. |
| `host` | Hostname of the database endpoint. |
| `port` | Port the database listens on. |
| `db_name` | Database to connect to. Null when none is set. |
| `user` | Database user Monte Carlo logs in as. |
| `ssl_ca_data` | PEM text of the CA certificate the server's certificate is checked against. Null when none is set. |
| `ssl_disabled` | Connect without TLS. Null when unset. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The credentials does not exist, or is not visible to the caller.
- An unexpected error prevented the request from being processed.
- Monte Carlo is busy or temporarily unavailable; try again after a moment.

## `delete_db2_credentials`: Delete Db2 credentials

Delete Db2 credentials no connection uses. Monte Carlo stops using the stored password. Change the password in Db2 if the password itself must be retired.

- **Effect:** deletes; destructive and idempotent.
- **Pairs with:** `get_db2_credentials`, `list_credentials`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned when they are created or listed. |

### Response

Returns `credentials_id` and `deleted: true` once the credentials is gone.

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The credentials does not exist, or is not visible to the caller.
- The change conflicts with the current state of the credentials.
- Monte Carlo is busy or temporarily unavailable; try again after a moment.
- An unexpected error prevented the request from being processed.

## `get_looker_git_clone_credentials`: Get LookML repository credentials

Get one set of LookML repository credentials, without the token or the SSH key.

An id that does not exist, belongs to another account, or names credentials of another
kind returns 404.

- **Effect:** read-only.
- **Pairs with:** `delete_looker_git_clone_credentials`, `list_credentials`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned by list_credentials. |

### Response

Response fields: id, connection_type, storage_type, created_time, repo_url, username, ssl_ca_data, ssl_skip_cert_verification.

| Field | Description |
|---|---|
| `id` | Unique identifier of the credentials. |
| `connection_type` | The connection type the credentials are for, such as `snowflake`. Fixed once created. |
| `storage_type` | Where the secret lives. Fixed once created. |
| `created_time` | When the credentials were created. |
| `repo_url` | Clone URL of the LookML repository, over HTTPS or SSH. |
| `username` | Git user. Null for an SSH clone. |
| `ssl_ca_data` | PEM certificate of the CA that signed the git server's certificate. Null unless set. |
| `ssl_skip_cert_verification` | Skip verifying the git server's TLS certificate. Null unless set. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The credentials does not exist, or is not visible to the caller.
- An unexpected error prevented the request from being processed.
- Monte Carlo is busy or temporarily unavailable; try again after a moment.

## `delete_looker_git_clone_credentials`: Delete LookML repository credentials

Delete LookML repository credentials no connection uses. Monte Carlo stops using the stored token or SSH key. Revoke it on the git server if it must be retired.

- **Effect:** deletes; destructive and idempotent.
- **Pairs with:** `get_looker_git_clone_credentials`, `list_credentials`.

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

## `get_looker_credentials`: Get Looker credentials

Get one set of Looker API credentials, without the client secret.

An id that does not exist, belongs to another account, or names credentials of another
kind returns 404.

- **Effect:** read-only.
- **Pairs with:** `delete_looker_credentials`, `list_credentials`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned by list_credentials. |

### Response

Response fields: id, connection_type, storage_type, created_time, base_url, api_client_id, verify_ssl.

| Field | Description |
|---|---|
| `id` | Unique identifier of the credentials. |
| `connection_type` | The connection type the credentials are for, such as `snowflake`. Fixed once created. |
| `storage_type` | Where the secret lives. Fixed once created. |
| `created_time` | When the credentials were created. |
| `base_url` | URL of the Looker API, such as https://acme.cloud.looker.com. |
| `api_client_id` | Client ID of the Looker API key. |
| `verify_ssl` | Whether to verify Looker's TLS certificate. Verified when left out. Null unless set. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The credentials does not exist, or is not visible to the caller.
- An unexpected error prevented the request from being processed.
- Monte Carlo is busy or temporarily unavailable; try again after a moment.

## `delete_looker_credentials`: Delete Looker credentials

Delete Looker credentials no connection uses. Monte Carlo stops using the stored client secret. Delete the API key in Looker if the secret itself must be retired.

- **Effect:** deletes; destructive and idempotent.
- **Pairs with:** `get_looker_credentials`, `list_credentials`.

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

## `get_mariadb_credentials`: Get MariaDB credentials

Get one set of MariaDB credentials, without the password.

An id that does not exist, belongs to another account, or names credentials of another
kind returns 404.

- **Effect:** read-only.
- **Pairs with:** `delete_mariadb_credentials`, `list_credentials`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned when they are created or listed. |

### Response

Response fields: id, connection_type, storage_type, created_time, host, port, db_name, user.

| Field | Description |
|---|---|
| `id` | Unique identifier of the credentials. |
| `connection_type` | The connection type the credentials are for, such as `snowflake`. Fixed once created. |
| `storage_type` | Where the secret lives. Fixed once created. |
| `created_time` | When the credentials were created. |
| `host` | Hostname of the database endpoint. |
| `port` | Port the database listens on. |
| `db_name` | Database to connect to. Null when none is set. |
| `user` | Database user Monte Carlo logs in as. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The credentials does not exist, or is not visible to the caller.
- An unexpected error prevented the request from being processed.
- Monte Carlo is busy or temporarily unavailable; try again after a moment.

## `delete_mariadb_credentials`: Delete MariaDB credentials

Delete MariaDB credentials no connection uses. Monte Carlo stops using the stored password. Change the password in MariaDB if the password itself must be retired.

- **Effect:** deletes; destructive and idempotent.
- **Pairs with:** `get_mariadb_credentials`, `list_credentials`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned when they are created or listed. |

### Response

Returns `credentials_id` and `deleted: true` once the credentials is gone.

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The credentials does not exist, or is not visible to the caller.
- The change conflicts with the current state of the credentials.
- Monte Carlo is busy or temporarily unavailable; try again after a moment.
- An unexpected error prevented the request from being processed.

## `get_mysql_credentials`: Get MySQL credentials

Get one set of MySQL credentials, without the password.

An id that does not exist, belongs to another account, or names credentials of another
kind returns 404.

- **Effect:** read-only.
- **Pairs with:** `delete_mysql_credentials`, `list_credentials`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned when they are created or listed. |

### Response

Response fields: id, connection_type, storage_type, created_time, host, port, db_name, user, ssl_ca_data, ssl_disabled, ssl_verify_cert, ssl_verify_identity, ssl_skip_cert_verification.

| Field | Description |
|---|---|
| `id` | Unique identifier of the credentials. |
| `connection_type` | The connection type the credentials are for, such as `snowflake`. Fixed once created. |
| `storage_type` | Where the secret lives. Fixed once created. |
| `created_time` | When the credentials were created. |
| `host` | Hostname of the database endpoint. |
| `port` | Port the database listens on. |
| `db_name` | Database to connect to. Null when none is set. |
| `user` | Database user Monte Carlo logs in as. |
| `ssl_ca_data` | PEM text of the CA certificate the server's certificate is checked against. Null when none is set. |
| `ssl_disabled` | Connect without TLS. Null when unset. |
| `ssl_verify_cert` | Check the server's certificate against the CA. Null when unset. |
| `ssl_verify_identity` | Check the certificate and that it names the host. Null when unset. |
| `ssl_skip_cert_verification` | Encrypt the connection without checking the server's certificate. Null when unset. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The credentials does not exist, or is not visible to the caller.
- An unexpected error prevented the request from being processed.
- Monte Carlo is busy or temporarily unavailable; try again after a moment.

## `delete_mysql_credentials`: Delete MySQL credentials

Delete MySQL credentials no connection uses. Monte Carlo stops using the stored password. Change the password in MySQL if the password itself must be retired.

- **Effect:** deletes; destructive and idempotent.
- **Pairs with:** `get_mysql_credentials`, `list_credentials`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned when they are created or listed. |

### Response

Returns `credentials_id` and `deleted: true` once the credentials is gone.

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The credentials does not exist, or is not visible to the caller.
- The change conflicts with the current state of the credentials.
- Monte Carlo is busy or temporarily unavailable; try again after a moment.
- An unexpected error prevented the request from being processed.

## `get_oracle_credentials`: Get Oracle credentials

Get one set of Oracle credentials, without the password.

An id that does not exist, belongs to another account, or names credentials of another
kind returns 404.

- **Effect:** read-only.
- **Pairs with:** `delete_oracle_credentials`, `list_credentials`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned when they are created or listed. |

### Response

Response fields: id, connection_type, storage_type, created_time, host, port, db_name, user, ssl_ca_data, ssl_disabled, ssl_verify_cert, ssl_verify_identity, ssl_skip_cert_verification.

| Field | Description |
|---|---|
| `id` | Unique identifier of the credentials. |
| `connection_type` | The connection type the credentials are for, such as `snowflake`. Fixed once created. |
| `storage_type` | Where the secret lives. Fixed once created. |
| `created_time` | When the credentials were created. |
| `host` | Hostname of the database endpoint. |
| `port` | Port the database listens on. |
| `db_name` | Database to connect to. |
| `user` | Database user Monte Carlo logs in as. |
| `ssl_ca_data` | PEM text of the CA certificate the server's certificate is checked against. Null when none is set. |
| `ssl_disabled` | Connect without TLS. Null when unset. |
| `ssl_verify_cert` | Check the server's certificate against the CA. Null when unset. |
| `ssl_verify_identity` | Check the certificate and that it names the host. Null when unset. |
| `ssl_skip_cert_verification` | Encrypt the connection without checking the server's certificate. Null when unset. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The credentials does not exist, or is not visible to the caller.
- An unexpected error prevented the request from being processed.
- Monte Carlo is busy or temporarily unavailable; try again after a moment.

## `delete_oracle_credentials`: Delete Oracle credentials

Delete Oracle credentials no connection uses. Monte Carlo stops using the stored password. Change the password in Oracle if the password itself must be retired.

- **Effect:** deletes; destructive and idempotent.
- **Pairs with:** `get_oracle_credentials`, `list_credentials`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned when they are created or listed. |

### Response

Returns `credentials_id` and `deleted: true` once the credentials is gone.

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The credentials does not exist, or is not visible to the caller.
- The change conflicts with the current state of the credentials.
- Monte Carlo is busy or temporarily unavailable; try again after a moment.
- An unexpected error prevented the request from being processed.

## `get_postgres_credentials`: Get PostgreSQL credentials

Get one set of PostgreSQL credentials, without the password.

An id that does not exist, belongs to another account, or names credentials of another
kind returns 404.

- **Effect:** read-only.
- **Pairs with:** `delete_postgres_credentials`, `list_credentials`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned when they are created or listed. |

### Response

Response fields: id, connection_type, storage_type, created_time, host, port, db_name, user, ssl_ca_data, ssl_disabled, ssl_verify_cert, ssl_verify_identity, ssl_skip_cert_verification, rds_proxy.

| Field | Description |
|---|---|
| `id` | Unique identifier of the credentials. |
| `connection_type` | The connection type the credentials are for, such as `snowflake`. Fixed once created. |
| `storage_type` | Where the secret lives. Fixed once created. |
| `created_time` | When the credentials were created. |
| `host` | Hostname of the database endpoint. |
| `port` | Port the database listens on. |
| `db_name` | Database to connect to. |
| `user` | Database user Monte Carlo logs in as. |
| `ssl_ca_data` | PEM text of the CA certificate the server's certificate is checked against. Null when none is set. |
| `ssl_disabled` | Connect without TLS. Null when unset. |
| `ssl_verify_cert` | Check the server's certificate against the CA. Null when unset. |
| `ssl_verify_identity` | Check the certificate and that it names the host. Null when unset. |
| `ssl_skip_cert_verification` | Encrypt the connection without checking the server's certificate. Null when unset. |
| `rds_proxy` | Whether `host` is an Amazon RDS Proxy endpoint. Null when unset. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The credentials does not exist, or is not visible to the caller.
- An unexpected error prevented the request from being processed.
- Monte Carlo is busy or temporarily unavailable; try again after a moment.

## `delete_postgres_credentials`: Delete PostgreSQL credentials

Delete PostgreSQL credentials no connection uses. Monte Carlo stops using the stored password. Change the password in PostgreSQL if the password itself must be retired.

- **Effect:** deletes; destructive and idempotent.
- **Pairs with:** `get_postgres_credentials`, `list_credentials`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned when they are created or listed. |

### Response

Returns `credentials_id` and `deleted: true` once the credentials is gone.

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The credentials does not exist, or is not visible to the caller.
- The change conflicts with the current state of the credentials.
- Monte Carlo is busy or temporarily unavailable; try again after a moment.
- An unexpected error prevented the request from being processed.

## `get_power_bi_credentials`: Get Power BI credentials

Get one set of Power BI credentials, without the client secret or the password.

An id that does not exist, belongs to another account, or names credentials of another
kind returns 404.

- **Effect:** read-only.
- **Pairs with:** `delete_power_bi_credentials`, `list_credentials`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned by list_credentials. |

### Response

Response fields: id, connection_type, storage_type, created_time, tenant_id, app_client_id, auth_mode, username.

| Field | Description |
|---|---|
| `id` | Unique identifier of the credentials. |
| `connection_type` | The connection type the credentials are for, such as `snowflake`. Fixed once created. |
| `storage_type` | Where the secret lives. Fixed once created. |
| `created_time` | When the credentials were created. |
| `tenant_id` | Microsoft Entra ID tenant the Power BI service belongs to. |
| `app_client_id` | Client ID of the Entra ID app registration Monte Carlo signs in with. |
| `auth_mode` | How Monte Carlo signs in. `service_principal` takes `app_client_secret`. `primary_user` takes `username` and `password`. |
| `username` | User Monte Carlo signs in as. Null unless set. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The credentials does not exist, or is not visible to the caller.
- An unexpected error prevented the request from being processed.
- Monte Carlo is busy or temporarily unavailable; try again after a moment.

## `delete_power_bi_credentials`: Delete Power BI credentials

Delete Power BI credentials no connection uses. Monte Carlo stops using the stored client secret or password. Rotate it in Microsoft Entra ID if it must be retired.

- **Effect:** deletes; destructive and idempotent.
- **Pairs with:** `get_power_bi_credentials`, `list_credentials`.

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

## `get_redshift_credentials`: Get Redshift credentials

Get one set of Redshift credentials, without the password.

An id that does not exist, belongs to another account, or names credentials of another
kind returns 404.

- **Effect:** read-only.
- **Pairs with:** `delete_redshift_credentials`, `list_credentials`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned when they are created or listed. |

### Response

Response fields: id, connection_type, storage_type, created_time, host, port, db_name, user, ssl_ca_data, ssl_disabled, ssl_verify_cert, ssl_verify_identity, ssl_skip_cert_verification.

| Field | Description |
|---|---|
| `id` | Unique identifier of the credentials. |
| `connection_type` | The connection type the credentials are for, such as `snowflake`. Fixed once created. |
| `storage_type` | Where the secret lives. Fixed once created. |
| `created_time` | When the credentials were created. |
| `host` | Hostname of the database endpoint. |
| `port` | Port the database listens on. |
| `db_name` | Redshift database to connect to. |
| `user` | Database user Monte Carlo logs in as. |
| `ssl_ca_data` | PEM text of the CA certificate the server's certificate is checked against. Null when none is set. |
| `ssl_disabled` | Connect without TLS. Null when unset. |
| `ssl_verify_cert` | Check the server's certificate against the CA. Null when unset. |
| `ssl_verify_identity` | Check the certificate and that it names the host. Null when unset. |
| `ssl_skip_cert_verification` | Encrypt the connection without checking the server's certificate. Null when unset. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The credentials does not exist, or is not visible to the caller.
- An unexpected error prevented the request from being processed.
- Monte Carlo is busy or temporarily unavailable; try again after a moment.

## `delete_redshift_credentials`: Delete Redshift credentials

Delete Redshift credentials no connection uses. Monte Carlo stops using the stored password. Change the password in Redshift if the password itself must be retired.

- **Effect:** deletes; destructive and idempotent.
- **Pairs with:** `get_redshift_credentials`, `list_credentials`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned when they are created or listed. |

### Response

Returns `credentials_id` and `deleted: true` once the credentials is gone.

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The credentials does not exist, or is not visible to the caller.
- The change conflicts with the current state of the credentials.
- Monte Carlo is busy or temporarily unavailable; try again after a moment.
- An unexpected error prevented the request from being processed.

## `get_sap_hana_credentials`: Get SAP HANA credentials

Get one set of SAP HANA credentials, without the password.

An id that does not exist, belongs to another account, or names credentials of another
kind returns 404.

- **Effect:** read-only.
- **Pairs with:** `delete_sap_hana_credentials`, `list_credentials`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned when they are created or listed. |

### Response

Response fields: id, connection_type, storage_type, created_time, host, port, db_name, user.

| Field | Description |
|---|---|
| `id` | Unique identifier of the credentials. |
| `connection_type` | The connection type the credentials are for, such as `snowflake`. Fixed once created. |
| `storage_type` | Where the secret lives. Fixed once created. |
| `created_time` | When the credentials were created. |
| `host` | Hostname of the database endpoint. |
| `port` | Port the database listens on. |
| `db_name` | Database to connect to. |
| `user` | Database user Monte Carlo logs in as. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The credentials does not exist, or is not visible to the caller.
- An unexpected error prevented the request from being processed.
- Monte Carlo is busy or temporarily unavailable; try again after a moment.

## `delete_sap_hana_credentials`: Delete SAP HANA credentials

Delete SAP HANA credentials no connection uses. Monte Carlo stops using the stored password. Change the password in SAP HANA if the password itself must be retired.

- **Effect:** deletes; destructive and idempotent.
- **Pairs with:** `get_sap_hana_credentials`, `list_credentials`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned when they are created or listed. |

### Response

Returns `credentials_id` and `deleted: true` once the credentials is gone.

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The credentials does not exist, or is not visible to the caller.
- The change conflicts with the current state of the credentials.
- Monte Carlo is busy or temporarily unavailable; try again after a moment.
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
| `sql_warehouse_id` | `str` | no | Databricks SQL warehouse the connection runs queries on. Required for a `databricks-sql-warehouse` or `databricks-metastore-sql-warehouse` connection. Between 1 and 200 characters. |
| `aws_region` | `str` | no | AWS region of the secret. Omit it to use the deployment's own region. Between 1 and 200 characters. |
| `assumable_role` | `str` | no | ARN of a role the deployment assumes to read the secret. Omit it to read as itself. Between 1 and 2048 characters. |
| `external_id` | `str` | no | External id the assumed role's trust policy requires, if it requires one. Between 1 and 1224 characters. |

### Response

Returns the new credentials. Response fields: id, connection_type, storage_type, created_time, bq_project_id, sql_warehouse_id, aws_secret, aws_region, assumable_role, external_id.

| Field | Description |
|---|---|
| `id` | Unique identifier of the credentials. |
| `connection_type` | The connection type the credentials are for, such as `snowflake`. Fixed once created. |
| `storage_type` | Where the secret lives. Fixed once created. |
| `created_time` | When the credentials were created. |
| `bq_project_id` | BigQuery project the connection reads from. Null unless set. |
| `sql_warehouse_id` | Databricks SQL warehouse the connection runs queries on. Null unless set. |
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
| `sql_warehouse_id` | `str` | no | Databricks SQL warehouse the connection runs queries on. Required for a `databricks-sql-warehouse` or `databricks-metastore-sql-warehouse` connection. Between 1 and 200 characters. |
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
| `validations` | The run's validations, in the order they are declared. A validation stays `pending` until it starts. It can wait on a prerequisite, or for earlier validations to finish. A read with `since` lists only the validations that changed after that revision, and may list none. |

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
| `credentials_id` | `str` | yes | Id of the credentials, as returned when they are created or listed. |

### Response

Response fields: id, connection_type, storage_type, created_time, bq_project_id, sql_warehouse_id, aws_secret, aws_region, assumable_role, external_id.

| Field | Description |
|---|---|
| `id` | Unique identifier of the credentials. |
| `connection_type` | The connection type the credentials are for, such as `snowflake`. Fixed once created. |
| `storage_type` | Where the secret lives. Fixed once created. |
| `created_time` | When the credentials were created. |
| `bq_project_id` | BigQuery project the connection reads from. Null unless set. |
| `sql_warehouse_id` | Databricks SQL warehouse the connection runs queries on. Null unless set. |
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
| `credentials_id` | `str` | yes | Id of the credentials, as returned when they are created or listed. |
| `bq_project_id` | `str` | no | BigQuery project the connection reads from. Only for a BigQuery connection. Between 1 and 200 characters. |
| `sql_warehouse_id` | `str` | no | Databricks SQL warehouse the connection runs queries on. Required for a `databricks-sql-warehouse` or `databricks-metastore-sql-warehouse` connection. Between 1 and 200 characters. |
| `aws_secret` | `str` | no | Name or ARN of the AWS Secrets Manager secret holding the connection's credentials. Between 1 and 2048 characters. |
| `aws_region` | `str` | no | AWS region of the secret. Omit it to use the deployment's own region. Between 1 and 200 characters. |
| `assumable_role` | `str` | no | ARN of a role the deployment assumes to read the secret. Omit it to read as itself. Between 1 and 2048 characters. |
| `external_id` | `str` | no | External id the assumed role's trust policy requires, if it requires one. Between 1 and 1224 characters. |

### Response

Returns the credentials after the change. Response fields: id, connection_type, storage_type, created_time, bq_project_id, sql_warehouse_id, aws_secret, aws_region, assumable_role, external_id.

| Field | Description |
|---|---|
| `id` | Unique identifier of the credentials. |
| `connection_type` | The connection type the credentials are for, such as `snowflake`. Fixed once created. |
| `storage_type` | Where the secret lives. Fixed once created. |
| `created_time` | When the credentials were created. |
| `bq_project_id` | BigQuery project the connection reads from. Null unless set. |
| `sql_warehouse_id` | Databricks SQL warehouse the connection runs queries on. Null unless set. |
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
| `credentials_id` | `str` | yes | Id of the credentials, as returned when they are created or listed. |

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
| `sql_warehouse_id` | `str` | no | Databricks SQL warehouse the connection runs queries on. Required for a `databricks-sql-warehouse` or `databricks-metastore-sql-warehouse` connection. Between 1 and 200 characters. |
| `akv_vault_name` | `str` | no | Name of the key vault. Send this, `akv_vault_url`, or both. Between 1 and 200 characters. |
| `akv_vault_url` | `str` | no | URL of the key vault. Send this, `akv_vault_name`, or both. Between 1 and 2048 characters. |

### Response

Returns the new credentials. Response fields: id, connection_type, storage_type, created_time, bq_project_id, sql_warehouse_id, akv_secret, akv_vault_name, akv_vault_url.

| Field | Description |
|---|---|
| `id` | Unique identifier of the credentials. |
| `connection_type` | The connection type the credentials are for, such as `snowflake`. Fixed once created. |
| `storage_type` | Where the secret lives. Fixed once created. |
| `created_time` | When the credentials were created. |
| `bq_project_id` | BigQuery project the connection reads from. Null unless set. |
| `sql_warehouse_id` | Databricks SQL warehouse the connection runs queries on. Null unless set. |
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
| `sql_warehouse_id` | `str` | no | Databricks SQL warehouse the connection runs queries on. Required for a `databricks-sql-warehouse` or `databricks-metastore-sql-warehouse` connection. Between 1 and 200 characters. |
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
| `validations` | The run's validations, in the order they are declared. A validation stays `pending` until it starts. It can wait on a prerequisite, or for earlier validations to finish. A read with `since` lists only the validations that changed after that revision, and may list none. |

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
| `credentials_id` | `str` | yes | Id of the credentials, as returned when they are created or listed. |

### Response

Response fields: id, connection_type, storage_type, created_time, bq_project_id, sql_warehouse_id, akv_secret, akv_vault_name, akv_vault_url.

| Field | Description |
|---|---|
| `id` | Unique identifier of the credentials. |
| `connection_type` | The connection type the credentials are for, such as `snowflake`. Fixed once created. |
| `storage_type` | Where the secret lives. Fixed once created. |
| `created_time` | When the credentials were created. |
| `bq_project_id` | BigQuery project the connection reads from. Null unless set. |
| `sql_warehouse_id` | Databricks SQL warehouse the connection runs queries on. Null unless set. |
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
| `credentials_id` | `str` | yes | Id of the credentials, as returned when they are created or listed. |
| `bq_project_id` | `str` | no | BigQuery project the connection reads from. Only for a BigQuery connection. Between 1 and 200 characters. |
| `sql_warehouse_id` | `str` | no | Databricks SQL warehouse the connection runs queries on. Required for a `databricks-sql-warehouse` or `databricks-metastore-sql-warehouse` connection. Between 1 and 200 characters. |
| `akv_secret` | `str` | no | Name of the Azure Key Vault secret holding the connection's credentials. Between 1 and 200 characters. |
| `akv_vault_name` | `str` | no | Name of the key vault. Send this, `akv_vault_url`, or both. Between 1 and 200 characters. |
| `akv_vault_url` | `str` | no | URL of the key vault. Send this, `akv_vault_name`, or both. Between 1 and 2048 characters. |

### Response

Returns the credentials after the change. Response fields: id, connection_type, storage_type, created_time, bq_project_id, sql_warehouse_id, akv_secret, akv_vault_name, akv_vault_url.

| Field | Description |
|---|---|
| `id` | Unique identifier of the credentials. |
| `connection_type` | The connection type the credentials are for, such as `snowflake`. Fixed once created. |
| `storage_type` | Where the secret lives. Fixed once created. |
| `created_time` | When the credentials were created. |
| `bq_project_id` | BigQuery project the connection reads from. Null unless set. |
| `sql_warehouse_id` | Databricks SQL warehouse the connection runs queries on. Null unless set. |
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
| `credentials_id` | `str` | yes | Id of the credentials, as returned when they are created or listed. |

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
| `sql_warehouse_id` | `str` | no | Databricks SQL warehouse the connection runs queries on. Required for a `databricks-sql-warehouse` or `databricks-metastore-sql-warehouse` connection. Between 1 and 200 characters. |
| `kms_key_id` | `str` | no | AWS KMS key the variable's value is encrypted with. Omit it for a value stored in the clear. Between 1 and 200 characters. |

### Response

Returns the new credentials. Response fields: id, connection_type, storage_type, created_time, bq_project_id, sql_warehouse_id, env_var_name, kms_key_id.

| Field | Description |
|---|---|
| `id` | Unique identifier of the credentials. |
| `connection_type` | The connection type the credentials are for, such as `snowflake`. Fixed once created. |
| `storage_type` | Where the secret lives. Fixed once created. |
| `created_time` | When the credentials were created. |
| `bq_project_id` | BigQuery project the connection reads from. Null unless set. |
| `sql_warehouse_id` | Databricks SQL warehouse the connection runs queries on. Null unless set. |
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
| `sql_warehouse_id` | `str` | no | Databricks SQL warehouse the connection runs queries on. Required for a `databricks-sql-warehouse` or `databricks-metastore-sql-warehouse` connection. Between 1 and 200 characters. |
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
| `validations` | The run's validations, in the order they are declared. A validation stays `pending` until it starts. It can wait on a prerequisite, or for earlier validations to finish. A read with `since` lists only the validations that changed after that revision, and may list none. |

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
| `credentials_id` | `str` | yes | Id of the credentials, as returned when they are created or listed. |

### Response

Response fields: id, connection_type, storage_type, created_time, bq_project_id, sql_warehouse_id, env_var_name, kms_key_id.

| Field | Description |
|---|---|
| `id` | Unique identifier of the credentials. |
| `connection_type` | The connection type the credentials are for, such as `snowflake`. Fixed once created. |
| `storage_type` | Where the secret lives. Fixed once created. |
| `created_time` | When the credentials were created. |
| `bq_project_id` | BigQuery project the connection reads from. Null unless set. |
| `sql_warehouse_id` | Databricks SQL warehouse the connection runs queries on. Null unless set. |
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
| `credentials_id` | `str` | yes | Id of the credentials, as returned when they are created or listed. |
| `bq_project_id` | `str` | no | BigQuery project the connection reads from. Only for a BigQuery connection. Between 1 and 200 characters. |
| `sql_warehouse_id` | `str` | no | Databricks SQL warehouse the connection runs queries on. Required for a `databricks-sql-warehouse` or `databricks-metastore-sql-warehouse` connection. Between 1 and 200 characters. |
| `env_var_name` | `str` | no | Name of the environment variable on the deployment that holds the connection's credentials. Must start with `MCD_`. Between 1 and 200 characters. |
| `kms_key_id` | `str` | no | AWS KMS key the variable's value is encrypted with. Omit it for a value stored in the clear. Between 1 and 200 characters. |

### Response

Returns the credentials after the change. Response fields: id, connection_type, storage_type, created_time, bq_project_id, sql_warehouse_id, env_var_name, kms_key_id.

| Field | Description |
|---|---|
| `id` | Unique identifier of the credentials. |
| `connection_type` | The connection type the credentials are for, such as `snowflake`. Fixed once created. |
| `storage_type` | Where the secret lives. Fixed once created. |
| `created_time` | When the credentials were created. |
| `bq_project_id` | BigQuery project the connection reads from. Null unless set. |
| `sql_warehouse_id` | Databricks SQL warehouse the connection runs queries on. Null unless set. |
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
| `credentials_id` | `str` | yes | Id of the credentials, as returned when they are created or listed. |

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
| `sql_warehouse_id` | `str` | no | Databricks SQL warehouse the connection runs queries on. Required for a `databricks-sql-warehouse` or `databricks-metastore-sql-warehouse` connection. Between 1 and 200 characters. |

### Response

Returns the new credentials. Response fields: id, connection_type, storage_type, created_time, bq_project_id, sql_warehouse_id, file_path.

| Field | Description |
|---|---|
| `id` | Unique identifier of the credentials. |
| `connection_type` | The connection type the credentials are for, such as `snowflake`. Fixed once created. |
| `storage_type` | Where the secret lives. Fixed once created. |
| `created_time` | When the credentials were created. |
| `bq_project_id` | BigQuery project the connection reads from. Null unless set. |
| `sql_warehouse_id` | Databricks SQL warehouse the connection runs queries on. Null unless set. |
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
| `sql_warehouse_id` | `str` | no | Databricks SQL warehouse the connection runs queries on. Required for a `databricks-sql-warehouse` or `databricks-metastore-sql-warehouse` connection. Between 1 and 200 characters. |

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
| `validations` | The run's validations, in the order they are declared. A validation stays `pending` until it starts. It can wait on a prerequisite, or for earlier validations to finish. A read with `since` lists only the validations that changed after that revision, and may list none. |

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
| `credentials_id` | `str` | yes | Id of the credentials, as returned when they are created or listed. |

### Response

Response fields: id, connection_type, storage_type, created_time, bq_project_id, sql_warehouse_id, file_path.

| Field | Description |
|---|---|
| `id` | Unique identifier of the credentials. |
| `connection_type` | The connection type the credentials are for, such as `snowflake`. Fixed once created. |
| `storage_type` | Where the secret lives. Fixed once created. |
| `created_time` | When the credentials were created. |
| `bq_project_id` | BigQuery project the connection reads from. Null unless set. |
| `sql_warehouse_id` | Databricks SQL warehouse the connection runs queries on. Null unless set. |
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
| `credentials_id` | `str` | yes | Id of the credentials, as returned when they are created or listed. |
| `bq_project_id` | `str` | no | BigQuery project the connection reads from. Only for a BigQuery connection. Between 1 and 200 characters. |
| `sql_warehouse_id` | `str` | no | Databricks SQL warehouse the connection runs queries on. Required for a `databricks-sql-warehouse` or `databricks-metastore-sql-warehouse` connection. Between 1 and 200 characters. |
| `file_path` | `str` | no | Path of the file on the deployment that holds the connection's credentials. Between 1 and 1024 characters. |

### Response

Returns the credentials after the change. Response fields: id, connection_type, storage_type, created_time, bq_project_id, sql_warehouse_id, file_path.

| Field | Description |
|---|---|
| `id` | Unique identifier of the credentials. |
| `connection_type` | The connection type the credentials are for, such as `snowflake`. Fixed once created. |
| `storage_type` | Where the secret lives. Fixed once created. |
| `created_time` | When the credentials were created. |
| `bq_project_id` | BigQuery project the connection reads from. Null unless set. |
| `sql_warehouse_id` | Databricks SQL warehouse the connection runs queries on. Null unless set. |
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
| `credentials_id` | `str` | yes | Id of the credentials, as returned when they are created or listed. |

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
| `sql_warehouse_id` | `str` | no | Databricks SQL warehouse the connection runs queries on. Required for a `databricks-sql-warehouse` or `databricks-metastore-sql-warehouse` connection. Between 1 and 200 characters. |

### Response

Returns the new credentials. Response fields: id, connection_type, storage_type, created_time, bq_project_id, sql_warehouse_id, gcp_secret.

| Field | Description |
|---|---|
| `id` | Unique identifier of the credentials. |
| `connection_type` | The connection type the credentials are for, such as `snowflake`. Fixed once created. |
| `storage_type` | Where the secret lives. Fixed once created. |
| `created_time` | When the credentials were created. |
| `bq_project_id` | BigQuery project the connection reads from. Null unless set. |
| `sql_warehouse_id` | Databricks SQL warehouse the connection runs queries on. Null unless set. |
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
| `sql_warehouse_id` | `str` | no | Databricks SQL warehouse the connection runs queries on. Required for a `databricks-sql-warehouse` or `databricks-metastore-sql-warehouse` connection. Between 1 and 200 characters. |

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
| `validations` | The run's validations, in the order they are declared. A validation stays `pending` until it starts. It can wait on a prerequisite, or for earlier validations to finish. A read with `since` lists only the validations that changed after that revision, and may list none. |

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
| `credentials_id` | `str` | yes | Id of the credentials, as returned when they are created or listed. |

### Response

Response fields: id, connection_type, storage_type, created_time, bq_project_id, sql_warehouse_id, gcp_secret.

| Field | Description |
|---|---|
| `id` | Unique identifier of the credentials. |
| `connection_type` | The connection type the credentials are for, such as `snowflake`. Fixed once created. |
| `storage_type` | Where the secret lives. Fixed once created. |
| `created_time` | When the credentials were created. |
| `bq_project_id` | BigQuery project the connection reads from. Null unless set. |
| `sql_warehouse_id` | Databricks SQL warehouse the connection runs queries on. Null unless set. |
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
| `credentials_id` | `str` | yes | Id of the credentials, as returned when they are created or listed. |
| `bq_project_id` | `str` | no | BigQuery project the connection reads from. Only for a BigQuery connection. Between 1 and 200 characters. |
| `sql_warehouse_id` | `str` | no | Databricks SQL warehouse the connection runs queries on. Required for a `databricks-sql-warehouse` or `databricks-metastore-sql-warehouse` connection. Between 1 and 200 characters. |
| `gcp_secret` | `str` | no | Name of the GCP Secret Manager secret holding the connection's credentials. Between 1 and 200 characters. |

### Response

Returns the credentials after the change. Response fields: id, connection_type, storage_type, created_time, bq_project_id, sql_warehouse_id, gcp_secret.

| Field | Description |
|---|---|
| `id` | Unique identifier of the credentials. |
| `connection_type` | The connection type the credentials are for, such as `snowflake`. Fixed once created. |
| `storage_type` | Where the secret lives. Fixed once created. |
| `created_time` | When the credentials were created. |
| `bq_project_id` | BigQuery project the connection reads from. Null unless set. |
| `sql_warehouse_id` | Databricks SQL warehouse the connection runs queries on. Null unless set. |
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
| `credentials_id` | `str` | yes | Id of the credentials, as returned when they are created or listed. |

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
| `credentials_id` | `str` | yes | Id of the credentials, as returned when they are created or listed. |

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
| `credentials_id` | `str` | yes | Id of the credentials, as returned when they are created or listed. |

### Response

Returns `credentials_id` and `deleted: true` once the credentials is gone.

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The credentials does not exist, or is not visible to the caller.
- The change conflicts with the current state of the credentials.
- Monte Carlo is busy or temporarily unavailable; try again after a moment.
- An unexpected error prevented the request from being processed.

## `get_starburst_enterprise_credentials`: Get Starburst Enterprise credentials

Get one set of Starburst Enterprise credentials, without the password.

An id that does not exist, belongs to another account, or names credentials of another
kind returns 404.

- **Effect:** read-only.
- **Pairs with:** `delete_starburst_enterprise_credentials`, `list_credentials`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned when they are created or listed. |

### Response

Response fields: id, connection_type, storage_type, created_time, host, port, db_name, user, ssl_ca_data, ssl_disabled.

| Field | Description |
|---|---|
| `id` | Unique identifier of the credentials. |
| `connection_type` | The connection type the credentials are for, such as `snowflake`. Fixed once created. |
| `storage_type` | Where the secret lives. Fixed once created. |
| `created_time` | When the credentials were created. |
| `host` | Hostname of the database endpoint. |
| `port` | Port the database listens on. |
| `db_name` | Database to connect to. Null when none is set. |
| `user` | Database user Monte Carlo logs in as. |
| `ssl_ca_data` | PEM text of the CA certificate the server's certificate is checked against. Null when none is set. |
| `ssl_disabled` | Skip the check of the server's certificate. The connection always uses TLS. Null when unset. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The credentials does not exist, or is not visible to the caller.
- An unexpected error prevented the request from being processed.
- Monte Carlo is busy or temporarily unavailable; try again after a moment.

## `delete_starburst_enterprise_credentials`: Delete Starburst Enterprise credentials

Delete Starburst Enterprise credentials no connection uses. Monte Carlo stops using the stored password. Change the password in Starburst Enterprise if the password itself must be retired.

- **Effect:** deletes; destructive and idempotent.
- **Pairs with:** `get_starburst_enterprise_credentials`, `list_credentials`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned when they are created or listed. |

### Response

Returns `credentials_id` and `deleted: true` once the credentials is gone.

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The credentials does not exist, or is not visible to the caller.
- The change conflicts with the current state of the credentials.
- Monte Carlo is busy or temporarily unavailable; try again after a moment.
- An unexpected error prevented the request from being processed.

## `get_starburst_galaxy_credentials`: Get Starburst Galaxy credentials

Get one set of Starburst Galaxy credentials, without the password.

An id that does not exist, belongs to another account, or names credentials of another
kind returns 404.

- **Effect:** read-only.
- **Pairs with:** `delete_starburst_galaxy_credentials`, `list_credentials`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned when they are created or listed. |

### Response

Response fields: id, connection_type, storage_type, created_time, host, port, db_name, user.

| Field | Description |
|---|---|
| `id` | Unique identifier of the credentials. |
| `connection_type` | The connection type the credentials are for, such as `snowflake`. Fixed once created. |
| `storage_type` | Where the secret lives. Fixed once created. |
| `created_time` | When the credentials were created. |
| `host` | Hostname of the database endpoint. |
| `port` | Port the database listens on. |
| `db_name` | Database to connect to. Null when none is set. |
| `user` | Database user Monte Carlo logs in as. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The credentials does not exist, or is not visible to the caller.
- An unexpected error prevented the request from being processed.
- Monte Carlo is busy or temporarily unavailable; try again after a moment.

## `delete_starburst_galaxy_credentials`: Delete Starburst Galaxy credentials

Delete Starburst Galaxy credentials no connection uses. Monte Carlo stops using the stored password. Change the password in Starburst Galaxy if the password itself must be retired.

- **Effect:** deletes; destructive and idempotent.
- **Pairs with:** `get_starburst_galaxy_credentials`, `list_credentials`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned when they are created or listed. |

### Response

Returns `credentials_id` and `deleted: true` once the credentials is gone.

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The credentials does not exist, or is not visible to the caller.
- The change conflicts with the current state of the credentials.
- Monte Carlo is busy or temporarily unavailable; try again after a moment.
- An unexpected error prevented the request from being processed.

## `get_tableau_credentials`: Get Tableau credentials

Get one set of Tableau credentials, without the password or the secrets.

An id that does not exist, belongs to another account, or names credentials of another
kind returns 404.

- **Effect:** read-only.
- **Pairs with:** `delete_tableau_credentials`, `list_credentials`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned by list_credentials. |

### Response

Response fields: id, connection_type, storage_type, created_time, server_name, site_name, verify_ssl, username, token_name, connected_app_client_id, connected_app_secret_id.

| Field | Description |
|---|---|
| `id` | Unique identifier of the credentials. |
| `connection_type` | The connection type the credentials are for, such as `snowflake`. Fixed once created. |
| `storage_type` | Where the secret lives. Fixed once created. |
| `created_time` | When the credentials were created. |
| `server_name` | URL of the Tableau server, starting with https:// or http://. |
| `site_name` | Tableau site. Null for the default site. |
| `verify_ssl` | Whether to verify the server's TLS certificate. Verified when left out. Null unless set. |
| `username` | Tableau user. Null for a personal access token. |
| `token_name` | Name of the personal access token. Null unless the credentials use one. |
| `connected_app_client_id` | Client ID of the connected app. Null unless the credentials use one. |
| `connected_app_secret_id` | ID of the connected app's secret. Null unless the credentials use one. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The credentials does not exist, or is not visible to the caller.
- An unexpected error prevented the request from being processed.
- Monte Carlo is busy or temporarily unavailable; try again after a moment.

## `delete_tableau_credentials`: Delete Tableau credentials

Delete Tableau credentials no connection uses. Monte Carlo stops using the stored password or secret. Revoke it in Tableau if the secret itself must be retired.

- **Effect:** deletes; destructive and idempotent.
- **Pairs with:** `get_tableau_credentials`, `list_credentials`.

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

## `get_teradata_credentials`: Get Teradata credentials

Get one set of Teradata credentials, without the password.

An id that does not exist, belongs to another account, or names credentials of another
kind returns 404.

- **Effect:** read-only.
- **Pairs with:** `delete_teradata_credentials`, `list_credentials`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned when they are created or listed. |

### Response

Response fields: id, connection_type, storage_type, created_time, host, port, db_name, user, ssl_ca_data, ssl_disabled, td_sslmode, td_logmech.

| Field | Description |
|---|---|
| `id` | Unique identifier of the credentials. |
| `connection_type` | The connection type the credentials are for, such as `snowflake`. Fixed once created. |
| `storage_type` | Where the secret lives. Fixed once created. |
| `created_time` | When the credentials were created. |
| `host` | Hostname of the database endpoint. |
| `port` | Port the database listens on. |
| `db_name` | Database to connect to. Null when none is set. |
| `user` | Database user Monte Carlo logs in as. |
| `ssl_ca_data` | PEM text of the CA certificate the server's certificate is checked against. Null when none is set. |
| `ssl_disabled` | Do not check the server against `ssl_ca_data`. `td_sslmode` decides whether the connection uses TLS. Null when unset. |
| `td_sslmode` | How the connection to Teradata uses TLS. Null when unset. |
| `td_logmech` | How Teradata authenticates the user. Null when unset. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The credentials does not exist, or is not visible to the caller.
- An unexpected error prevented the request from being processed.
- Monte Carlo is busy or temporarily unavailable; try again after a moment.

## `delete_teradata_credentials`: Delete Teradata credentials

Delete Teradata credentials no connection uses. Monte Carlo stops using the stored password. Change the password where Teradata checks it if the password itself must be retired.

- **Effect:** deletes; destructive and idempotent.
- **Pairs with:** `get_teradata_credentials`, `list_credentials`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned when they are created or listed. |

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
| `credentials_id` | `str` | yes | Id of the credentials, as returned when they are created or listed. |

### Response

Returns `credentials_id` and `deleted: true` once the credentials is gone.

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The credentials does not exist, or is not visible to the caller.
- The change conflicts with the current state of the credentials.
- Monte Carlo is busy or temporarily unavailable; try again after a moment.
- An unexpected error prevented the request from being processed.
