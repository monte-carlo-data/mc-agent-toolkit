# MCP Parameter Notes

Important parameter details for Monte Carlo MCP tools. Consult when making API
calls to avoid common mistakes.

---

## `getAlerts` — use snake_case parameters

The MCP tool uses Python snake_case, **not** the camelCase params from the MC web UI:

```
✓ created_after    (not createdTime.after)
✓ created_before   (not createdTime.before)
✓ order_by         (not orderBy)
✓ table_mcons      (not tableMcons)
```

Always provide `created_after` and `created_before`. Max window is 60 days.
Pass ISO 8601 timestamps computed from the current date — e.g. for a 7-day
window ending now: `created_after="2026-07-03T00:00:00Z"`,
`created_before="2026-07-10T00:00:00Z"` (use the actual current date).

---

## `search` — finding the right table identifier

MC uses MCONs (Monte Carlo Object Names) as table identifiers. Always use
`search` first to resolve a table name to its MCON before calling `getTable`,
`getAssetLineage`, or `getAlerts`.

```
search(query="orders_status") → returns mcon, full_table_id, warehouse
```
