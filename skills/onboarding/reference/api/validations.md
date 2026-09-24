# `validations` tools

<!-- GENERATED STUB: api-codegen's `-mcp-reference` mode will replace this file whole from the
     REST API v2 OpenAPI document; do not hand-edit once that lands. -->

Monte Carlo REST API v2 operations of the `validations` tag. Each heading is the tool name once the Monte Carlo MCP
server exposes it.

## `get_validation_run`: Get a validation run

Read a validation run started by a validate operation. Poll until `status` is `completed`, honoring the `Retry-After` the response carries; each validation then carries its own `passed` verdict with the problems behind it. A run is kept for a limited time and then forgotten: an id that expired, never existed or belongs to another account returns 404.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `run_id` | `str` | yes | Id of the run, as returned by validate_connection. |

### Response

Response fields: id, status, target_type, target_id, validations_passed, validations_total, started_at, finished_at, expires_at, validations.
