# Safe-Change Plugin — Future Improvements

Tracked issues and enhancements discovered during Phase 1 development and testing.

---

## SKILL.md: Monitor offer missing for new models

**Discovered:** 2026-03-24
**Severity:** Medium — missing observability nudge

When creating a brand new dbt model, Workflow 4 runs the "upstream health check" variant instead of the full change impact assessment. The synthesis step that offers Workflow 2 (monitor generation) at SKILL.md lines 428-435 is only reached during the existing-model flow.

**Result:** New models get created with zero monitor coverage and no offer to add one.

**Fix:** Add explicit instruction to the new-model section of SKILL.md:
> "For new models: after the upstream health report, always offer Workflow 2 to generate monitors for the new model's output columns. New models have zero observability by default — this is the best time to add it."

---

## detect.py: Extend beyond dbt

**Discovered:** 2026-03-24 (design phase)
**Severity:** Low — Phase 1 scoped to dbt only

`is_dbt_model()` only recognizes files under `/models/` with `{{ ref(` or `{{ source(` patterns. Future SQL transformation frameworks (SQLMesh, Dataform, plain SQL) are not detected.

**Fix:** Add pluggable detection functions in `detect.py` — one function per framework, called in sequence.

---

## Pre-edit hook: New file creation may bypass blocking

**Discovered:** 2026-03-24 (testing)
**Severity:** Low — SKILL.md covers this case

When Claude creates a new `.sql` file with `Write`, the file doesn't exist yet when `is_dbt_model()` tries to read it to check for `{{ ref(`. The hook may let the first Write through because it can't verify the file is a dbt model.

**Current mitigation:** SKILL.md instructs Claude to run Workflow 4 before writing any SQL model. The hook is a safety net, not the primary enforcement for new files.

**Possible fix:** For `Write` (not `Edit`), inspect `tool_input.content` instead of reading the file from disk.

---

## Expand file detection beyond `/models/*.sql`

**Discovered:** 2026-03-24 (design discussion)
**Severity:** Medium — broadens coverage of data-impacting changes

Phase 1 targets `.sql` files under `/models/` with `{{ ref(` or `{{ source(` patterns. This covers the highest-impact dbt changes but misses other data-impacting file types within dbt projects.

### dbt-internal gaps (high priority)

| Pattern | Risk | Notes |
|---|---|---|
| `/macros/*.sql` | High | A single macro change can silently alter many models that call it. Detection needs downstream tracing to identify affected models. |
| `/snapshots/*.sql` | High | SCD Type 2 tables — incorrect snapshot logic corrupts historical data and is hard to undo. |
| `dbt_project.yml` | Medium | Project config changes can alter materializations (view→table), target schemas, and vars that flow into model logic. |
| `/models/**/*.yml` with `materialized:` | Medium | Schema-level materialization overrides can change how models are built. |
| `/seeds/*.csv` | Low | Static reference data loaded into warehouse — changes affect downstream models that `{{ ref() }}` the seed. |

### Beyond dbt (future framework support)

| Framework | File patterns | Notes |
|---|---|---|
| **SQLMesh** | `/models/*.sql` | Structurally similar to dbt — detection logic ports easily. Has built-in column-level lineage. |
| **Airflow** | `dags/*.py` with embedded SQL | Python DAG files — harder to detect data impact; look for `sql=` parameters and SQL template files. |
| **Spark / PySpark / Databricks** | `.py` with `spark.sql()`, `.ipynb` notebooks | DataFrame operations and SparkSQL — detection requires Python AST analysis or pattern matching. |
| **Stored procedures / SQL migrations** | `migrations/*.sql`, `procedures/*.sql` | Common in enterprises using Flyway, Liquibase, or Alembic. Predictable directory structure. |
| **LookML (Looker)** | `.lkml` files | Semantic layer — changing a dimension/measure can break dashboards. Different risk profile than transformations. |

### Recommended approach

1. **Phase 2:** Add macro and snapshot detection within dbt projects (highest incremental value)
2. **Phase 3:** Add SQLMesh support (low effort given structural similarity to dbt)
3. **Phase 4:** Evaluate Airflow/Spark support (requires different detection strategies)

The adapter pattern in `detect.py` is already designed for this — add one detection function per framework, called in sequence.

---

## Dedicated MCP endpoint for Claude Code

**Discovered:** 2026-03-24 (design phase)
**Severity:** Low — Phase 2 scope

Currently using `/mcp/`. A dedicated `/mcp/editor/claude/` endpoint would enable:
- Usage tracking per editor integration
- Session tracing back into Monte Carlo (Phase 2)
- Editor-specific response tailoring

**Fix:** Single-line change in `plugin.json` MCP server args when the endpoint is ready.
