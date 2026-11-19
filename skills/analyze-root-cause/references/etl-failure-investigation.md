# ETL Failure Investigation Playbook

Use this when an Airflow DAG, dbt model, or Databricks job failed.

## Investigation steps

### 1. Identify the failure

Based on the alert or user description, determine which platform:

**Airflow:**
- Call `get_etl_jobs` with `platform="airflow"` and the affected table MCONs to find which DAGs/tasks write to these tables
- Call `get_etl_issues` with `platform="airflow"` and a time range — look for:
  - Task failure error messages
  - Retry counts (high retries = flaky task)
  - SLA misses
  - Upstream task failures that blocked downstream tasks

**dbt:**
- Call `get_etl_jobs` with `platform="dbt"` and the affected table MCONs to find which dbt jobs write to these tables
- Call `get_etl_issues` with `platform="dbt"` — look for:
  - Compilation errors (bad SQL syntax, missing refs)
  - Test failures (data quality assertions)
  - Timeout errors
  - Dependency failures (upstream model failed)

**Databricks:**
- Call `get_etl_jobs` with `platform="databricks"` and the affected table MCONs to find which Databricks jobs write to these tables
- Call `get_etl_issues` with `platform="databricks"` — look for:
  - Notebook execution errors
  - Cluster startup failures
  - Out of memory errors
  - Permission denied errors

### 2. Check what tables are affected

Call `get_asset_lineage(mcons=[table_mcon], direction="DOWNSTREAM")`:
- Which downstream tables couldn't refresh because this pipeline failed?
- How many consumers are impacted?

### 3. Check for recent changes

Call `get_change_timeline` — was there a code change around the failure time?
- Query text modifications right before the failure → code regression
- Volume spike right before the failure → data volume overwhelmed the pipeline

### 4. Check for query-level issues

Call `get_query_rca` with the affected table MCONs:
- **Failed** patterns: what errors are the queries hitting?
- **Futile** patterns: are queries running but producing nothing?
- Look at error messages for clues (timeout, permission, missing object)

### 5. Check job runtime trends and current status

Call `get_jobs_performance` to see runtime stats, failure rates, and current status:
- Gradual slowdown → growing data volume or inefficient query
- Sudden spike → query regression or resource contention

## Common root causes

- **Code deployment** — new dbt model or query has a bug
- **Data volume spike** — source data grew faster than the pipeline can process
- **Permission change** — service account lost access
- **Infrastructure** — cluster sizing, warehouse suspension, network issues
- **Dependency failure** — upstream pipeline failed, cascading downstream
- **Schema mismatch** — upstream schema changed, breaking the ETL query
