# Storage Cost Analysis Skill

Identifies storage waste patterns and recommends safe cleanup actions with cost savings estimates.

## What it does

- Finds tables wasting storage: unread, write-only, dead-end, zombie, bulk-loaded, and stale tables
- Classifies each into a waste pattern with clear explanation
- Computes safety tiers using lineage, query activity, importance scores, and monitoring status
- Estimates cost savings (Snowflake: ~$23/TB/month)
- Never recommends removing tables with downstream consumers without explicit verification

## MCP Tools Required

Connect to Monte Carlo's MCP server (`integrations.getmontecarlo.com/mcp`). The skill uses these tools:

| Tool | Purpose |
|------|---------|
| `search` | Find tables, filter by monitoring status and importance |
| `get_table` | Table metadata (size, type, timestamps) |
| `get_asset_lineage` | Check downstream dependencies before recommending removal |
| `get_queries_for_table` | Check read/write query activity |
| `get_warehouses` | List available warehouses |

## Example prompts

- "Which tables are wasting storage in our Snowflake warehouse?"
- "Find unused tables I can safely drop"
- "How much could we save by cleaning up stale tables?"
- "Are there any zombie tables in the analytics schema?"

## Waste patterns detected

| Pattern | Description |
|---------|-------------|
| Unread | Zero read queries -- nobody uses this table |
| Write-Only | ETL writes but nobody reads |
| Dead-End | Receives upstream data but serves nothing downstream |
| Bulk-Loaded | File loads nobody consumes |
| Static Waste | Size unchanged, no reads in 90+ days |
| Zombie | Forgotten, low importance, unmonitored |

See `references/waste-patterns.md` for full classification criteria.
