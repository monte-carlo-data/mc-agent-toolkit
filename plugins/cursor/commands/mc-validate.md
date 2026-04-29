---
description: Generate and run validation queries for the current change
---

Parse `$ARGUMENTS` to decide which mode to run. The Monte Carlo Prevent skill defines four supported invocations:

| Invocation | Mode | Workflows |
|---|---|---|
| _(empty)_ | default generate | W3 only |
| `generate` | explicit generate | W3 only |
| `run` | full validate | W4.1 (Build) → W4.2 (Execute) |
| `run --skip-build` | execute-only | W4.2 only |

`run` also accepts `--dev-db <NAME>` to bypass the dev-database prompt in W4.2. Flags can combine: `run --skip-build --dev-db <NAME>`.

**`run` does not auto-generate.** If no `validation/<table>_<ts>.sql` exists for the current session's changed models, abort and tell the engineer:

> "No validation queries found for <table_name>. Run `/mc-validate` (or `/mc-validate generate`) first to generate them, then re-run `/mc-validate run`."

**Decision rules:**

- If `$ARGUMENTS` is empty or starts with `generate`: **generate-only mode**. Run Workflow 3 from the Monte Carlo Prevent skill. Save queries to `validation/<table_name>_<timestamp>.sql`. At the end, **always offer** the four next-step options described in W3 step 6 of `references/workflows.md` (say **continue** to auto-run `/mc-validate run`, run it yourself, run with `--skip-build`, or substitute `<YOUR_DEV_DATABASE>` and run manually).

- If `$ARGUMENTS` starts with `run`: **run mode**.
  1. Verify a `validation/<table>_<ts>.sql` exists for the current session's changed models. If none exist, abort with the message above. Do **not** run W3.
  2. If `--skip-build` is **not** present: run **Workflow 4.1** (Build), then **Workflow 4.2** (Execute).
  3. If `--skip-build` **is** present: skip W4.1 and run **Workflow 4.2** directly. Assume the engineer built manually.
  4. If `--dev-db <NAME>` is present: pass `<NAME>` into W4.2 and skip its dev-database confirmation prompt.

- Any other token after `run` that isn't `--skip-build` or `--dev-db <NAME>` is an error — surface it to the engineer and stop.

Workflow definitions live in the Monte Carlo Prevent skill's `references/workflows.md`. Read that file before executing either mode.

**Arguments:** $ARGUMENTS
