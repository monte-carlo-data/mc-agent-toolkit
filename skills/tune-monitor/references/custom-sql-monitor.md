# Tuning Custom SQL Monitors

This reference covers type-specific tuning guidance for custom SQL monitors (custom rules).
Read this file after determining the monitor type in Phase 1.5.

## Config fields to extract

Extract these from the `get_monitors` config response for your Phase 2 analysis:

- SQL query text (`sql` or `custom_sql`)
- Alert conditions — each has an `operator` and either a `thresholdValue` (explicit) or ML
  threshold configuration
- Warehouse name
- Schedule interval

**IMPORTANT:** Determine whether the monitor uses **ML thresholds** or **explicit thresholds**.
This affects which tuning levers are available. ML-threshold monitors support sensitivity tuning
(covered in Phase 3 of SKILL.md). Explicit-threshold monitors require direct threshold adjustment
(covered below).

---

## Threshold adjustment (explicit thresholds)

For monitors with explicit thresholds (`GT`, `LT`, `GTE`, `LTE`, `EQ`, `NE`):

**When to recommend loosening a threshold:**
- Anomalies are consistently marginal — the observed value just barely crosses the threshold
- The margin between observed and threshold is small relative to the metric's natural variance
- Most alerts are assessed as normal variation, not genuine issues

**CRITICAL:** Always explain what the threshold value represents in business terms before
recommending a change. The user needs to understand what "changing GT 0 to GT 5" means for their
data quality.

**Common pattern:** If the query returns a count of "bad" rows and the threshold is 0, but normal
operations produce 1-3 rows that match the condition (e.g., stale records, delayed updates),
recommend raising the threshold to a reasonable floor based on observed values.

**Examples:**
```yaml
# Before: fires on any bad row
alert_conditions:
  - operator: GT
    thresholdValue: 0

# After: tolerates up to 5 (based on observed noise floor of 1-3)
alert_conditions:
  - operator: GT
    thresholdValue: 5
```

**NEVER** recommend a threshold change without citing the observed anomaly values from the report.

---

## SQL query modifications

When the SQL itself contributes to noise, recommend targeted modifications:

**When to recommend SQL changes:**
- The query lacks time-window filters and picks up stale data
- Certain dimensions or categories are known-noisy and should be excluded
- NULL handling is missing and causes spurious results
- The query could benefit from a more targeted WHERE clause

**NEVER** rewrite the full SQL without showing a diff. Present the original query and the proposed
change side by side so the user can review exactly what changed.

**IMPORTANT:** SQL syntax varies by warehouse. When suggesting modifications, match the warehouse
dialect:

| Warehouse | Date arithmetic example |
|-----------|------------------------|
| Snowflake | `DATEADD('day', -7, CURRENT_TIMESTAMP())` |
| BigQuery | `TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)` |
| Redshift | `DATEADD(day, -7, GETDATE())` |
| Databricks | `DATE_SUB(CURRENT_TIMESTAMP(), 7)` |

---

## Applying changes

Use `create_custom_sql_monitor` to update the monitor.

1. **Always pass the existing identifier** to update rather than create a new monitor.
2. **Always dry-run first** — show the user the preview and ask for confirmation before applying.
3. **On confirmation**, apply the change.

### Common mistakes

- **NEVER** apply changes without showing the preview first.
- **CRITICAL:** When modifying the SQL query, ensure the query still returns a single numeric
  value. A query that returns multiple rows or non-numeric data will break the monitor.
- **IMPORTANT:** If the monitor has multiple alert conditions, ensure all conditions are included
  in the update — the tool replaces the full config, not individual conditions.
