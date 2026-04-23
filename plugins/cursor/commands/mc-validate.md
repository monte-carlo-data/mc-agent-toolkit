---
description: Generate and run validation queries for the current change
---

Parse `$ARGUMENTS` to decide which mode to run:

- If `$ARGUMENTS` starts with `run` (optionally followed by flags): **run mode**.
  Run Workflow 5 first to generate queries if they don't already exist in
  `validation/` for the current session's changed models. Then run Workflow 6
  (sandbox build) and Workflow 7 (execute validation) from the Monte Carlo
  Prevent skill.

  Supported flags after `run`:
  - `--skip-build` — do not prompt for `dbt build`; assume the user built manually.
  - `--dev-db <NAME>` — bypass the dev-database confirmation prompt and use `<NAME>` directly.
  - `--models <m1,m2,...>` — restrict the flow to a subset of changed models (same semantics as Workflow 5's `--models`).

- Otherwise (no `run` keyword): **generate-only mode** (existing behavior).
  Run Workflow 5. Save queries to `validation/<table_name>_<timestamp>.sql`.
  At the end of Workflow 5, **always offer** `/mc-validate run` as the next step:
  > "Run these against your sandbox now? (`/mc-validate run`)"

Workflow definitions live in the Monte Carlo Prevent skill's
`references/workflows.md`. Read that file before executing either mode.

**Arguments:** $ARGUMENTS
