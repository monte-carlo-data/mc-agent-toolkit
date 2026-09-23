# `users` tools

<!-- GENERATED STUB (YET-2891): api-codegen's `-mcp-reference` mode will replace this file whole from the
     REST API v2 OpenAPI document; do not hand-edit once that lands. Until then this stub lists the operations
     of the tag by `operationId`, which is the MCP tool name, with the arguments the spec declares. -->

Monte Carlo REST API v2 operations of the `users` tag. Each heading is the tool name once the Monte Carlo MCP
server exposes it. Operations marked **not an MCP tool** are reachable through the CLI, Terraform or the SDK only,
because their request or response carries a secret.

## `get_current_user`: Get the current user

Return the identity this request was authenticated as, along with its account.

### Arguments

None.

### Response

Response fields: user_id, email, first_name, last_name, identity_type, account_id, account_name, account_frozen, auth_groups.
