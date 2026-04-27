# Tuning Validation Monitors

This reference covers type-specific tuning guidance for validation monitors. Read this file after
determining the monitor type in Phase 1.5.

## Config fields to extract

Extract these from the `get_monitors` config response for your Phase 2 analysis:

- Alert condition tree (`alert_condition`) — a FilterGroup with UNARY, BINARY, SQL, and/or
  nested GROUP nodes
- Table being validated
- Schedule interval
- Whether conditions use simple predicates or SQL expressions

---

## Key constraint: limited incident detail

Validation incidents only report **invalid row counts** — not what the rows contained. This
fundamentally limits what you can recommend without troubleshooting analysis (TSA).

**Without TSA:** You cannot determine _why_ rows are invalid or whether the alert condition
itself is too broad. Only schedule changes are safe to recommend.

**With TSA:** If troubleshooting analysis identifies specific values, patterns, or root causes
for the invalid rows, you can recommend alert condition modifications.

---

## Schedule tuning (always safe)

- If the monitor fires repeatedly for the same underlying issue (e.g., the same batch of invalid
  rows detected on every run) → increase the schedule interval to reduce duplicate alerts.
- If invalid rows appear only after specific ETL jobs → align the schedule to run after those
  jobs complete.

---

## Alert condition modifications (requires troubleshooting analysis)

**IMPORTANT:** Do NOT recommend alert condition changes unless TSA is present and identifies the
root cause of the invalid rows. Without knowing _what_ the invalid data looks like, condition
changes risk masking real issues.

The alert condition is a FilterGroup tree. When tuning:

### Add exclusions

Add SQL conditions or additional predicates to exclude known-valid edge cases that trigger
false positives:

```json
{
  "type": "GROUP",
  "operator": "AND",
  "conditions": [
    // ... existing conditions ...
    {
      "type": "SQL",
      "sql": "category != 'legacy_import'"
    }
  ]
}
```

### Tighten or loosen existing predicates

- If a BINARY condition threshold is too tight (e.g., `greater_than 0` but 1-3 invalid rows
  is normal) → loosen the threshold based on observed values from TSA.
- If a UNARY null check fires on a column that is legitimately nullable for certain record
  types → add an exclusion condition rather than removing the null check.

### Produce the full FilterGroup tree

When recommending changes, always output the **complete** `alert_condition` tree — not just the
modified node. The tool replaces the full condition, not individual nodes.

**NEVER** simplify or restructure the condition tree beyond the targeted change. Preserve the
existing structure and only modify what's needed.

---

## What NOT to recommend without TSA

- Removing conditions from the alert condition tree
- Changing predicate logic (e.g., `null` to `not_null`, `in_set` to different values)
- Adding new conditions based on speculation about what the invalid data might look like

If TSA is absent and the monitor is noisy, say so explicitly:

> This validation monitor is firing frequently, but without troubleshooting analysis I cannot
> determine what the invalid rows contain. I can only recommend schedule changes. To enable
> deeper tuning, run troubleshooting on recent incidents to identify the root cause.

---

## Applying changes

Use `create_validation_monitor` to update the monitor.

1. **Always pass the existing identifier** to update rather than create a new monitor.
2. **Always preview first** — show the user the full updated `alert_condition` tree and ask
   for confirmation before applying.
3. **On confirmation**, apply the change.

### Common mistakes

- **NEVER** apply changes without showing the preview first.
- **CRITICAL:** The `alert_condition` must be a dict (JSON object), never a JSON-encoded string.
- **IMPORTANT:** Always produce the full `alert_condition` tree, not just the changed node.
  The tool replaces the entire condition tree.
- **NEVER** recommend condition changes without TSA evidence — schedule changes are the only
  safe lever without it.
