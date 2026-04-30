# Tuning Table Monitors

This reference covers type-specific tuning guidance for table monitors. Read this file after
determining the monitor type in Phase 1.5.

Table monitors cover multiple tables and metrics (freshness, volume change, unchanged size,
schema). Each (table, metric) pair can be tuned independently.

## Config fields to extract

Extract these from the monitor report for your Phase 2 analysis:

- Which tables and metrics the monitor covers
- Per (table, metric) pair: current sensitivity or explicit threshold
- Which (table, metric) pairs are firing and how often
- The metric type for each anomaly: `last_updated_on` (freshness), `total_row_count` /
  `total_byte_count` (volume change), `total_row_count_last_changed_on` /
  `total_byte_count_last_changed_on` (unchanged size), or schema

---

## Key constraint: one recommendation per (table, metric) pair

Each recommendation **MUST** target exactly one table MCON and one metric. Do NOT group multiple
tables into a single recommendation, even if the change is identical. The apply step makes one
tool call per recommendation.

---

## Correlated anomalies

When multiple (table, metric) pairs fire within a short window (minutes to a few hours), they
likely share a common cause — e.g., a delayed pipeline affects freshness across several tables,
or a bulk load triggers volume anomalies on related tables. Before counting anomalies per pair,
group alerts by time proximity and assess whether they stem from the same upstream event. A burst
of correlated alerts is one noise source, not many independent ones — address the root cause
rather than tuning each pair separately.

---

## Minimum anomaly threshold

Only recommend tuning a (table, metric) pair if it has **3 or more anomalies** in the report.
A pair with 1-2 anomalies is not a clear noise pattern — it could be legitimate.

For pairs with only 3-4 anomalies, require **strong supporting evidence**: consistent marginal
breaches, TSA confirming normal variation, or NOT_ACKNOWLEDGED status on all. A handful of
anomalies alone is not enough — the pattern must clearly indicate noise.

---

## Tuning levers by metric

### Freshness (`last_updated_on`)

- **Sensitivity**: LOW / MEDIUM / HIGH. Lower when tables have known late-arriving data.
- **Explicit threshold**: set a fixed threshold in minutes. Use when the table has a known SLA
  (e.g., "this table updates every 6 hours -> set threshold to 420 minutes").
- Use the delay and threshold values from the incident to judge whether the current sensitivity
  is too tight.

### Volume change (`total_row_count`, `total_byte_count`)

- **Sensitivity**: LOW / MEDIUM / HIGH. Lower for tables with bursty or seasonal patterns.
- **Explicit thresholds**: set `upper_threshold_pct` and `lower_threshold_pct` (e.g., 50 means
  50% change). Also requires `threshold_lookback_minutes`.
- Check the delta vs threshold in the incident — if deltas are consistently just above the auto
  threshold, lower sensitivity. If the expected range is known, use explicit thresholds.

### Unchanged size (`total_row_count_last_changed_on`, `total_byte_count_last_changed_on`)

- **Sensitivity**: LOW / MEDIUM / HIGH. Lower for tables that legitimately go quiet (weekends,
  batch jobs).
- **Explicit threshold**: set a fixed threshold in minutes for how long the table can remain
  unchanged before alerting.
- Check "time since update" vs threshold in the incident — if the table regularly goes quiet
  for known periods, set an explicit threshold above that period.

### Schema anomalies

**Do NOT recommend changes for schema anomalies** — they are not tunable via the
`tune_*_table_monitor` tools.

---

## Sensitivity vs explicit thresholds

For ML thresholds (`threshold_type=auto`), always try **lowering sensitivity first**. Only
switch to explicit thresholds if:
- The lowest sensitivity still fires on expected behavior, OR
- The user has a clear SLA or schedule that makes a fixed threshold more appropriate

---

## Applying changes

Table monitor tuning uses per-metric tools — **not** `create_table_monitor`:

| Metric | Tool |
|---|---|
| Freshness (`last_updated_on`) | `tune_freshness_table_monitor` |
| Volume change (`total_row_count`) | `tune_volume_change_table_monitor` |
| Unchanged size (`total_row_count_last_changed_on`) | `tune_unchanged_size_table_monitor` |

Each tool call targets one (MCON, metric) pair:
- For sensitivity changes: pass `mcon` and `sensitivity`.
- For explicit thresholds: pass `mcon` and the threshold parameters.

1. **Always preview first** — show the user the planned changes per (table, metric) pair and
   ask for confirmation before applying.
2. **On confirmation**, make one tool call per recommendation.

### Common mistakes

- **NEVER** apply changes without showing the preview first.
- **NEVER** group multiple tables into one recommendation — one tool call per (MCON, metric).
- **NEVER** recommend tuning schema anomalies — they are not supported.
- **IMPORTANT:** These mutations are full replacements. Pass `tags` if the current config has
  any — omitting tags clears them.
