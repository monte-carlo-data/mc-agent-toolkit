# Tuning Metric Monitors

This reference covers type-specific tuning guidance for metric monitors. Read this file after
determining the monitor type in Phase 1.5.

## Config fields to extract

Extract these from the `get_monitors` config response for your Phase 2 analysis:

- Monitor metric (e.g., `RELATIVE_ROW_COUNT`, `NULL_RATE`, `NUMERIC_MEAN`)
- Segment field(s) (`segment_fields`)
- WHERE condition (`where_condition`)
- Aggregation bucket (`aggregate_by`: `hour`, `day`, `week`, `month`)
- Aggregation time field (`aggregate_time_field`)
- Collection lag (`collection_lag_minutes`)

---

## Threshold adjustment (explicit thresholds)

For metric monitors using explicit thresholds (`GT`, `LT`, `GTE`, `LTE`, `EQ`, `NE`) instead of
`AUTO`:

- If anomalies are consistently marginal — the observed value just barely crosses the threshold —
  recommend loosening the threshold based on observed values from the report.
- **CRITICAL:** Always explain what the threshold value represents in the context of the metric
  before recommending a change. For example, "NULL_RATE GT 0.05 means alert when more than 5% of
  values are null."
- **NEVER** recommend a threshold change without citing observed anomaly values from the report.

---

## WHERE condition / segment exclusion

**When to recommend a WHERE condition:**
- One or more specific segment values fire repeatedly and are assessed as expected behavior
  (e.g., a sparse/bursty event type, a scheduled batch event)
- The noisy segments are identifiable from the incident history

**Syntax examples:**
```yaml
where_condition: "event_type NOT IN ('inactive_monitor', 'agent_evaluation_anom')"
```
```yaml
where_condition: "status != 'test'"
```

**IMPORTANT:** Always verify the column name and values exist in the table before recommending a
WHERE condition. Reference specific segment values from the monitor report.

**High-cardinality segments:**
- If the segment field has very high cardinality with many sparse values → recommend
  `"high_segment_count": true` or consider removing segmentation entirely
- **NEVER** recommend removing segmentation without explaining what signal would be lost

---

## Aggregation bucket changes

If the monitor aggregates by `hour` and anomalies are caused by sparse or bursty segments
(e.g., event types that fire only at certain hours), switching to `"aggregate_by": "day"` can
dramatically reduce false positives. The daily bucket smooths out intra-day spikes that are
normal over a 24-hour window.

**When to recommend:**
- Anomaly values are marginal at the hour level but would be within range at the daily level
- The segment naturally has low and variable hourly counts

**Trade-off:** You lose hourly granularity and may detect issues later. Always state this.

**CRITICAL:** Do not recommend changing `aggregate_by` without also checking whether the
`interval_minutes` needs to align. Hourly aggregation requires a schedule ≥60 min; daily
requires ≥1440 min.

---

## Monitor restructure

Recommend splitting into separate monitors when:
- Different segment values have fundamentally different expected behaviors (e.g., one segment
  is bursty by design, another should be steady)
- No single `where_condition` can cleanly separate noisy segments from signal-carrying ones

Recommend reviewing whether the metric and field combination is the right approach when:
- The monitor consistently fires on patterns that are inherent to the data shape
- A different metric would better capture the actual data quality concern

---

## Applying changes

Use `create_metric_monitor` to update the monitor.

1. **Always pass the existing `uuid`** to update rather than create a new monitor.
2. **Always dry-run first** (`dry_run=True`, the default) — show the user the YAML preview and
   ask for confirmation before applying.
3. **On confirmation**, call again with `dry_run=False`.
4. **Check the returned UUID** — if it differs from the one you passed, tell the user the old
   monitor was replaced with a new one.

### Common mistakes

- **NEVER** omit the `uuid` field — this creates a duplicate monitor instead of updating.
- **NEVER** apply changes without showing the dry-run preview first.
- **IMPORTANT:** When updating a single field (e.g., `where_condition`), you must still pass all
  required parameters. The tool replaces the full config, not individual fields.
