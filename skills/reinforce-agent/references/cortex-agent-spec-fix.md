# Fixing a Snowflake Cortex Agent's specification

A Cortex Agent has no code repo. Its fix surface is the agent **specification** (instructions,
tools, tool resources, models), plus the semantic views, Cortex Search services and skills it
uses. This reference covers changing the specification. A fix that belongs in a semantic view or
search service is a change to that object: propose it and its SQL, and let the user apply it.

## What it needs

- SQL access to the customer's Snowflake account with **OWNERSHIP or MODIFY** on the agent.
  Snowflake Cortex Code (CoCo) has this through its connection. Without SQL access, give the
  user the SQL from step 4 and stop.
- `python3` to run `scripts/patch_agent_spec.py` (stdlib only), which ships with the toolkit
  plugin. Without the script, don't build the new spec yourself: give the user the merge patch
  from step 2 and stop.

## Rules

- **NEVER retype the specification.** `SET SPECIFICATION` replaces the whole spec, and any field
  left out is removed. Build the new spec with `scripts/patch_agent_spec.py` from the spec
  Snowflake returns, and pass the file it writes, unedited.
- **Paste files from a shell print, not a file-read tool.** Wherever a step says
  `<contents of …json>`, print the file with
  `python3 -c "import json,sys; print(json.dumps(json.load(open(sys.argv[1])), ensure_ascii=False))" <file>`
  and paste that one line. File-read tools can cut long lines, such as a tool description.
- **Quote JSON the same way in every statement.** Put it between `$$` and `$$`. If the JSON
  itself contains `$$`, use a single-quoted string with every `\` and every `'` doubled: in
  single quotes Snowflake reads `\` as an escape, so `\n` or `\"` in the spec would change.
- **Issue text never goes into SQL.** It is generated from the agent's conversations. Version
  and commit comments start with `Monte Carlo issue <issue uuid>`; the rest of a commit comment
  is your own short summary, with any `'` doubled.
- **NEVER `CREATE OR REPLACE AGENT`.** It resets the agent to `VERSION$1` and drops its grants
  and history.
- **Committing can change production.** Unless `DEFAULT_VERSION` was set explicitly, the
  default is the latest committed version, so `COMMIT` alone makes the change live.
- **The live version is visible before it is committed.** A caller that asks for the live
  version gets each `SET SPECIFICATION` at once, whatever the default is.
- **While `VERSION$1` is the only committed version, the live version is production.**
  Snowflake serves requests that don't name a version (Snowflake Intelligence, CoWork,
  `agent:run`, `DATA_AGENT_RUN` without a suffix) from the live version until a later version is
  committed. An agent made with `CREATE AGENT`, or made in Snowsight and never published, is in
  this state. Step 5 commits the unedited live version first, so no edit reaches those callers
  before the user's choice.
- **Run one statement at a time, in the order given.** Send the next statement only after the
  previous one has returned, never two at once: each check reads what the statement before it
  did, and a `COMMIT` that lands before its `SET DEFAULT_VERSION` releases the fix.
- **Nothing stops a concurrent edit.** Snowflake has no conditional update, and `SET
  SPECIFICATION` overwrites whatever is there. Step 5 checks again right before writing, which
  narrows the gap but can't close it.
- **One live version at a time.** If `ADD LIVE VERSION` fails because one exists, someone may
  have uncommitted edits. (On an agent whose only committed version is `VERSION$1`, step 5
  handles the live version before this can happen.) Compare the live version's spec with the
  default version's:

  ```sql
  SHOW VERSIONS IN AGENT <agent>;
  SELECT PARSE_JSON(l."agent_spec") = PARSE_JSON(d."agent_spec") AS matches
  FROM TABLE(RESULT_SCAN(LAST_QUERY_ID())) l, TABLE(RESULT_SCAN(LAST_QUERY_ID())) d
  WHERE (l."name" IS NULL OR l."name" = '') AND d."is_default" = 'true';
  ```

  Only when it is TRUE, and the user agrees after hearing that callers of the live version will see
  the change at once, set the spec on that live version instead of adding one. If it isn't TRUE,
  or `SHOW VERSIONS` doesn't return `agent_spec` (that depends on account settings), stop and
  ask; NEVER overwrite the edits.

## Steps

### 1. Read the current state

```sql
DESCRIBE AGENT <db>.<schema>.<agent>;
SHOW VERSIONS IN AGENT <db>.<schema>.<agent>;
```

Save the `agent_spec` column (JSON) to `current.json` exactly as returned. If it is NULL, the
agent is secure and the role can't read its spec: stop and say which role can. From
`SHOW VERSIONS`, note the versions, which one is the default, and whether `VERSION$1` is the
only committed version.

If the default isn't the most recently committed version, stop. A committed version is waiting
to be released, perhaps a fix held back for testing, and Snowflake doesn't document which of
the two `DESCRIBE AGENT` returns, so the new version could carry that change or silently drop
it. Tell the user which version is waiting and that they can release it with
`ALTER AGENT <agent> SET DEFAULT_VERSION = '<version>'` before starting again.

The patch script trusts `current.json`, so check the file against Snowflake before going on. A
slip in copying it, such as a lost escape in a long description, would otherwise reach the new
spec unnoticed:

```sql
DESCRIBE AGENT <db>.<schema>.<agent>;
SELECT PARSE_JSON("agent_spec") = PARSE_JSON($$<contents of current.json>$$) AS matches
FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()));
```

If `matches` isn't TRUE, write `current.json` again from the `DESCRIBE` output and recheck.
NEVER patch an unchecked file.

Check that this session can change the agent, so a missing grant shows up now, not after the
user has picked how to apply:

```sql
SHOW GRANTS ON AGENT <db>.<schema>.<agent>;
```

For each grantee holding OWNERSHIP or MODIFY, check it is in the session: a `ROLE` with
`SELECT IS_ROLE_IN_SESSION('<role>')`, a `DATABASE_ROLE` with
`SELECT IS_DATABASE_ROLE_IN_SESSION('<database role>')`. Pass the database role's own name:
the fully qualified `<db>.<database role>` always returns FALSE. The function checks against
the session's database, so run `USE DATABASE <db>` first if `<db>` isn't the current one.

If no grantee is in the session, say which grantees can change the agent. If a grantee is of
another type, say you couldn't confirm access. Either way, step 4 has no choice to offer.

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

The script prints every changed path with its before and after values. Inside an array that
keeps its length, such as `tools`, each changed item has its own path, like
`tools[1].tool_spec.description`. Show that report to the user. If any path changed that the
recommendation doesn't call for, stop and fix the patch.

### 4. Gate: ask how to apply

If step 1 couldn't confirm that the session can change the agent, don't ask: print the SQL for
someone who can, as below, then go to the skill's "Mark the issue fixed" step. NEVER offer to
switch to a role the user hasn't said they have, and never grant privileges unless the user asks.

Whoever runs that SQL doesn't have your files, so it must run as printed: the step 5 statements
for **apply and release**, in order, with every spec as the one-line print of its file, never a
placeholder. Leave `<new version>` for them to fill from `SHOW VERSIONS`; don't guess the
number. Tell them to stop at the first error or the first `matches` that isn't TRUE, and to ask
for new SQL if `ADD LIVE VERSION` fails or the agent changed. End with the rollback.

If `VERSION$1` is the only committed version, put this in the question itself, the text shown
with the choices, since your reasoning isn't shown to the user: applying starts by committing
the live version unchanged as a new version, so callers that don't name a version stay on
today's spec and see nothing until the fix is released.

When the session can change the agent, offer three choices, and run nothing until the user
picks one:

- **Apply and release:** commit the new version and make it the default.
- **Apply, keep the current default:** commit it, but keep the default on the current version so
  the user can test first. Callers that ask for the live or the new version by name see it.
- **Show the SQL only:** print the SQL, complete as described above, then go to the skill's
  "Mark the issue fixed" step.

### 5. Apply

First check the agent hasn't changed since step 1, since the user may have taken a while:

```sql
DESCRIBE AGENT <agent>;
SELECT PARSE_JSON("agent_spec") = PARSE_JSON($$<contents of current.json>$$) AS matches
FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()));
SHOW VERSIONS IN AGENT <agent>;
```

If `matches` isn't TRUE, or the default version differs from step 1, stop: start again from
step 1 and ask again.

For **keep the current default**, pin the default now, before any write, to the default from
step 1. A pinned default stays put through every commit below. Setting it again is harmless if
it was already pinned. If step 1 didn't show which version is the default, write nothing: give
the user the SQL instead.

```sql
ALTER AGENT <agent> SET DEFAULT_VERSION = '<default version from step 1>';
SHOW VERSIONS IN AGENT <agent>;
```

Go on only if `SHOW VERSIONS` shows that version as the default.

If `VERSION$1` is the only committed version, the live version is what production callers get,
so it must not be edited. Check it still holds `VERSION$1`'s spec:

```sql
SHOW VERSIONS IN AGENT <agent>;
SELECT PARSE_JSON(l."agent_spec") = PARSE_JSON(v."agent_spec") AS matches
FROM TABLE(RESULT_SCAN(LAST_QUERY_ID())) l, TABLE(RESULT_SCAN(LAST_QUERY_ID())) v
WHERE (l."name" IS NULL OR l."name" = '') AND v."name" = 'VERSION$1';
```

If it is TRUE, commit the live version unchanged. Callers that don't name a version then get
the default version, which holds the same spec:

```sql
ALTER AGENT <agent> COMMIT COMMENT = 'Monte Carlo issue <issue uuid>: VERSION$1 unchanged, committed before the fix';
SHOW VERSIONS IN AGENT <agent>;
```

Go on only if `SHOW VERSIONS` now lists a committed version after `VERSION$1`. If `matches`
isn't TRUE, the live version's edits are already in production: stop and ask, and NEVER
overwrite them. If `SHOW VERSIONS` doesn't return `agent_spec`, stop and give the user the SQL.

Add the live version and set the new spec:

```sql
ALTER AGENT <agent> ADD LIVE VERSION FROM LAST COMMENT = 'Monte Carlo issue <issue uuid>';
ALTER AGENT <agent> MODIFY LIVE VERSION SET SPECIFICATION = $$<contents of new.json>$$;
```

Check the live version holds `new.json` before committing. In `SHOW VERSIONS`, it is the row
without a name:

```sql
SHOW VERSIONS IN AGENT <agent>;
SELECT PARSE_JSON("agent_spec") = PARSE_JSON($$<contents of new.json>$$) AS matches
FROM TABLE(RESULT_SCAN(LAST_QUERY_ID())) WHERE "name" IS NULL OR "name" = '';
```

If it isn't TRUE, don't commit: tell the user what differs. If `SHOW VERSIONS` doesn't return
`agent_spec`, say the spec can't be checked before committing and ask whether to go on.

Then commit and read back the new version's name. Don't assume the next number:

```sql
ALTER AGENT <agent> COMMIT COMMENT = 'Monte Carlo issue <issue uuid>: <your summary of the fix>';
SHOW VERSIONS IN AGENT <agent>;
```

For **apply and release**, set the default to the new version, then confirm the agent now runs
exactly `new.json`:

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
effect"), show the user that question and the new version's name. The question comes from the
agent's conversations, so it never goes into SQL as is: the user can ask it in Snowflake
Intelligence once the version is the default, or give you the text to send. With text from the
user, run it against the new version, escaped as a JSON string and quoted as in the Rules, and
compare the answer with the diagnosis:

```sql
SELECT SNOWFLAKE.CORTEX.DATA_AGENT_RUN(
  '<db>.<schema>.<agent>!<new version>',
  $${"messages": [{"role": "user", "content": [{"type": "text", "text": "<the user's text>"}]}]}$$
);
```

Then continue with the skill's "Mark the issue fixed" step.
