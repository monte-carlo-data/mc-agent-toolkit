# Freshness Investigation Playbook

Use this when a table hasn't updated on its expected schedule.

## Investigation steps

### 1. Confirm the freshness delay

Call `get_table_freshness` with the table's `full_table_id` and `resource_id`. Check:
- When was the last successful update?
- What's the normal update cadence? (hourly, daily, etc.)
- How long has the delay been?

### 2. Check the ETL pipeline

The table is populated by an ETL pipeline. Check if the pipeline failed:

**Airflow:**
- Call `get_etl_jobs` with `platform="airflow"` to find which DAGs/tasks write to this table
- Call `get_etl_issues` with `platform="airflow"` and a time range — look for task failures, retries, or SLA misses

**dbt:**
- Call `get_etl_jobs` with `platform="dbt"` to find which dbt jobs/models produce this table
- Call `get_etl_issues` with `platform="dbt"` — look for compilation errors, test failures, or timeouts

**Databricks:**
- Call `get_etl_jobs` with `platform="databricks"` to find relevant jobs
- Call `get_etl_issues` with `platform="databricks"` — look for notebook failures, cluster issues

### 3. Check the write queries

Call `get_queries_for_table(mcon=table_mcon, query_type="destination")` to see recent write queries:
- Did write queries stop running entirely? → pipeline scheduling issue
- Did write queries run but with errors? → data or permission issue
- Did write queries run successfully but produce no rows? → upstream data issue

### 4. Check upstream freshness

Call `get_asset_lineage(mcons=[table_mcon], direction="UPSTREAM")` to find upstream tables, then:
- Call `get_table_freshness` on each upstream table
- If an upstream table is also stale, the issue is propagating from there
- Recurse upstream until you find the root source of the delay

### 5. Check ETL job performance

Call `get_jobs_performance` to check if the ETL job's runtime has degraded:
- Is the job taking longer than usual? (compare `avgDuration` to 7-day trend)
- Is the job failing more often? (check `failureRate`)
- Is the job currently running or stuck? (check last run status)
- A job that's running but taking 3x longer than normal may explain the freshness delay without an outright failure

Also call `get_etl_jobs` with the relevant `platform` and the table MCONs to find which specific jobs write to this table, then check their issues with `get_etl_issues`.

### 6. Check for query changes

Call `get_query_changes` — did someone modify the ETL query recently?
- New JOINs that produce empty results
- Changed WHERE clauses that filter out all data
- Modified schedule or dependency

## Common root causes

- **Pipeline scheduling failure** — cron job stopped, DAG was paused, permissions revoked
- **Upstream freshness cascade** — an upstream table is stale, blocking this table's refresh
- **Query timeout** — the refresh query is taking too long and timing out
- **Resource contention** — warehouse is overloaded, queries are queued
- **Permission change** — service account lost access to source data
