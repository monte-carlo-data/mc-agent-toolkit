# Safety Tier Computation

Before recommending any action on a table, compute its safety tier. The tier is a score from 0 (safest to remove) to 5 (highest risk).

## Risk factors (each adds +1 to the safety tier)

| Factor | Description | How to check |
|--------|-------------|-------------|
| Has downstream consumers | Other tables or reports read from this table | `get_asset_lineage` with `direction=DOWNSTREAM` returns `has_relationships: true` |
| High importance score | Table has a computed importance score > 0.3 | From `search` results or `get_table` metadata |
| Is monitored | Someone cared enough to set up monitoring | `is_monitored: true` from search results |
| Has recent reads | Table was read in the last 30 days | `get_queries_for_table` with `query_type=source` shows recent activity |
| Part of critical lineage | Table is a hub or source node in a widely-used pipeline | `get_asset_lineage` with `direction=DOWNSTREAM` shows many consumers |

## Interpreting the tier

| Tier | Risk Level | Recommendation |
|------|-----------|----------------|
| 0 | Minimal | Safe to DROP. No downstream deps, no readers, not monitored, low importance. |
| 1 | Low | Likely safe to DROP. One minor risk factor. Verify before acting. |
| 2 | Moderate | Needs review. Has some usage signals. Present evidence and let user decide. |
| 3 | Elevated | Needs investigation. Multiple risk factors. Do NOT recommend removal without user review. |
| 4-5 | High | Do NOT recommend removal. Table is actively used or critical. Flag as "not a waste candidate." |

## Rules

- **Never skip the lineage check.** A table with zero reads but downstream consumers in lineage is NOT safe to remove -- the lineage relationship may represent an ETL dependency that doesn't show up in query logs.
- **Importance score is a signal, not a verdict.** Low importance + zero reads + no lineage = safe. Low importance + downstream consumers = not safe.
- **When in doubt, recommend INVESTIGATE over DROP.** The cost of keeping a table an extra month is negligible compared to the cost of breaking a pipeline.
