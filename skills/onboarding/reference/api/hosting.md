# `hosting` tools

<!-- Rendered from the REST API v2 OpenAPI document by api-codegen; do not edit. -->

Monte Carlo REST API v2 tools of the `hosting` tag, as the Monte Carlo MCP server exposes
them. Each section is one tool; its name is the tool to call.

## `get_hosting_domains`: Get the hosting domains

Get the URLs your Monte Carlo instance serves.

Some integrations need one of these URLs before they can be set up. dbt Cloud, for
example, issues a webhook secret only after you give it `dbt_cloud_webhook_url`.

Every caller in an instance gets the same values.

- **Effect:** read-only.

### Arguments

None.

### Response

Response fields: ui_url, integrations_url, graphql_api_url, graphql_oauth_api_url, m2m_token_url, m2m_instance_scope, dbt_cloud_webhook_url.

| Field | Description |
|---|---|
| `ui_url` | URL of the Monte Carlo web app. |
| `integrations_url` | Base URL of the integrations gateway, which receives webhooks and other inbound requests from the tools you connect. |
| `graphql_api_url` | URL of the GraphQL API, for API keys. |
| `graphql_oauth_api_url` | URL of the GraphQL API, for OAuth clients. |
| `m2m_token_url` | URL an OAuth client requests an access token from, with the client-credentials grant. Null when the instance does not support OAuth clients. |
| `m2m_instance_scope` | Scope an OAuth client requests for its token to reach this instance. Null when the instance does not support OAuth clients. |
| `dbt_cloud_webhook_url` | URL to give dbt Cloud when you create the webhook that reports job runs to Monte Carlo. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- An unexpected error prevented the request from being processed.

## `get_hosting_network`: Get the hosting network

Get the public IP addresses one region of your Monte Carlo instance connects from.

Allowlist them where Monte Carlo reaches your resources over the internet. Asking for the
secondary region of an instance without disaster recovery returns 404.

- **Effect:** read-only.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `instance_region` | one of `primary`, `secondary` | no | The region of your Monte Carlo instance to read. `primary`, the default, is the region serving your instance, which is the recovery region during a failover. `secondary` is the disaster recovery region, and only an instance with disaster recovery has one. With disaster recovery, read both and allow both, so access keeps working after a failover. During a failover both read the recovery region, so applying your policies then drops the original primary region until you apply them again after failing back. |

### Response

Response fields: collection_ip_addresses, saas_ip_addresses, webhook_ip_addresses, data_platform_ip_addresses.

| Field | Description |
|---|---|
| `collection_ip_addresses` | Addresses Monte Carlo collects from, such as when it reaches your warehouse, collection agent or data store over the internet. |
| `saas_ip_addresses` | Addresses the rest of the Monte Carlo platform connects from. |
| `webhook_ip_addresses` | Addresses Monte Carlo sends webhook notifications from. |
| `data_platform_ip_addresses` | Addresses Monte Carlo's data processing services connect from. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The hosting does not exist, or is not visible to the caller.
- An unexpected error prevented the request from being processed.

## `get_hosting_private_link`: Get the hosting private link details

Get how one region of your Monte Carlo instance reaches your AWS resources privately.

Use the VPC endpoint of the region you deploy to in an `aws:SourceVpce` condition, and the
private subnet CIDRs in an allowlist. Asking for the secondary region of an instance
without disaster recovery returns 404.

- **Effect:** read-only.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `instance_region` | one of `primary`, `secondary` | no | The region of your Monte Carlo instance to read. `primary`, the default, is the region serving your instance, which is the recovery region during a failover. `secondary` is the disaster recovery region, and only an instance with disaster recovery has one. With disaster recovery, read both and allow both, so access keeps working after a failover. During a failover both read the recovery region, so applying your policies then drops the original primary region until you apply them again after failing back. |

### Response

Response fields: aws.

| Field | Description |
|---|---|
| `aws` | AWS private connectivity. Null when the region has none. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- The hosting does not exist, or is not visible to the caller.
- An unexpected error prevented the request from being processed.
