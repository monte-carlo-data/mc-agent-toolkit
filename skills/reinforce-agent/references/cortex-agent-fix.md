# Fixing a Snowflake Cortex Agent

A Cortex Agent has no code repo. Its fix surface is the agent **specification** (instructions,
tools, tool resources, models), plus the semantic views, Cortex Search services and skills it
uses. This reference covers changing the specification. A fix that belongs in a semantic view or
search service is a change to that object: propose it and its SQL, and let the user apply it.

## What it needs

- SQL access to the customer's Snowflake account with **OWNERSHIP or MODIFY** on the agent.
  Snowflake Cortex Code (CoCo) has this through its connection. Without SQL access, show the
  user the statements from step 5 and stop.
- `python3` to run `scripts/patch_agent_spec.py` (stdlib only), which ships with the toolkit
  plugin. Without the script, don't build the new spec yourself: give the user the merge patch
  from step 2 and stop.

## Rules

- **Never retype the specification.** `SET SPECIFICATION` replaces the whole spec, and any field
  left out is removed. Build the new spec with `scripts/patch_agent_spec.py` from the spec
  Snowflake returns, and pass the file it writes, unedited.
- **Paste files from a shell print, not a file-read tool.** Wherever a step says
  `<contents of …json>`, print the file with
  `python3 -c "import json,sys; print(json.dumps(json.load(open(sys.argv[1])), ensure_ascii=False))" <file>`
  and paste that one line. File-read tools can cut long lines, such as a tool description.
- **Never `CREATE OR REPLACE AGENT`.** It resets the agent to `VERSION$1` and drops its grants
  and history.
- **Committing can change production.** Unless `DEFAULT_VERSION` was set explicitly, the
  default is the latest committed version, so `COMMIT` alone makes the change live. Pin the
  default first when the user wants to test before releasing (step 5).
- **One live version at a time.** If `ADD LIVE VERSION` fails because one exists, someone may
  have uncommitted edits. A new agent also starts with one, holding its first version's spec.
  Run `SHOW VERSIONS` again and, in a query over `RESULT_SCAN(LAST_QUERY_ID())`, compare the
  live version's `agent_spec` with the default version's using `PARSE_JSON` equality. Only when
  it is TRUE, and the user agrees, set the spec on that live version instead of adding one.
  Otherwise stop and ask; never overwrite the edits.

## Steps

### 1. Read the current state

```sql
DESCRIBE AGENT <db>.<schema>.<agent>;
SHOW VERSIONS IN AGENT <db>.<schema>.<agent>;
```

Save the `agent_spec` column (JSON) to `current.json` exactly as returned. If it is NULL, the
agent is secure and the role can't read its spec: stop and say which role can. From
`SHOW VERSIONS`, note the versions and which one is the default.

Check that this session can change the agent, so a missing grant shows up now, not after the
user has picked how to apply:

```sql
SHOW GRANTS ON AGENT <db>.<schema>.<agent>;
SELECT IS_ROLE_IN_SESSION('<role>');  -- for each role holding OWNERSHIP or MODIFY
```

If none is in the session, say which roles can change the agent. Step 4 then has no choice to
offer: show the SQL and stop.

The patch script trusts `current.json`, so check the file against Snowflake before going on. A
slip in copying it, such as a lost escape in a long description, would otherwise reach the new
spec unnoticed:

```sql
DESCRIBE AGENT <db>.<schema>.<agent>;
SELECT PARSE_JSON("agent_spec") = PARSE_JSON($$<contents of current.json>$$) AS matches
FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()));
```

If `matches` isn't TRUE, write `current.json` again from the `DESCRIBE` output and recheck.
Never patch an unchecked file.

Check the issue's diagnosis against the spec (for example, "instructions holds only
`sample_questions`"). If the spec has moved on since the diagnosis, say so before proposing
anything.

### 2. Write the smallest patch

Write `fix.json` as a JSON Merge Patch (RFC 7396) holding only what the recommendation changes:
objects merge key by key, `null` deletes a key, and an array or string replaces the old value
whole. To add to an existing string, such as `instructions.orchestration`, put the existing text
and the new text together in the patch, so no rule is lost.

### 3. Build the new spec and show the difference

```bash
python3 <skill dir>/scripts/patch_agent_spec.py --spec current.json --patch fix.json --out new.json
```

The script prints every changed path with its before and after values. Show that report to the
user. If any path changed that the recommendation doesn't call for, stop and fix the patch.

### 4. Gate: ask how to apply

If step 1 found no role in the session that can change the agent, don't ask: print the SQL for
someone holding one of those roles to run, and stop.

Whoever runs that SQL doesn't have your files, so it must run as printed. Give the step 5
statements for **apply and release** in order: the spec as the one-line print of `new.json`,
never a placeholder; `SET DEFAULT_VERSION` to the version `SHOW VERSIONS` lists after the
commit, without guessing its number; the `matches` check; and the rollback to the current
default. Never offer to switch to a role the user hasn't said they have, and never grant
privileges unless the user asks.

Otherwise, offer three choices, and run nothing until the user picks one:

- **Apply and release:** commit the new version and make it the default.
- **Apply, keep the current default:** commit it, but keep the agent answering from the current
  version so the user can test first.
- **Show the SQL only:** print the SQL, complete as described above, and stop.

### 5. Apply

```sql
ALTER AGENT <agent> ADD LIVE VERSION FROM LAST
  COMMENT = 'Monte Carlo issue <issue uuid>: <issue title>';
ALTER AGENT <agent> MODIFY LIVE VERSION SET SPECIFICATION = $$<contents of new.json>$$;
```

If `new.json` contains `$$`, pass it as a single-quoted string with each `'` doubled instead.

For **keep the current default**, pin the default to the version it is now, from step 1, before
committing. Setting it again is harmless if it was already pinned. If step 1 didn't show which
version is the default, don't commit: give the user the SQL instead.

```sql
ALTER AGENT <agent> SET DEFAULT_VERSION = '<current default version>';
```

Then commit and read back the new version's name. Don't assume the next number:

```sql
ALTER AGENT <agent> COMMIT COMMENT = '<what the fix does>';
SHOW VERSIONS IN AGENT <agent>;
```

For **apply and release**, set the default to the new version, then confirm the agent now runs
exactly `new.json`, with the same check as step 1:

```sql
ALTER AGENT <agent> SET DEFAULT_VERSION = '<new version>';
DESCRIBE AGENT <agent>;
SELECT PARSE_JSON("agent_spec") = PARSE_JSON($$<contents of new.json>$$) AS matches
FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()));
```

If `matches` isn't TRUE, roll back and tell the user.

Tell the user the rollback: `ALTER AGENT <agent> SET DEFAULT_VERSION = '<previous default>';`.
For **keep the current default**, tell them how to release once they've tested:
`SET DEFAULT_VERSION = '<new version>'`.

### 6. Check it worked

If the issue names a question or conversation to rerun (often under "Unverified" or "Expected
effect"), offer to rerun it against the new version and compare the result with the diagnosis.
Then continue with the skill's "Record the fix" step.
