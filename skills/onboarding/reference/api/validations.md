# `validations` tools

<!-- Rendered from the REST API v2 OpenAPI document by api-codegen; do not edit. -->

Monte Carlo REST API v2 tools of the `validations` tag, as the Monte Carlo MCP server exposes
them. Each section is one tool; its name is the tool to call.

## `get_validation_run`: Get a validation run

Read a validation run started by a validate operation.

Poll this until `status` is `completed`. Each validation carries its own `status` and,
once it has one, a `passed` verdict with the problems behind it.

Pass the `revision` from each response as `since` on the next poll to get only the
validations that changed. The run's other fields are always returned in full.

A response with the run carries an `ETag`. Send it back as `If-None-Match` to get a 304 with no
body when nothing has changed.

A run is kept for a limited time after it starts and then forgotten. An id that has
expired, never existed, or belongs to another account all return 404.

`Retry-After` says how long to wait before polling again.

- **Effect:** read-only.

### Arguments

| Argument | Type | Required | Description |
|---|---|---|---|
| `run_id` | `str` | yes | Id of the validation run, as returned by the operation that started it. |
| `since` | `int` | no | The `revision` from the previous response. Only validations that changed after it are returned. Omit it to get every validation. |

### Response

Response fields: id, status, revision, target_type, target_id, validations_passed, validations_total, started_at, finished_at, expires_at, validations.

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
- The run does not exist, or is not visible to the caller.
- An argument is invalid; the error names the field.
- An unexpected error prevented the request from being processed.
- Monte Carlo is busy or temporarily unavailable; try again after a moment.
