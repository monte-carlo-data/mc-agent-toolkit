# Storage Cost Analysis Skill

Identifies storage waste patterns and recommends safe cleanup actions with cost savings estimates.

## What it does

- Delegates analysis to the `analyze_storage_costs` MCP tool, which fetches candidates, classifies waste patterns and table categories, and computes safety tiers
- Presents the pre-formatted summary + Top-N table verbatim
- Handles follow-ups: drill into a specific category without re-fetching, or run a lineage check for a specific table
- Never recommends removing tables with downstream consumers without explicit verification

## Supported warehouses

Snowflake, BigQuery, Redshift, and Databricks. Other warehouse types are out of scope.

## MCP Tools Required

Connect to Monte Carlo's MCP server (`mcp.getmontecarlo.com/mcp`). The skill uses these tools:

| Tool | Purpose |
|------|---------|
| `analyze_storage_costs` | Runs the full pipeline: candidates → waste patterns → categories → safety tiers → formatted output |
| `get_asset_lineage` | Follow-up lineage checks for a specific table before removal |

## Example prompts

- "Which tables are wasting storage in our Snowflake warehouse?"
- "Find unused tables I can safely drop"
- "How much could we save by cleaning up stale tables?"
- "Are there any zombie tables in the analytics schema?"
- Follow-up: "show me the temporary tables" / "what about production?"
- Follow-up: "is it safe to remove `db.schema.table`?"

## Waste patterns and categories

The `analyze_storage_costs` tool classifies each candidate into:

- A **waste pattern**: Unread, Write-only, Dead-end, Static waste, Zombie, Other stale
- A **table category**: Temporary/Staging, Archive/Snapshot, Production, Other

The skill itself does not re-implement the taxonomy — the server owns it. See `references/output-structure.md` for the output contract (region markers, category keys, safety-signal glossary).
