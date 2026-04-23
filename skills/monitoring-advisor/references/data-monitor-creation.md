# Data Monitor Creation Procedure

This is the data monitor creation procedure for Monte Carlo warehouse tables. Use this reference when a user wants to create monitors for their data warehouse tables -- it walks through the full workflow from understanding the request through generating monitors-as-code (MaC) YAML.

All creation tools run in **dry-run mode** and return MaC YAML. No monitors are created directly -- the user applies the YAML via the Monte Carlo CLI or CI/CD.

---

## Validation Phase (Steps 1-3)

**CRITICAL: Do not call creation tools before the validation phase is complete.** The number one error pattern is agents skipping validation and calling a creation tool with guessed or incomplete parameters. Every field in the creation call must be grounded in data retrieved during this phase.

### Step 1: Understand the request

Ask yourself:
- What does the user want to monitor? (a specific table, a metric, a data quality rule, cross-table consistency, freshness/volume at schema level)
- Which monitor type fits? Use the monitor type selection table below.
- Does the user have all the details, or do they need guidance?

If the user's intent is unclear, ask a focused question before proceeding.

### Step 2: Identify the table(s) and columns

If you don't have the table MCON:
1. Use `search` with the table name and `include_fields: ["field_names"]` to find the MCON and get column names.
2. If the user provided a full table ID like `database:schema.table`, search for it.
3. Once you have the MCON, call `get_table` with `include_fields: true` and `include_table_capabilities: true` to verify capabilities and get domain info.

If you already have the MCON:
1. Call `get_table` with the MCON, `include_fields: true`, and `include_table_capabilities: true`.

**CRITICAL: You need the actual column names from `get_table` results. NEVER guess or hallucinate column names.** This is the most common source of monitor creation failures.

For monitor types that require a timestamp column (metric monitors), review the column names and identify likely timestamp candidates. Present them to the user if ambiguous.

### Step 3: Handle domain assignment

**ALWAYS resolve a `domain_uuids` value BEFORE calling any creation tool.** Missing or empty domain assignment is one of the top failure modes — the backend will reject the monitor with `Domain assignment is required for this monitor. Please provide one and only one valid domain UUID.`

The tool field is `domain_uuids` (a list). For data monitors, provide exactly one UUID.

Use the `domains` list on the `get_table` response (each entry has `uuid` and `name`):

1. If the table's `domains` has exactly one entry: default `domain_uuids` to `[<that uuid>]`.
2. If the table's `domains` has multiple entries: present only those domains and ask the user to pick.
3. If the table's `domains` is empty: call `get_domains` to see the account's domains. If the account has one or more, ask the user to pick one (do not invent a selection) -- note that domains that don't contain the table may still be rejected on apply. If `get_domains` returns zero domains, only then may `domain_uuids` be omitted.

Do NOT present all account domains as options when the table already has domains listed -- prefer domains that contain the table.

---

## Creation Phase (Steps 4-8)

Only enter this phase after the validation phase is complete with real data from MCP tools.

### Step 4: Load the per-type reference

Based on the monitor type, read the detailed reference for parameter guidance:

| Type           | Reference file               |
| -------------- | ---------------------------- |
| **Metric**     | `data-metric-monitor.md`     |
| **Validation** | `data-validation-monitor.md` |
| **Custom SQL** | `data-custom-sql-monitor.md` |
| **Comparison** | `data-comparison-monitor.md` |
| **Table**      | `data-table-monitor.md`      |

All reference files are in the same directory as this file.

### Step 5: Ask about scheduling

**Skip this step for table monitors.** Table monitors do not support the `schedule` field in MaC YAML -- adding it will cause a validation error on `montecarlo monitors apply`. Table monitor scheduling is managed automatically by Monte Carlo.

For all other monitor types, the creation tools default to a fixed schedule running every 60 minutes. Present these options:

1. **Fixed interval** -- any integer for `interval_minutes` (30, 60, 90, 120, 360, 720, 1440, etc.)
2. **Dynamic** -- MC auto-determines when to run based on table update patterns.
3. **Loose** -- runs once per day.

Schedule format in MaC YAML:
- Fixed: `schedule: { type: fixed, interval_minutes: <N> }`
- Dynamic: `schedule: { type: dynamic }`
- Loose: `schedule: { type: loose, start_time: "00:00" }`

### Step 6: Confirm with the user

**NEVER skip the confirmation step.**

Before calling the creation tool, present the monitor configuration in plain language:
- Monitor type
- Target table (and columns if applicable)
- What it checks / what triggers an alert
- Domain assignment
- Schedule

Ask: "Does this look correct? I'll generate the monitor configuration."

### Step 7: Create the monitor

Call the appropriate creation tool with the parameters built in previous steps. Always pass an MCON when possible. If only table name is available, also pass warehouse.

### Step 8: Present results

**CRITICAL: Always include the YAML in your response.** The user needs copy-pasteable YAML.

1. If a non-default schedule was chosen, modify the schedule section in the YAML before presenting.
2. Wrap the YAML in the full MaC structure (see MaC YAML format below).
3. ALWAYS present the full YAML in a ```yaml code block.
4. Explain where to put it and how to apply it (see below).
5. ALWAYS use ISO 8601 format for datetime values.
6. **NEVER reformat YAML values returned by creation tools.**

---

## Monitor Type Selection

| Type           | Creation tool                  | Use when                                                                                                                               |
| -------------- | ------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------- |
| **Metric**     | `create_metric_monitor_mac`     | Track statistical metrics on fields (null rates, unique counts, numeric stats) or row count changes over time. Requires a timestamp field for aggregation. |
| **Validation** | `create_validation_monitor_mac` | Row-level data quality checks with conditions (e.g. "field X is never null", "status is in allowed set"). Alerts on INVALID data.      |
| **Custom SQL** | `create_custom_sql_monitor_mac` | Run arbitrary SQL returning a single number and alert on thresholds. Most flexible; use when other types don't fit.                    |
| **Comparison** | `create_comparison_monitor_mac` | Compare metrics between two tables (e.g. dev vs prod, source vs target).                                                              |
| **Table**      | `create_table_monitor_mac`      | Monitor groups of tables for freshness, schema changes, and volume. Uses asset selection at database/schema level.                     |

Per-type reference files with detailed parameter guidance, constraints, and examples:
- `data-metric-monitor.md`
- `data-validation-monitor.md`
- `data-custom-sql-monitor.md`
- `data-comparison-monitor.md`
- `data-table-monitor.md`

---

## MaC YAML Format

The YAML returned by creation tools is the monitor definition. It must be wrapped in the standard MaC structure to be applied:

```yaml
montecarlo:
  <monitor_type>:
    - <returned yaml>
```

For example, a metric monitor would look like:

```yaml
montecarlo:
  metric:
    - <yaml returned by create_metric_monitor_mac>
```

**Important:** `montecarlo.yml` (without a directory path) is a separate Monte Carlo project configuration file -- it is NOT the same as a monitor definition file. Monitor definitions go in their own `.yml` files, typically in a `monitors/` directory or alongside dbt model schema files.

Tell the user:
- Save the YAML to a `.yml` file (e.g. `monitors/<table_name>.yml` or in their dbt schema)
- Apply via the Monte Carlo CLI: `montecarlo monitors apply --namespace <namespace>`
- Or integrate into CI/CD for automatic deployment on merge

---

## Available MCP Tools

All tools are available via the `monte-carlo` MCP server.

| Tool                            | Purpose                                                      |
| ------------------------------- | ------------------------------------------------------------ |
| `test_connection`               | Verify auth and connectivity before starting                 |
| `search`                        | Find tables/assets by name; use `include_fields` for columns |
| `get_table`                     | Schema, stats, metadata, domain membership, capabilities     |
| `get_validation_predicates`     | List available validation rule types for a warehouse         |
| `get_domains`                   | List MC domains (only needed if table has no domain info)    |
| `create_metric_monitor_mac`     | Generate metric monitor YAML (dry-run)                       |
| `create_validation_monitor_mac` | Generate validation monitor YAML (dry-run)                   |
| `create_comparison_monitor_mac` | Generate comparison monitor YAML (dry-run)                   |
| `create_custom_sql_monitor_mac` | Generate custom SQL monitor YAML (dry-run)                   |
| `create_table_monitor_mac`      | Generate table monitor YAML (dry-run)                        |
