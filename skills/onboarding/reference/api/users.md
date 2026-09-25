# `users` tools

<!-- Rendered from the REST API v2 OpenAPI document by api-codegen; do not edit. -->

Monte Carlo REST API v2 tools of the `users` tag, as the Monte Carlo MCP server exposes
them. Each section is one tool; its name is the tool to call.

## `get_current_user`: Get the current user

Return the identity this request was authenticated as, along with its account.

Use it to confirm that a set of credentials works, to find out which account they belong
to, and to read the authorization groups that decide what the caller may do.

Any authenticated caller may call this operation, and it keeps answering while an account
is paused. A client can therefore learn that the account is paused, rather than only
seeing every other operation refused.

- **Effect:** read-only.

### Arguments

None.

### Response

Response fields: user_id, email, first_name, last_name, identity_type, account_id, account_name, account_frozen, auth_groups.

| Field | Description |
|---|---|
| `user_id` | Unique identifier of the user. |
| `email` | Email address of the user. An identity with no mailbox of its own, such as an AI agent, carries a display label here instead. |
| `first_name` | Given name of the user. Null when it is not set. |
| `last_name` | Family name of the user. Null when it is not set. |
| `identity_type` | What kind of identity this is. It does not decide what the identity may do — that comes from the authorization groups it belongs to. |
| `account_id` | Unique identifier of the caller's account. |
| `account_name` | Display name of the account. Null when the account has no name. |
| `account_frozen` | Whether the account is paused. While it is, this endpoint still answers but every other one returns 403 with the code `account_frozen`. |
| `auth_groups` | Names of the authorization groups this user belongs to. They determine what the user is permitted to do. |

### What can fail

- Authentication credentials are missing or invalid.
- The request was authenticated, but the caller is not allowed to perform this operation. Read `code` to tell the reasons apart: `account_frozen` means the account is paused, rather than that the caller lacks permission.
- An unexpected error prevented the request from being processed.
