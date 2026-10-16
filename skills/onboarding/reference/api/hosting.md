# `hosting` tools

<!-- Rendered from the REST API v2 OpenAPI document by api-codegen; do not edit. -->

Monte Carlo REST API v2 tools of the `hosting` tag, as the Monte Carlo MCP server exposes
them. Each section is one tool; its name is the tool to call.

## `get_hosting_domains`: Get the hosting domains

Get the URLs your Monte Carlo deployment serves.

Some integrations need one of these URLs before they can be set up. dbt Cloud, for
example, issues a webhook secret only after you give it `dbt_cloud_webhook_url`.

Every caller in a deployment gets the same values.

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
| `m2m_token_url` | URL an OAuth client requests an access token from, with the client-credentials grant. Null when the deployment does not support OAuth clients. |
| `m2m_instance_scope` | Scope an OAuth client requests for its token to reach this deployment. Null when the deployment does not support OAuth clients. |
| `dbt_cloud_webhook_url` | URL to give dbt Cloud when you create the webhook that reports job runs to Monte Carlo. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- An unexpected error prevented the request from being processed.
