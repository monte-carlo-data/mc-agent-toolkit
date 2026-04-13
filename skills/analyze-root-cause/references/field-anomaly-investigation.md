# Field Anomaly Investigation Playbook

Use this when a field-level metric drifted (null rate spike, mean shift, distribution change).

## Investigation steps

### 1. Understand the anomaly

From the alert details, identify:
- Which field/column is affected?
- What metric changed? (null rate, mean, max, min, uniqueness, etc.)
- When did the change occur?
- What was the expected vs actual value?

### 2. Trace field lineage

Call `get_field_lineage` to find where this field's data comes from:
- Which upstream table and column feeds this field?
- Is the upstream field also anomalous?
- Walk the field lineage chain upstream until you find the source of the bad data

### 3. Check for correlated anomalies

Call `get_alerts` with a time range around the incident:
- Are there other alerts on the same table at the same time? (volume, freshness)
- Are there alerts on upstream tables?
- Multiple correlated anomalies often point to a single root cause

### 4. Check for query changes

Call `get_query_changes` — did the ETL query modify how this field is computed?
- Changed CASE WHEN logic → different values
- Changed COALESCE or NULL handling → null rate changes
- Changed aggregation → mean/sum shifts
- Changed type casting → precision changes

### 5. Profile the data (if DB connector available)

Run targeted queries to understand the field's behavior:

```sql
-- Null rate over time
SELECT DATE_TRUNC('day', timestamp_col) AS day,
       COUNT(*) AS total,
       COUNT(field_name) AS non_null,
       1.0 - COUNT(field_name) / COUNT(*) AS null_rate
FROM table
WHERE timestamp_col >= DATEADD('day', -14, CURRENT_TIMESTAMP())
GROUP BY 1 ORDER BY 1

-- Value distribution shift
SELECT field_name, COUNT(*) AS cnt
FROM table
WHERE timestamp_col >= DATEADD('day', -1, CURRENT_TIMESTAMP())
GROUP BY 1 ORDER BY 2 DESC LIMIT 20

-- Check what upstream values correlate with the anomaly
SELECT upstream_table.key_field,
       COUNT(*) AS affected_rows,
       AVG(this_table.anomalous_field) AS avg_value
FROM this_table
JOIN upstream_table ON this_table.fk = upstream_table.pk
WHERE this_table.timestamp_col >= 'anomaly_start_time'
GROUP BY 1 ORDER BY 2 DESC
```

See `references/data-exploration.md` for more patterns.

### 6. Check upstream data quality

For the upstream table/field identified in Step 2:
- Call `get_table_freshness` — is the upstream data fresh?
- Call `get_table_size_history` — did upstream volume change?
- If DB connector available, profile the upstream field directly

## Common root causes

- **Upstream data quality issue** — bad data in source propagated downstream
- **ETL logic change** — CASE/COALESCE/type handling modified
- **New data source** — a new upstream source introduced unexpected values
- **Schema change** — column type changed, causing implicit conversions
- **Backfill** — historical data reprocessed with different logic
- **Null propagation** — upstream NULL values cascading through JOINs
