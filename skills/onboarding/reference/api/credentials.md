# `credentials` tools

<!-- Rendered from the REST API v2 OpenAPI document by api-codegen; do not edit. -->

Monte Carlo REST API v2 tools of the `credentials` tag, as the Monte Carlo MCP server exposes
them. Each section is one tool; its name is the tool to call.

## `list_credentials`: List credentials

List the credentials in your account, of every kind, a page at a time.

Credentials are returned oldest first. Each entry says what connection type it is for and
where its secret lives. Get one by id to see the other fields of its kind.

- **Effect:** read-only.
- **Pairs with:** `create_airflow_credentials`, `create_athena_credentials`, `validate_athena_credentials`, `validate_athena_credentials_change`, `create_glue_credentials`, `validate_glue_credentials`, `validate_glue_credentials_change`, `create_hive_credentials`, `create_hive_s3_credentials`, `create_s3_credentials`, `create_aws_secrets_manager_credentials`, `validate_aws_secrets_manager_credentials`, `validate_aws_secrets_manager_credentials_change`, `create_azure_key_vault_credentials`, `validate_azure_key_vault_credentials`, `validate_azure_key_vault_credentials_change`, `create_env_var_credentials`, `validate_env_var_credentials`, `validate_env_var_credentials_change`, `create_file_credentials`, `validate_file_credentials`, `validate_file_credentials_change`, `create_gcp_secret_manager_credentials`, `validate_gcp_secret_manager_credentials`, `validate_gcp_secret_manager_credentials_change`, `get_credentials`.
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

## `create_airflow_credentials`: Create Airflow credentials

Store the host name of an Airflow environment as credentials. Takes `host_name` only: Airflow needs no secret. Refused once the account holds its limit of credentials.

- **Effect:** creates; repeating it creates again.
- **Pairs with:** `update_airflow_credentials`, `list_credentials`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `host_name` | `str` | yes | Host name of the Airflow web server, as Airflow reports it to Monte Carlo. Between 1 and 2048 characters. |

### Response

Returns the new credentials. Response fields: id, connection_type, storage_type, created_time, host_name.

| Field | Description |
|---|---|
| `id` | Unique identifier of the credentials. |
| `connection_type` | The connection type the credentials are for, such as `snowflake`. Fixed once created. |
| `storage_type` | Where the secret lives. Fixed once created. |
| `created_time` | When the credentials were created. |
| `host_name` | Host name of the Airflow web server, as Airflow reports it to Monte Carlo. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The change conflicts with the current state of the credentials.
- An argument is invalid; the error names the field.
- Monte Carlo is busy or temporarily unavailable; the tool retries once after the wait Monte Carlo asks for.
- An unexpected error prevented the request from being processed.

## `update_airflow_credentials`: Update Airflow credentials

Change the `host_name` of Airflow credentials. Every connection using them picks up the change. An empty body returns them unchanged.

- **Effect:** updates in place; idempotent.
- **Pairs with:** `create_airflow_credentials`, `list_credentials`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned by list_credentials. |
| `host_name` | `str` | no | Host name of the Airflow web server, as Airflow reports it to Monte Carlo. Between 1 and 2048 characters. |

### Response

Returns the credentials after the change. Response fields: id, connection_type, storage_type, created_time, host_name.

| Field | Description |
|---|---|
| `id` | Unique identifier of the credentials. |
| `connection_type` | The connection type the credentials are for, such as `snowflake`. Fixed once created. |
| `storage_type` | Where the secret lives. Fixed once created. |
| `created_time` | When the credentials were created. |
| `host_name` | Host name of the Airflow web server, as Airflow reports it to Monte Carlo. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The credentials does not exist, or is not visible to the caller.
- An argument is invalid; the error names the field.
- Monte Carlo is busy or temporarily unavailable; the tool retries once after the wait Monte Carlo asks for.
- An unexpected error prevented the request from being processed.

## `create_athena_credentials`: Create Athena credentials

Store the IAM role Monte Carlo assumes to run Athena queries, as credentials for an athena connection. Takes `assumable_role`, the ARN of a role in the customer's AWS account that the deployment assumes, plus `external_id` when the role's trust policy requires one and `aws_region`. `catalog` and `workgroup` are optional and default to AwsDataCatalog and primary. Athena needs no secret. Then call create_connection on a data-lake warehouse, usually the one with the glue connection. Refused once the account holds its limit of credentials.

- **Effect:** creates; repeating it creates again.
- **Pairs with:** `update_athena_credentials`, `list_credentials`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `assumable_role` | `str` | yes | ARN of the IAM role in your AWS account that the deployment assumes. Between 1 and 2048 characters. |
| `external_id` | `str` | no | External id your role's trust policy requires, if it requires one. It is not the deployment's `aws_external_id`. Between 1 and 1224 characters. |
| `aws_region` | `str` | no | AWS region to call. Omit it to use the deployment's own region. Between 1 and 200 characters. |
| `catalog` | `str` | no | Athena data catalog to query. Omit it to use `AwsDataCatalog`. Between 1 and 256 characters. |
| `workgroup` | `str` | no | Athena workgroup to run queries in. Omit it to use the `primary` workgroup. The role needs permission to start queries in it. Between 1 and 256 characters. |

### Response

Returns the new credentials. Response fields: id, connection_type, storage_type, created_time, assumable_role, external_id, aws_region, catalog, workgroup.

| Field | Description |
|---|---|
| `id` | Unique identifier of the credentials. |
| `connection_type` | The connection type the credentials are for, such as `snowflake`. Fixed once created. |
| `storage_type` | Where the secret lives. Fixed once created. |
| `created_time` | When the credentials were created. |
| `assumable_role` | ARN of the IAM role in your AWS account that the deployment assumes. Null unless set. |
| `external_id` | External id your role's trust policy requires, if it requires one. It is not the deployment's `aws_external_id`. Null unless set. |
| `aws_region` | AWS region to call. Null means the deployment's own region. |
| `catalog` | Athena data catalog to query. Null means `AwsDataCatalog`. |
| `workgroup` | Athena workgroup to run queries in. Null means the `primary` workgroup. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The change conflicts with the current state of the credentials.
- An argument is invalid; the error names the field.
- Monte Carlo is busy or temporarily unavailable; the tool retries once after the wait Monte Carlo asks for.
- An unexpected error prevented the request from being processed.

## `validate_athena_credentials`: Validate Athena credentials

Check candidate Athena credentials from a deployment before creating them. Takes the create_athena_credentials fields and a `deployment_id` from list_deployments. Creates nothing. Returns a run that is still going: poll `get_validation_run` with its id until the status is `completed`, then read each validation's own verdict.

- **Effect:** creates; repeating it creates again.
- **Pairs with:** `list_credentials`, `list_deployments`.
- **Runs in the background:** the response is the accepted request; poll it to completion.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `deployment_id` | `str` | yes | Deployment that runs the validations. It has to be one `GET /deployments` lists, and it has to be able to reach the system the credentials are for. |
| `assumable_role` | `str` | yes | ARN of the IAM role in your AWS account that the deployment assumes. Between 1 and 2048 characters. |
| `external_id` | `str` | no | External id your role's trust policy requires, if it requires one. It is not the deployment's `aws_external_id`. Between 1 and 1224 characters. |
| `aws_region` | `str` | no | AWS region to call. Omit it to use the deployment's own region. Between 1 and 200 characters. |
| `catalog` | `str` | no | Athena data catalog to query. Omit it to use `AwsDataCatalog`. Between 1 and 256 characters. |
| `workgroup` | `str` | no | Athena workgroup to run queries in. Omit it to use the `primary` workgroup. The role needs permission to start queries in it. Between 1 and 256 characters. |

### Response

Returns the accepted request as-is. Response fields: id, status, revision, target_type, target_id, validations_passed, validations_total, started_at, finished_at, expires_at, validations.

| Field | Description |
|---|---|
| `id` | Identifier of the run. Poll `GET /validations/{run_id}` with it. |
| `status` | Whether the run is still going. Every validation is final once it is not. |
| `revision` | Moves forward every time a validation changes. Pass it as `since` on the next poll to get only the validations that changed after this response. |
| `target_type` | What the run validates. |
| `target_id` | Identifier of what is being validated: the connection, or the credentials a change applies to. Null for candidate values, which are not stored anywhere. |
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

## `update_athena_credentials`: Update Athena credentials

Change Athena credentials. Every connection using them picks up the change. A field set to null is cleared, except `assumable_role`, which cannot be. An empty body returns them unchanged.

- **Effect:** updates in place; idempotent.
- **Pairs with:** `create_athena_credentials`, `list_credentials`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned when they are created or listed. |
| `assumable_role` | `str` | no | ARN of the IAM role in your AWS account that the deployment assumes. Between 1 and 2048 characters. |
| `external_id` | `str` | no | External id your role's trust policy requires, if it requires one. It is not the deployment's `aws_external_id`. Between 1 and 1224 characters. |
| `aws_region` | `str` | no | AWS region to call. Omit it to use the deployment's own region. Between 1 and 200 characters. |
| `catalog` | `str` | no | Athena data catalog to query. Omit it to use `AwsDataCatalog`. Between 1 and 256 characters. |
| `workgroup` | `str` | no | Athena workgroup to run queries in. Omit it to use the `primary` workgroup. The role needs permission to start queries in it. Between 1 and 256 characters. |

### Response

Returns the credentials after the change. Response fields: id, connection_type, storage_type, created_time, assumable_role, external_id, aws_region, catalog, workgroup.

| Field | Description |
|---|---|
| `id` | Unique identifier of the credentials. |
| `connection_type` | The connection type the credentials are for, such as `snowflake`. Fixed once created. |
| `storage_type` | Where the secret lives. Fixed once created. |
| `created_time` | When the credentials were created. |
| `assumable_role` | ARN of the IAM role in your AWS account that the deployment assumes. Null unless set. |
| `external_id` | External id your role's trust policy requires, if it requires one. It is not the deployment's `aws_external_id`. Null unless set. |
| `aws_region` | AWS region to call. Null means the deployment's own region. |
| `catalog` | Athena data catalog to query. Null means `AwsDataCatalog`. |
| `workgroup` | Athena workgroup to run queries in. Null means the `primary` workgroup. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The credentials does not exist, or is not visible to the caller.
- An argument is invalid; the error names the field.
- Monte Carlo is busy or temporarily unavailable; the tool retries once after the wait Monte Carlo asks for.
- An unexpected error prevented the request from being processed.

## `validate_athena_credentials_change`: Validate a change to Athena credentials

Check a change to Athena credentials from a deployment before making it. Takes the update_athena_credentials fields and a `deployment_id`. Changes nothing. Returns a run that is still going: poll `get_validation_run` with its id until the status is `completed`, then read each validation's own verdict.

- **Effect:** creates; repeating it creates again.
- **Pairs with:** `list_credentials`, `list_deployments`.
- **Runs in the background:** the response is the accepted request; poll it to completion.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned when they are created or listed. |
| `deployment_id` | `str` | yes | Deployment that runs the validations. It has to be one `GET /deployments` lists, and it has to be able to reach the system the credentials are for. |
| `assumable_role` | `str` | no | ARN of the IAM role in your AWS account that the deployment assumes. Between 1 and 2048 characters. |
| `external_id` | `str` | no | External id your role's trust policy requires, if it requires one. It is not the deployment's `aws_external_id`. Between 1 and 1224 characters. |
| `aws_region` | `str` | no | AWS region to call. Omit it to use the deployment's own region. Between 1 and 200 characters. |
| `catalog` | `str` | no | Athena data catalog to query. Omit it to use `AwsDataCatalog`. Between 1 and 256 characters. |
| `workgroup` | `str` | no | Athena workgroup to run queries in. Omit it to use the `primary` workgroup. The role needs permission to start queries in it. Between 1 and 256 characters. |

### Response

Returns the accepted request as-is. Response fields: id, status, revision, target_type, target_id, validations_passed, validations_total, started_at, finished_at, expires_at, validations.

| Field | Description |
|---|---|
| `id` | Identifier of the run. Poll `GET /validations/{run_id}` with it. |
| `status` | Whether the run is still going. Every validation is final once it is not. |
| `revision` | Moves forward every time a validation changes. Pass it as `since` on the next poll to get only the validations that changed after this response. |
| `target_type` | What the run validates. |
| `target_id` | Identifier of what is being validated: the connection, or the credentials a change applies to. Null for candidate values, which are not stored anywhere. |
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

## `create_glue_credentials`: Create Glue credentials

Store the IAM role Monte Carlo assumes to read a Glue catalog, as credentials for a glue connection. Takes `assumable_role`, the ARN of a role in the customer's AWS account that the deployment assumes, plus `external_id` when the role's trust policy requires one and `aws_region`. `ssl_ca_data` is optional. Glue needs no secret. Then call create_connection on a data-lake warehouse with no main connection yet. Refused once the account holds its limit of credentials.

- **Effect:** creates; repeating it creates again.
- **Pairs with:** `update_glue_credentials`, `list_credentials`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `assumable_role` | `str` | yes | ARN of the IAM role in your AWS account that the deployment assumes. Between 1 and 2048 characters. |
| `external_id` | `str` | no | External id your role's trust policy requires, if it requires one. It is not the deployment's `aws_external_id`. Between 1 and 1224 characters. |
| `aws_region` | `str` | no | AWS region to call. Omit it to use the deployment's own region. Between 1 and 200 characters. |
| `ssl_ca_data` | `str` | no | PEM text of a CA certificate to check the AWS endpoint's certificate against. Between 1 and 65536 characters. |

### Response

Returns the new credentials. Response fields: id, connection_type, storage_type, created_time, assumable_role, external_id, aws_region, ssl_ca_data.

| Field | Description |
|---|---|
| `id` | Unique identifier of the credentials. |
| `connection_type` | The connection type the credentials are for, such as `snowflake`. Fixed once created. |
| `storage_type` | Where the secret lives. Fixed once created. |
| `created_time` | When the credentials were created. |
| `assumable_role` | ARN of the IAM role in your AWS account that the deployment assumes. Null unless set. |
| `external_id` | External id your role's trust policy requires, if it requires one. It is not the deployment's `aws_external_id`. Null unless set. |
| `aws_region` | AWS region to call. Null means the deployment's own region. |
| `ssl_ca_data` | PEM text of a CA certificate to check the AWS endpoint's certificate against. Null unless set. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The change conflicts with the current state of the credentials.
- An argument is invalid; the error names the field.
- Monte Carlo is busy or temporarily unavailable; the tool retries once after the wait Monte Carlo asks for.
- An unexpected error prevented the request from being processed.

## `validate_glue_credentials`: Validate Glue credentials

Check candidate Glue credentials from a deployment before creating them. Takes the create_glue_credentials fields and a `deployment_id` from list_deployments. Creates nothing. Returns a run that is still going: poll `get_validation_run` with its id until the status is `completed`, then read each validation's own verdict.

- **Effect:** creates; repeating it creates again.
- **Pairs with:** `list_credentials`, `list_deployments`.
- **Runs in the background:** the response is the accepted request; poll it to completion.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `deployment_id` | `str` | yes | Deployment that runs the validations. It has to be one `GET /deployments` lists, and it has to be able to reach the system the credentials are for. |
| `assumable_role` | `str` | yes | ARN of the IAM role in your AWS account that the deployment assumes. Between 1 and 2048 characters. |
| `external_id` | `str` | no | External id your role's trust policy requires, if it requires one. It is not the deployment's `aws_external_id`. Between 1 and 1224 characters. |
| `aws_region` | `str` | no | AWS region to call. Omit it to use the deployment's own region. Between 1 and 200 characters. |
| `ssl_ca_data` | `str` | no | PEM text of a CA certificate to check the AWS endpoint's certificate against. Between 1 and 65536 characters. |

### Response

Returns the accepted request as-is. Response fields: id, status, revision, target_type, target_id, validations_passed, validations_total, started_at, finished_at, expires_at, validations.

| Field | Description |
|---|---|
| `id` | Identifier of the run. Poll `GET /validations/{run_id}` with it. |
| `status` | Whether the run is still going. Every validation is final once it is not. |
| `revision` | Moves forward every time a validation changes. Pass it as `since` on the next poll to get only the validations that changed after this response. |
| `target_type` | What the run validates. |
| `target_id` | Identifier of what is being validated: the connection, or the credentials a change applies to. Null for candidate values, which are not stored anywhere. |
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

## `update_glue_credentials`: Update Glue credentials

Change Glue credentials. Every connection using them picks up the change. A field set to null is cleared, except `assumable_role`, which cannot be. An empty body returns them unchanged.

- **Effect:** updates in place; idempotent.
- **Pairs with:** `create_glue_credentials`, `list_credentials`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned when they are created or listed. |
| `assumable_role` | `str` | no | ARN of the IAM role in your AWS account that the deployment assumes. Between 1 and 2048 characters. |
| `external_id` | `str` | no | External id your role's trust policy requires, if it requires one. It is not the deployment's `aws_external_id`. Between 1 and 1224 characters. |
| `aws_region` | `str` | no | AWS region to call. Omit it to use the deployment's own region. Between 1 and 200 characters. |
| `ssl_ca_data` | `str` | no | PEM text of a CA certificate to check the AWS endpoint's certificate against. Between 1 and 65536 characters. |

### Response

Returns the credentials after the change. Response fields: id, connection_type, storage_type, created_time, assumable_role, external_id, aws_region, ssl_ca_data.

| Field | Description |
|---|---|
| `id` | Unique identifier of the credentials. |
| `connection_type` | The connection type the credentials are for, such as `snowflake`. Fixed once created. |
| `storage_type` | Where the secret lives. Fixed once created. |
| `created_time` | When the credentials were created. |
| `assumable_role` | ARN of the IAM role in your AWS account that the deployment assumes. Null unless set. |
| `external_id` | External id your role's trust policy requires, if it requires one. It is not the deployment's `aws_external_id`. Null unless set. |
| `aws_region` | AWS region to call. Null means the deployment's own region. |
| `ssl_ca_data` | PEM text of a CA certificate to check the AWS endpoint's certificate against. Null unless set. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The credentials does not exist, or is not visible to the caller.
- An argument is invalid; the error names the field.
- Monte Carlo is busy or temporarily unavailable; the tool retries once after the wait Monte Carlo asks for.
- An unexpected error prevented the request from being processed.

## `validate_glue_credentials_change`: Validate a change to Glue credentials

Check a change to Glue credentials from a deployment before making it. Takes the update_glue_credentials fields and a `deployment_id`. Changes nothing. Returns a run that is still going: poll `get_validation_run` with its id until the status is `completed`, then read each validation's own verdict.

- **Effect:** creates; repeating it creates again.
- **Pairs with:** `list_credentials`, `list_deployments`.
- **Runs in the background:** the response is the accepted request; poll it to completion.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned when they are created or listed. |
| `deployment_id` | `str` | yes | Deployment that runs the validations. It has to be one `GET /deployments` lists, and it has to be able to reach the system the credentials are for. |
| `assumable_role` | `str` | no | ARN of the IAM role in your AWS account that the deployment assumes. Between 1 and 2048 characters. |
| `external_id` | `str` | no | External id your role's trust policy requires, if it requires one. It is not the deployment's `aws_external_id`. Between 1 and 1224 characters. |
| `aws_region` | `str` | no | AWS region to call. Omit it to use the deployment's own region. Between 1 and 200 characters. |
| `ssl_ca_data` | `str` | no | PEM text of a CA certificate to check the AWS endpoint's certificate against. Between 1 and 65536 characters. |

### Response

Returns the accepted request as-is. Response fields: id, status, revision, target_type, target_id, validations_passed, validations_total, started_at, finished_at, expires_at, validations.

| Field | Description |
|---|---|
| `id` | Identifier of the run. Poll `GET /validations/{run_id}` with it. |
| `status` | Whether the run is still going. Every validation is final once it is not. |
| `revision` | Moves forward every time a validation changes. Pass it as `since` on the next poll to get only the validations that changed after this response. |
| `target_type` | What the run validates. |
| `target_id` | Identifier of what is being validated: the connection, or the credentials a change applies to. Null for candidate values, which are not stored anywhere. |
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

## `create_hive_credentials`: Create Hive credentials

Store the address of a HiveServer2 and the user Monte Carlo signs in as, as credentials for a hive connection. Takes `host` and `user`, plus `port`, `db_name` and `auth_mode` (`SASL` when left out). Hive needs no secret. Then call create_connection with them on a data-lake warehouse. Refused once the account holds its limit of credentials.

- **Effect:** creates; repeating it creates again.
- **Pairs with:** `update_hive_credentials`, `list_credentials`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `host` | `str` | yes | Hostname of the HiveServer2. Between 1 and 255 characters. |
| `user` | `str` | yes | User Monte Carlo signs in as. Hive takes no password. Between 1 and 200 characters. |
| `port` | `int` | no | Port the HiveServer2 listens on in binary mode. Between 1 and 65535. |
| `db_name` | `str` | no | Database Monte Carlo connects to. Between 1 and 200 characters. |
| `auth_mode` | one of `SASL`, `NOSASL` | no | How Monte Carlo signs in. Omit it for `SASL`. |

### Response

Returns the new credentials. Response fields: id, connection_type, storage_type, created_time, host, port, user, db_name, auth_mode.

| Field | Description |
|---|---|
| `id` | Unique identifier of the credentials. |
| `connection_type` | The connection type the credentials are for, such as `snowflake`. Fixed once created. |
| `storage_type` | Where the secret lives. Fixed once created. |
| `created_time` | When the credentials were created. |
| `host` | Hostname of the HiveServer2. |
| `port` | Port the HiveServer2 listens on in binary mode. Null means the client's default. |
| `user` | User Monte Carlo signs in as. Hive takes no password. |
| `db_name` | Database Monte Carlo connects to. Null means the default database. |
| `auth_mode` | How Monte Carlo signs in. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The change conflicts with the current state of the credentials.
- An argument is invalid; the error names the field.
- Monte Carlo is busy or temporarily unavailable; the tool retries once after the wait Monte Carlo asks for.
- An unexpected error prevented the request from being processed.

## `create_hive_s3_credentials`: Create Hive (S3) credentials

Store the S3 location of Hive query logs from EMR and the IAM role Monte Carlo assumes to read them, as credentials for a hive-s3 connection. Takes `bucket`, `prefix` (the key prefix, not empty) and `assumable_role`, the ARN of a role in the customer's AWS account that the deployment assumes to read the bucket, plus `external_id` when the role's trust policy requires one. Hive (S3) needs no secret. Then call create_connection on a data-lake warehouse. Refused once the account holds its limit of credentials.

- **Effect:** creates; repeating it creates again.
- **Pairs with:** `update_hive_s3_credentials`, `list_credentials`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `assumable_role` | `str` | yes | ARN of the IAM role in your AWS account that the deployment assumes. Between 1 and 2048 characters. |
| `bucket` | `str` | yes | S3 bucket Monte Carlo reads from. Between 3 and 255 characters. |
| `prefix` | `str` | yes | Key prefix of the EMR log root, such as `emr/prod`. Leave out the bucket, a leading `/` and any `s3://` scheme. Send an empty string when the cluster's EMR log URI is the bucket root. Monte Carlo reads each cluster's Hive logs under `<prefix>/<cluster-id>/node/<instance-id>/applications/hive/`. Up to 1024 characters. |
| `external_id` | `str` | no | External id your role's trust policy requires, if it requires one. It is not the deployment's `aws_external_id`. Between 1 and 1224 characters. |

### Response

Returns the new credentials. Response fields: id, connection_type, storage_type, created_time, assumable_role, external_id, bucket, prefix.

| Field | Description |
|---|---|
| `id` | Unique identifier of the credentials. |
| `connection_type` | The connection type the credentials are for, such as `snowflake`. Fixed once created. |
| `storage_type` | Where the secret lives. Fixed once created. |
| `created_time` | When the credentials were created. |
| `assumable_role` | ARN of the IAM role in your AWS account that the deployment assumes. |
| `external_id` | External id your role's trust policy requires, if it requires one. It is not the deployment's `aws_external_id`. Null unless set. |
| `bucket` | S3 bucket Monte Carlo reads from. |
| `prefix` | Key prefix the objects sit under, such as `emr/prod`. Leave out the bucket, a leading `/` and any `s3://` scheme. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The change conflicts with the current state of the credentials.
- An argument is invalid; the error names the field.
- Monte Carlo is busy or temporarily unavailable; the tool retries once after the wait Monte Carlo asks for.
- An unexpected error prevented the request from being processed.

## `update_hive_s3_credentials`: Update Hive (S3) credentials

Change Hive (S3) credentials. Every connection using them picks up the change. `external_id` set to null is cleared. `bucket`, `prefix` and `assumable_role` cannot be cleared. An empty body returns them unchanged.

- **Effect:** updates in place; idempotent.
- **Pairs with:** `create_hive_s3_credentials`, `list_credentials`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned when they are created or listed. |
| `assumable_role` | `str` | no | ARN of the IAM role in your AWS account that the deployment assumes. Between 1 and 2048 characters. |
| `external_id` | `str` | no | External id your role's trust policy requires, if it requires one. It is not the deployment's `aws_external_id`. Between 1 and 1224 characters. |
| `bucket` | `str` | no | S3 bucket Monte Carlo reads from. Between 3 and 255 characters. |
| `prefix` | `str` | no | Key prefix of the EMR log root, such as `emr/prod`. Leave out the bucket, a leading `/` and any `s3://` scheme. Send an empty string when the cluster's EMR log URI is the bucket root. Monte Carlo reads each cluster's Hive logs under `<prefix>/<cluster-id>/node/<instance-id>/applications/hive/`. Up to 1024 characters. |

### Response

Returns the credentials after the change. Response fields: id, connection_type, storage_type, created_time, assumable_role, external_id, bucket, prefix.

| Field | Description |
|---|---|
| `id` | Unique identifier of the credentials. |
| `connection_type` | The connection type the credentials are for, such as `snowflake`. Fixed once created. |
| `storage_type` | Where the secret lives. Fixed once created. |
| `created_time` | When the credentials were created. |
| `assumable_role` | ARN of the IAM role in your AWS account that the deployment assumes. |
| `external_id` | External id your role's trust policy requires, if it requires one. It is not the deployment's `aws_external_id`. Null unless set. |
| `bucket` | S3 bucket Monte Carlo reads from. |
| `prefix` | Key prefix the objects sit under, such as `emr/prod`. Leave out the bucket, a leading `/` and any `s3://` scheme. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The credentials does not exist, or is not visible to the caller.
- An argument is invalid; the error names the field.
- Monte Carlo is busy or temporarily unavailable; the tool retries once after the wait Monte Carlo asks for.
- An unexpected error prevented the request from being processed.

## `update_hive_credentials`: Update Hive credentials

Change Hive credentials. Every connection using them picks up the change. `port` and `db_name` set to null are cleared, and `auth_mode` set to null goes back to `SASL`. `host` and `user` cannot be cleared. An empty body returns them unchanged.

- **Effect:** updates in place; idempotent.
- **Pairs with:** `create_hive_credentials`, `list_credentials`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned when they are created or listed. |
| `host` | `str` | no | Hostname of the HiveServer2. Between 1 and 255 characters. |
| `port` | `int` | no | Port the HiveServer2 listens on in binary mode. Between 1 and 65535. |
| `user` | `str` | no | User Monte Carlo signs in as. Hive takes no password. Between 1 and 200 characters. |
| `db_name` | `str` | no | Database Monte Carlo connects to. Between 1 and 200 characters. |
| `auth_mode` | one of `SASL`, `NOSASL` | no | How Monte Carlo signs in. Omit it for `SASL`. |

### Response

Returns the credentials after the change. Response fields: id, connection_type, storage_type, created_time, host, port, user, db_name, auth_mode.

| Field | Description |
|---|---|
| `id` | Unique identifier of the credentials. |
| `connection_type` | The connection type the credentials are for, such as `snowflake`. Fixed once created. |
| `storage_type` | Where the secret lives. Fixed once created. |
| `created_time` | When the credentials were created. |
| `host` | Hostname of the HiveServer2. |
| `port` | Port the HiveServer2 listens on in binary mode. Null means the client's default. |
| `user` | User Monte Carlo signs in as. Hive takes no password. |
| `db_name` | Database Monte Carlo connects to. Null means the default database. |
| `auth_mode` | How Monte Carlo signs in. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The credentials does not exist, or is not visible to the caller.
- An argument is invalid; the error names the field.
- Monte Carlo is busy or temporarily unavailable; the tool retries once after the wait Monte Carlo asks for.
- An unexpected error prevented the request from being processed.

## `create_s3_credentials`: Create S3 credentials

Store an S3 location and the IAM role Monte Carlo assumes to read it, as credentials for an s3 connection. Takes `bucket`, `prefix` (the key prefix, not empty) and `assumable_role`, the ARN of a role in the customer's AWS account that the deployment assumes to read the bucket, plus `external_id` when the role's trust policy requires one. S3 needs no secret. Then call create_connection on a data-lake warehouse. An s3 connection runs no jobs on its own. Refused once the account holds its limit of credentials.

- **Effect:** creates; repeating it creates again.
- **Pairs with:** `update_s3_credentials`, `list_credentials`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `assumable_role` | `str` | yes | ARN of the IAM role in your AWS account that the deployment assumes. Between 1 and 2048 characters. |
| `bucket` | `str` | yes | S3 bucket Monte Carlo reads from. Between 3 and 255 characters. |
| `prefix` | `str` | yes | Key prefix the objects sit under, such as `emr/prod`. Leave out the bucket, a leading `/` and any `s3://` scheme. Between 1 and 1024 characters. |
| `external_id` | `str` | no | External id your role's trust policy requires, if it requires one. It is not the deployment's `aws_external_id`. Between 1 and 1224 characters. |

### Response

Returns the new credentials. Response fields: id, connection_type, storage_type, created_time, assumable_role, external_id, bucket, prefix.

| Field | Description |
|---|---|
| `id` | Unique identifier of the credentials. |
| `connection_type` | The connection type the credentials are for, such as `snowflake`. Fixed once created. |
| `storage_type` | Where the secret lives. Fixed once created. |
| `created_time` | When the credentials were created. |
| `assumable_role` | ARN of the IAM role in your AWS account that the deployment assumes. |
| `external_id` | External id your role's trust policy requires, if it requires one. It is not the deployment's `aws_external_id`. Null unless set. |
| `bucket` | S3 bucket Monte Carlo reads from. |
| `prefix` | Key prefix the objects sit under, such as `emr/prod`. Leave out the bucket, a leading `/` and any `s3://` scheme. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The change conflicts with the current state of the credentials.
- An argument is invalid; the error names the field.
- Monte Carlo is busy or temporarily unavailable; the tool retries once after the wait Monte Carlo asks for.
- An unexpected error prevented the request from being processed.

## `update_s3_credentials`: Update S3 credentials

Change S3 credentials. Every connection using them picks up the change. `external_id` set to null is cleared. `bucket`, `prefix` and `assumable_role` cannot be cleared. An empty body returns them unchanged.

- **Effect:** updates in place; idempotent.
- **Pairs with:** `create_s3_credentials`, `list_credentials`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned when they are created or listed. |
| `assumable_role` | `str` | no | ARN of the IAM role in your AWS account that the deployment assumes. Between 1 and 2048 characters. |
| `external_id` | `str` | no | External id your role's trust policy requires, if it requires one. It is not the deployment's `aws_external_id`. Between 1 and 1224 characters. |
| `bucket` | `str` | no | S3 bucket Monte Carlo reads from. Between 3 and 255 characters. |
| `prefix` | `str` | no | Key prefix the objects sit under, such as `emr/prod`. Leave out the bucket, a leading `/` and any `s3://` scheme. Between 1 and 1024 characters. |

### Response

Returns the credentials after the change. Response fields: id, connection_type, storage_type, created_time, assumable_role, external_id, bucket, prefix.

| Field | Description |
|---|---|
| `id` | Unique identifier of the credentials. |
| `connection_type` | The connection type the credentials are for, such as `snowflake`. Fixed once created. |
| `storage_type` | Where the secret lives. Fixed once created. |
| `created_time` | When the credentials were created. |
| `assumable_role` | ARN of the IAM role in your AWS account that the deployment assumes. |
| `external_id` | External id your role's trust policy requires, if it requires one. It is not the deployment's `aws_external_id`. Null unless set. |
| `bucket` | S3 bucket Monte Carlo reads from. |
| `prefix` | Key prefix the objects sit under, such as `emr/prod`. Leave out the bucket, a leading `/` and any `s3://` scheme. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The credentials does not exist, or is not visible to the caller.
- An argument is invalid; the error names the field.
- Monte Carlo is busy or temporarily unavailable; the tool retries once after the wait Monte Carlo asks for.
- An unexpected error prevented the request from being processed.

## `create_aws_secrets_manager_credentials`: Create AWS Secrets Manager credentials

Store where a connection's credentials live in AWS Secrets Manager: the secret's name or ARN, its region and the role to assume, never the secret itself.

- **Effect:** creates; repeating it creates again.
- **Pairs with:** `update_aws_secrets_manager_credentials`, `list_credentials`.

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
| `target_id` | Identifier of what is being validated: the connection, or the credentials a change applies to. Null for candidate values, which are not stored anywhere. |
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

## `update_aws_secrets_manager_credentials`: Update AWS Secrets Manager credentials

Change where AWS Secrets Manager credentials point. Takes only the fields to change.

- **Effect:** updates in place; idempotent.
- **Pairs with:** `create_aws_secrets_manager_credentials`, `list_credentials`.

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

## `validate_aws_secrets_manager_credentials_change`: Validate a change to AWS Secrets Manager credentials

Check whether a change to existing AWS Secrets Manager credentials works before making it. Takes only the fields to change, as the update does, and a deployment to run from. The stored credentials are not changed. Returns a run that is still going: poll `get_validation_run` with its id until the status is `completed`, then read each validation's own verdict.

- **Effect:** creates; repeating it creates again.
- **Pairs with:** `list_credentials`, `list_deployments`.
- **Runs in the background:** the response is the accepted request; poll it to completion.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned when they are created or listed. |
| `deployment_id` | `str` | yes | Deployment that runs the validations. It has to be one `GET /deployments` lists, and it has to be able to reach the system the credentials are for. |
| `bq_project_id` | `str` | no | BigQuery project the connection reads from. Only for a BigQuery connection. Between 1 and 200 characters. |
| `sql_warehouse_id` | `str` | no | Databricks SQL warehouse the connection runs queries on. Required for a `databricks-sql-warehouse` or `databricks-metastore-sql-warehouse` connection. Between 1 and 200 characters. |
| `aws_secret` | `str` | no | Name or ARN of the AWS Secrets Manager secret holding the connection's credentials. Between 1 and 2048 characters. |
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
| `target_id` | Identifier of what is being validated: the connection, or the credentials a change applies to. Null for candidate values, which are not stored anywhere. |
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

## `create_azure_key_vault_credentials`: Create Azure Key Vault credentials

Store where a connection's credentials live in Azure Key Vault: the vault and the secret's name, never the secret itself.

- **Effect:** creates; repeating it creates again.
- **Pairs with:** `update_azure_key_vault_credentials`, `list_credentials`.

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
| `target_id` | Identifier of what is being validated: the connection, or the credentials a change applies to. Null for candidate values, which are not stored anywhere. |
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

## `update_azure_key_vault_credentials`: Update Azure Key Vault credentials

Change where Azure Key Vault credentials point. Takes only the fields to change.

- **Effect:** updates in place; idempotent.
- **Pairs with:** `create_azure_key_vault_credentials`, `list_credentials`.

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

## `validate_azure_key_vault_credentials_change`: Validate a change to Azure Key Vault credentials

Check whether a change to existing Azure Key Vault credentials works before making it. Takes only the fields to change, as the update does, and a deployment to run from. The stored credentials are not changed. Returns a run that is still going: poll `get_validation_run` with its id until the status is `completed`, then read each validation's own verdict.

- **Effect:** creates; repeating it creates again.
- **Pairs with:** `list_credentials`, `list_deployments`.
- **Runs in the background:** the response is the accepted request; poll it to completion.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned when they are created or listed. |
| `deployment_id` | `str` | yes | Deployment that runs the validations. It has to be one `GET /deployments` lists, and it has to be able to reach the system the credentials are for. |
| `bq_project_id` | `str` | no | BigQuery project the connection reads from. Only for a BigQuery connection. Between 1 and 200 characters. |
| `sql_warehouse_id` | `str` | no | Databricks SQL warehouse the connection runs queries on. Required for a `databricks-sql-warehouse` or `databricks-metastore-sql-warehouse` connection. Between 1 and 200 characters. |
| `akv_secret` | `str` | no | Name of the Azure Key Vault secret holding the connection's credentials. Between 1 and 200 characters. |
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
| `target_id` | Identifier of what is being validated: the connection, or the credentials a change applies to. Null for candidate values, which are not stored anywhere. |
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

## `create_env_var_credentials`: Create environment variable credentials

Store which environment variable of the deployment holds a connection's credentials, and the KMS key that encrypts it, never the value itself.

- **Effect:** creates; repeating it creates again.
- **Pairs with:** `update_env_var_credentials`, `list_credentials`.

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
| `target_id` | Identifier of what is being validated: the connection, or the credentials a change applies to. Null for candidate values, which are not stored anywhere. |
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

## `update_env_var_credentials`: Update environment variable credentials

Change which environment variable credentials point at. Takes only the fields to change.

- **Effect:** updates in place; idempotent.
- **Pairs with:** `create_env_var_credentials`, `list_credentials`.

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

## `validate_env_var_credentials_change`: Validate a change to environment variable credentials

Check whether a change to existing environment variable credentials works before making it. Takes only the fields to change, as the update does, and a deployment to run from. The stored credentials are not changed. Returns a run that is still going: poll `get_validation_run` with its id until the status is `completed`, then read each validation's own verdict.

- **Effect:** creates; repeating it creates again.
- **Pairs with:** `list_credentials`, `list_deployments`.
- **Runs in the background:** the response is the accepted request; poll it to completion.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned when they are created or listed. |
| `deployment_id` | `str` | yes | Deployment that runs the validations. It has to be one `GET /deployments` lists, and it has to be able to reach the system the credentials are for. |
| `bq_project_id` | `str` | no | BigQuery project the connection reads from. Only for a BigQuery connection. Between 1 and 200 characters. |
| `sql_warehouse_id` | `str` | no | Databricks SQL warehouse the connection runs queries on. Required for a `databricks-sql-warehouse` or `databricks-metastore-sql-warehouse` connection. Between 1 and 200 characters. |
| `env_var_name` | `str` | no | Name of the environment variable on the deployment that holds the connection's credentials. Must start with `MCD_`. Between 1 and 200 characters. |
| `kms_key_id` | `str` | no | AWS KMS key the variable's value is encrypted with. Omit it for a value stored in the clear. Between 1 and 200 characters. |

### Response

Returns the accepted request as-is. Response fields: id, status, revision, target_type, target_id, validations_passed, validations_total, started_at, finished_at, expires_at, validations.

| Field | Description |
|---|---|
| `id` | Identifier of the run. Poll `GET /validations/{run_id}` with it. |
| `status` | Whether the run is still going. Every validation is final once it is not. |
| `revision` | Moves forward every time a validation changes. Pass it as `since` on the next poll to get only the validations that changed after this response. |
| `target_type` | What the run validates. |
| `target_id` | Identifier of what is being validated: the connection, or the credentials a change applies to. Null for candidate values, which are not stored anywhere. |
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

## `create_file_credentials`: Create file credentials

Store which file on the deployment holds a connection's credentials, never the contents.

- **Effect:** creates; repeating it creates again.
- **Pairs with:** `update_file_credentials`, `list_credentials`.

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
| `target_id` | Identifier of what is being validated: the connection, or the credentials a change applies to. Null for candidate values, which are not stored anywhere. |
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

## `update_file_credentials`: Update file credentials

Change which file credentials point at. Takes only the fields to change.

- **Effect:** updates in place; idempotent.
- **Pairs with:** `create_file_credentials`, `list_credentials`.

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

## `validate_file_credentials_change`: Validate a change to file credentials

Check whether a change to existing file credentials works before making it. Takes only the fields to change, as the update does, and a deployment to run from. The stored credentials are not changed. Returns a run that is still going: poll `get_validation_run` with its id until the status is `completed`, then read each validation's own verdict.

- **Effect:** creates; repeating it creates again.
- **Pairs with:** `list_credentials`, `list_deployments`.
- **Runs in the background:** the response is the accepted request; poll it to completion.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned when they are created or listed. |
| `deployment_id` | `str` | yes | Deployment that runs the validations. It has to be one `GET /deployments` lists, and it has to be able to reach the system the credentials are for. |
| `bq_project_id` | `str` | no | BigQuery project the connection reads from. Only for a BigQuery connection. Between 1 and 200 characters. |
| `sql_warehouse_id` | `str` | no | Databricks SQL warehouse the connection runs queries on. Required for a `databricks-sql-warehouse` or `databricks-metastore-sql-warehouse` connection. Between 1 and 200 characters. |
| `file_path` | `str` | no | Path of the file on the deployment that holds the connection's credentials. Between 1 and 1024 characters. |

### Response

Returns the accepted request as-is. Response fields: id, status, revision, target_type, target_id, validations_passed, validations_total, started_at, finished_at, expires_at, validations.

| Field | Description |
|---|---|
| `id` | Identifier of the run. Poll `GET /validations/{run_id}` with it. |
| `status` | Whether the run is still going. Every validation is final once it is not. |
| `revision` | Moves forward every time a validation changes. Pass it as `since` on the next poll to get only the validations that changed after this response. |
| `target_type` | What the run validates. |
| `target_id` | Identifier of what is being validated: the connection, or the credentials a change applies to. Null for candidate values, which are not stored anywhere. |
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

## `create_gcp_secret_manager_credentials`: Create GCP Secret Manager credentials

Store where a connection's credentials live in GCP Secret Manager: the secret's name, never the secret itself.

- **Effect:** creates; repeating it creates again.
- **Pairs with:** `update_gcp_secret_manager_credentials`, `list_credentials`.

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
| `target_id` | Identifier of what is being validated: the connection, or the credentials a change applies to. Null for candidate values, which are not stored anywhere. |
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

## `update_gcp_secret_manager_credentials`: Update GCP Secret Manager credentials

Change where GCP Secret Manager credentials point. Takes only the fields to change.

- **Effect:** updates in place; idempotent.
- **Pairs with:** `create_gcp_secret_manager_credentials`, `list_credentials`.

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

## `validate_gcp_secret_manager_credentials_change`: Validate a change to GCP Secret Manager credentials

Check whether a change to existing GCP Secret Manager credentials works before making it. Takes only the fields to change, as the update does, and a deployment to run from. The stored credentials are not changed. Returns a run that is still going: poll `get_validation_run` with its id until the status is `completed`, then read each validation's own verdict.

- **Effect:** creates; repeating it creates again.
- **Pairs with:** `list_credentials`, `list_deployments`.
- **Runs in the background:** the response is the accepted request; poll it to completion.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned when they are created or listed. |
| `deployment_id` | `str` | yes | Deployment that runs the validations. It has to be one `GET /deployments` lists, and it has to be able to reach the system the credentials are for. |
| `bq_project_id` | `str` | no | BigQuery project the connection reads from. Only for a BigQuery connection. Between 1 and 200 characters. |
| `sql_warehouse_id` | `str` | no | Databricks SQL warehouse the connection runs queries on. Required for a `databricks-sql-warehouse` or `databricks-metastore-sql-warehouse` connection. Between 1 and 200 characters. |
| `gcp_secret` | `str` | no | Name of the GCP Secret Manager secret holding the connection's credentials. Between 1 and 200 characters. |

### Response

Returns the accepted request as-is. Response fields: id, status, revision, target_type, target_id, validations_passed, validations_total, started_at, finished_at, expires_at, validations.

| Field | Description |
|---|---|
| `id` | Identifier of the run. Poll `GET /validations/{run_id}` with it. |
| `status` | Whether the run is still going. Every validation is final once it is not. |
| `revision` | Moves forward every time a validation changes. Pass it as `since` on the next poll to get only the validations that changed after this response. |
| `target_type` | What the run validates. |
| `target_id` | Identifier of what is being validated: the connection, or the credentials a change applies to. Null for candidate values, which are not stored anywhere. |
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

## `get_credentials`: Get credentials

Get credentials of any kind by id.

Takes the id the list or a connection returns. `details` holds the other fields of that
kind. A secret is never returned.

- **Effect:** read-only.
- **Pairs with:** `list_credentials`, `delete_credentials`.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `credentials_id` | `str` | yes | Id of the credentials, as returned when they are created or listed. |

### Response

Response fields: id, connection_type, storage_type, created_time, details.

| Field | Description |
|---|---|
| `id` | Unique identifier of the credentials. |
| `connection_type` | The connection type the credentials are for, such as `snowflake`. Fixed once created. |
| `storage_type` | Where the secret lives. Fixed once created. |
| `created_time` | When the credentials were created. |
| `details` | The fields the typed read of this kind returns beyond the ones above, such as `account` and `user` for Snowflake. Never a secret. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The credentials does not exist, or is not visible to the caller.
- An unexpected error prevented the request from being processed.
- Monte Carlo is busy or temporarily unavailable; try again after a moment.

## `delete_credentials`: Delete credentials

Delete credentials of any kind, by the id list_credentials or a connection returns. Refused while a connection still uses them. Call delete_connection first. Monte Carlo stops using them. Whatever they point at is untouched. To retire a secret, rotate or revoke it where it lives.

- **Effect:** deletes; destructive and idempotent.
- **Pairs with:** `list_credentials`, `get_credentials`.

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
