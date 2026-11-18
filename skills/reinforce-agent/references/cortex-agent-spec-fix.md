# Fixing a Snowflake Cortex Agent's specification

A Cortex Agent has no code repo. Its fix surface is the agent **specification** (instructions,
tools, tool resources, models), plus the semantic views, Cortex Search services and skills it
uses. This reference covers changing the specification. A fix that belongs in a semantic view or
search service is a change to that object: propose it and its SQL, and let the user apply it.

## What it needs

- SQL access to the customer's Snowflake account with **OWNERSHIP or MODIFY** on the agent.
  Snowflake Cortex Code (CoCo) has this through its connection. Without SQL access, show the
  user the change to make in words, then go to the skill's "Mark the issue fixed" step: the SQL
  from step 4 needs the spec and versions that only step 1's reads return.
- `python3` to run `scripts/patch_agent_spec.py` (stdlib only), which ships with the toolkit
  plugin. Without the script, don't build the new spec yourself: give the user the merge patch
  from step 2, then go to the skill's "Mark the issue fixed" step.

## Rules

- **Every exit that hands the user SQL or a patch goes on to the skill's "Mark the issue fixed"
  step**, which offers to mark the issue in progress, so Monte Carlo shows someone is on it.
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
  is your own short summary, with every `\` and every `'` doubled, as for single-quoted JSON.
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
- **A check reads only its own `SHOW`.** `RESULT_SCAN(LAST_QUERY_ID())` reads the statement just
  before it in the same session. If a check returns no rows or an error, run its `SHOW` and the
  check again, once. If it still does, treat the check as not TRUE. NEVER take no rows as TRUE.
- **Nothing stops a concurrent edit.** Snowflake has no conditional update, and `SET
  SPECIFICATION` overwrites whatever is there. Step 5 checks again right before writing, which
  narrows the gap but can't close it.
- **One live version at a time.** If `ADD LIVE VERSION` fails because one exists, someone may
  have uncommitted edits. (On an agent whose only committed version is `VERSION$1`, step 5
  handles the live version before this can happen.) Compare the live version's spec with the
  default version's:

  ```sql
  SHOW VERSIONS IN AGENT <db>.<schema>.<agent>;
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

Name the agent in full, `<db>.<schema>.<agent>`, in every statement in this reference. A bare name
resolves against the session's current database and schema, which `USE DATABASE` below can
change, so it could act on another agent of the same name.

```sql
DESCRIBE AGENT <db>.<schema>.<agent>;
SHOW VERSIONS IN AGENT <db>.<schema>.<agent>;
```

Save the `agent_spec` of the default version's row in `SHOW VERSIONS` (`is_default` is true) to
`current.json` exactly as returned. Don't take it from `DESCRIBE AGENT`: on an agent with no live
version, `DESCRIBE` can return an empty `agent_spec`. Two cases stop the run here:

- `SHOW VERSIONS` doesn't return `agent_spec` (that depends on account settings): the checks
  below can't run. Say so, and show the user the change to make in words, never a merge patch: a
  patch that adds to a string or an array has to repeat its existing value, and there is no
  checked copy of it. Then go to the skill's "Mark the issue fixed" step.
- The spec is NULL or empty: the agent may be secure, which hides its spec from roles other than
  its owner. Say so, and name the owner from `DESCRIBE AGENT`.

Otherwise keep a snapshot of step 1 for the checks below. From `SHOW VERSIONS`: the versions
with their comments, which one is the default (the name of the `is_default` row, never `LAST`:
this is "the default version from step 1" below), whether `VERSION$1` is the only committed
version, and whether there is a live version (the row without a name). From `DESCRIBE AGENT`:
`default_version_name`. `LAST` means no default was set, so callers get whichever version was
committed last.

The patch script trusts `current.json`, so check the file against Snowflake before going on. A
slip in copying it, such as a lost escape in a long description, would otherwise reach the new
spec unnoticed:

```sql
SHOW VERSIONS IN AGENT <db>.<schema>.<agent>;
SELECT PARSE_JSON("agent_spec") = PARSE_JSON($$<contents of current.json>$$) AS matches
FROM TABLE(RESULT_SCAN(LAST_QUERY_ID())) WHERE "is_default" = 'true';
```

If `matches` isn't TRUE, write `current.json` again from that row and recheck.
NEVER patch an unchecked file.

Check that this session can change the agent, so a missing grant shows up now, not after the
user has picked what to do:

```sql
SHOW GRANTS ON AGENT <db>.<schema>.<agent>;
```

For each grantee holding OWNERSHIP or MODIFY, check it is in the session: a `ROLE` with
`SELECT IS_ROLE_IN_SESSION('<role>')`, a `DATABASE_ROLE` with
`SELECT IS_DATABASE_ROLE_IN_SESSION('<database role>')`. Pass the database role's own name:
the fully qualified `<db>.<database role>` always returns FALSE. The function checks against
the session's database, so run `USE DATABASE <db>` first if `<db>` isn't the current one.

If no grantee is in the session, say which grantees can change the agent. If a grantee is of
another type, say you couldn't confirm access. Either way, nothing below runs a write: the
choices below and in step 4 hand the user SQL instead.

If the default isn't the most recently committed version, a committed version is waiting to be
released, perhaps a fix held back for testing. Step 5 replaces the whole spec with one built
from the default's, so the new version would silently leave that change out. Write nothing yet.
List each committed version newer than the default with its comment from `SHOW VERSIONS`, and
show what it changes. For each one, save its `agent_spec` from `SHOW VERSIONS` to `waiting.json`
exactly as returned, and check it as `current.json` was checked:

```sql
SHOW VERSIONS IN AGENT <db>.<schema>.<agent>;
SELECT PARSE_JSON("agent_spec") = PARSE_JSON($$<contents of waiting.json>$$) AS matches
FROM TABLE(RESULT_SCAN(LAST_QUERY_ID())) WHERE "name" = '<version>';
```

If `matches` isn't TRUE, write `waiting.json` again from that row and recheck. Then:

```bash
python3 <skill dir>/scripts/patch_agent_spec.py --spec current.json --compare waiting.json
```

Show the user that report. Without the script, say you couldn't show the difference. A version
this skill committed may be one a run rolled back because its check failed, not a fix held back
for testing: the report shows what it would release. Ask the user what it is, and offer three
choices:

- **Release it**: `ALTER AGENT <db>.<schema>.<agent> SET DEFAULT_VERSION = '<version>';`
- **Drop it**: `ALTER AGENT <db>.<schema>.<agent> DROP VERSION <version>;` for each waiting
  version, newest first, with the name unquoted. A dropped version can't be restored. If the
  drop leaves `VERSION$1` as the only committed version, callers that don't name a version go
  back to the live version, which may hold a spec nobody checked. If there is no live version,
  what Snowflake serves them hasn't been confirmed.
- **Stop** while they keep testing it.

Run the chosen statement only if the session can change the agent. Otherwise give the user the
SQL and stop: ask them to tell you once it has run, then start again from step 1. If Snowflake
refuses a release or a drop, stop and show the user the error. After a release or a drop you
ran, start again from step 1.

A version commented `Monte Carlo issue <uuid>: VERSION$1 unchanged, committed before the fix`
is meant to be a copy of `VERSION$1`. Check that it is before saying anything about it:

```sql
SHOW VERSIONS IN AGENT <db>.<schema>.<agent>;
SELECT PARSE_JSON(c."agent_spec") = PARSE_JSON(v."agent_spec") AS matches
FROM TABLE(RESULT_SCAN(LAST_QUERY_ID())) c, TABLE(RESULT_SCAN(LAST_QUERY_ID())) v
WHERE c."name" = '<that version>' AND v."name" = 'VERSION$1';
```

If it is TRUE, releasing it changes nothing callers get, so suggest releasing it. Don't call a
drop harmless: see the Drop choice above.

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

Whoever runs that SQL doesn't have your files or step 1's results, so it must run as printed:

- Start with the step 1 snapshot: the versions, the default row and `default_version_name`. The
  recheck stops when the agent differs from it.
- Then the step 5 statements for **apply and release**, in order, with every spec as the
  one-line print of its file, never a placeholder. Leave `<new version>` for them to fill from
  `SHOW VERSIONS`; don't guess the number.
- If step 1 found a live version on an agent with a committed version after `VERSION$1`, run
  the comparison in "One live version at a time" now. If it isn't TRUE, print no writes: say the
  live version holds edits, and stop. If it is TRUE, print that comparison again right before
  `MODIFY LIVE VERSION`, in place of the `ADD LIVE VERSION`: they go on only if it returns TRUE,
  and callers that ask for the live version see the change at once.
- Tell them to stop at the first error or the first `matches` that isn't TRUE, and to ask for
  new SQL if `ADD LIVE VERSION` fails or the agent differs from the snapshot.
- Tell them a `COMMIT` error may still have landed: if `SHOW VERSIONS` then lists a named version
  with the fix's comment that wasn't in the `SHOW VERSIONS` just before the fix's `COMMIT`, it
  landed, so they go on with the checks.
- After the rest, print what to run if they stop after the `MODIFY` that sets `new.json` and
  before the fix's `COMMIT` lands: the check that the live version holds `new.json`, then the
  put-back from "When the run stops", only if that check returns TRUE.
- End with the rollback, naming the default version from step 1. If they stop after the fix's
  `COMMIT` lands and before the release check returns TRUE, they check in `SHOW VERSIONS` which
  version is the default, and run the rollback only if it is the fix's version.

If `VERSION$1` is the only committed version, put this in the question itself, the text shown
with the choices, since your reasoning isn't shown to the user: applying starts by committing
the live version unchanged as a new version, so callers that don't name a version stay on
today's spec and see nothing until the fix is released.

When the session can change the agent, offer three choices, and run nothing until the user
picks one:

- **Apply and release:** commit the new version and make it the default.
- **Apply, keep the current default:** commit it, but keep the default on the current version so
  the user can test first. Callers that ask for the new version by name see it.
- **Show the SQL only:** print the SQL, complete as described above, then go to the skill's
  "Mark the issue fixed" step.

### 5. Apply

Follow the parts below in order, skipping a part only where it says so. A failed recheck starts
again from step 1. Whatever else stops the run in this step, go to "When the run stops" at the
end of it.

#### Recheck

First check the agent hasn't changed since step 1, since the user may have taken a while:

```sql
DESCRIBE AGENT <db>.<schema>.<agent>;
SHOW VERSIONS IN AGENT <db>.<schema>.<agent>;
SELECT PARSE_JSON("agent_spec") = PARSE_JSON($$<contents of current.json>$$) AS matches
FROM TABLE(RESULT_SCAN(LAST_QUERY_ID())) WHERE "is_default" = 'true';
```

If `matches` isn't TRUE, or the versions, the default row or `default_version_name` differ from
step 1, stop: start again from step 1 and ask again.

#### Only if `VERSION$1` is the only committed version: check the live version

Skip this part on any other agent. Here the live version is what production callers get, so it
must not be edited. If `SHOW VERSIONS` lists no live version (no row without a name), such as
after a later version was dropped, skip the check: there are no live edits to keep. Otherwise
check the live version still holds `VERSION$1`'s spec:

```sql
SHOW VERSIONS IN AGENT <db>.<schema>.<agent>;
SELECT PARSE_JSON(l."agent_spec") = PARSE_JSON(v."agent_spec") AS matches
FROM TABLE(RESULT_SCAN(LAST_QUERY_ID())) l, TABLE(RESULT_SCAN(LAST_QUERY_ID())) v
WHERE (l."name" IS NULL OR l."name" = '') AND v."name" = 'VERSION$1';
```

If `matches` isn't TRUE, the live version's edits are already in production: stop and ask, and
NEVER overwrite them. Nothing has been written yet.

#### Only for keep the current default: pin the default

Skip this part for **apply and release**. Pin the default now, before any write, to the default
version from step 1. A pinned default stays put through every commit below. Setting it again is
harmless if it was already pinned.

```sql
ALTER AGENT <db>.<schema>.<agent> SET DEFAULT_VERSION = '<default version from step 1>';
SHOW VERSIONS IN AGENT <db>.<schema>.<agent>;
```

Go on only if `SHOW VERSIONS` shows that version as the default.

#### Only if `VERSION$1` is the only committed version: commit it unchanged

Skip this part on any other agent, and go to "Set the new spec". Callers that don't name a
version then get the default version, which holds the same spec. Only when `SHOW VERSIONS`
listed no live version, add one first. It copies `VERSION$1`, so callers see no change:

```sql
ALTER AGENT <db>.<schema>.<agent> ADD LIVE VERSION FROM LAST;
```

Then commit it:

```sql
ALTER AGENT <db>.<schema>.<agent> COMMIT COMMENT = 'Monte Carlo issue <issue uuid>: VERSION$1 unchanged, committed before the fix';
SHOW VERSIONS IN AGENT <db>.<schema>.<agent>;
```

Go on only if `SHOW VERSIONS` now lists a version after `VERSION$1` with that comment.

#### Set the new spec

Add the live version and set the new spec. If `ADD LIVE VERSION` fails because a live version
exists, follow "One live version at a time" in the Rules:

```sql
ALTER AGENT <db>.<schema>.<agent> ADD LIVE VERSION FROM LAST COMMENT = 'Monte Carlo issue <issue uuid>';
ALTER AGENT <db>.<schema>.<agent> MODIFY LIVE VERSION SET SPECIFICATION = $$<contents of new.json>$$;
```

From this `MODIFY` until the fix's `COMMIT` lands, the live version holds an uncommitted spec,
which callers that ask for the live version get, and which blocks the next run's
`ADD LIVE VERSION`. Check it holds `new.json`. In `SHOW VERSIONS`, it is the row without a name:

```sql
SHOW VERSIONS IN AGENT <db>.<schema>.<agent>;
SELECT PARSE_JSON("agent_spec") = PARSE_JSON($$<contents of new.json>$$) AS matches
FROM TABLE(RESULT_SCAN(LAST_QUERY_ID())) WHERE "name" IS NULL OR "name" = '';
```

If it isn't TRUE, don't commit: tell the user what differs, and stop.

#### Commit the fix

Keep the version list from the `SHOW VERSIONS` just above. Then commit and read back the new
version's name. Don't assume the next number:

```sql
ALTER AGENT <db>.<schema>.<agent> COMMIT COMMENT = 'Monte Carlo issue <issue uuid>: <your summary of the fix>';
SHOW VERSIONS IN AGENT <db>.<schema>.<agent>;
```

A `COMMIT` that returns an error, such as a timeout, may still have landed. Compare this
`SHOW VERSIONS` with the list you kept. A new named version with this commit's comment means it
landed, whatever the error said: go on with that version. No new named version means it didn't
land: stop. Anything else, including a `SHOW VERSIONS` that fails, means you don't know: stop,
write nothing more, and say so.

Whatever the default, check the new version holds `new.json`. Under a `LAST` default with
nothing pinned (**apply and release** on an agent whose default was never set), the fix is
already what callers get, since the `COMMIT` landed:

```sql
SHOW VERSIONS IN AGENT <db>.<schema>.<agent>;
SELECT PARSE_JSON("agent_spec") = PARSE_JSON($$<contents of new.json>$$) AS matches
FROM TABLE(RESULT_SCAN(LAST_QUERY_ID())) WHERE "name" = '<new version>';
```

If it isn't TRUE, stop, and give the user no release statement.

#### Only for apply and release: release it

Skip this part for **keep the current default**. Set the default to the new version, then
confirm the agent now runs exactly `new.json`. If step 1's `default_version_name` was `LAST`, use
`'LAST'` in place of `'<new version>'`: the new version is the latest commit, and the default
goes back to following the latest commit, as before.

```sql
ALTER AGENT <db>.<schema>.<agent> SET DEFAULT_VERSION = '<new version>';
SHOW VERSIONS IN AGENT <db>.<schema>.<agent>;
SELECT PARSE_JSON("agent_spec") = PARSE_JSON($$<contents of new.json>$$) AS matches
FROM TABLE(RESULT_SCAN(LAST_QUERY_ID())) WHERE "is_default" = 'true';
```

If `matches` isn't TRUE, stop.

#### Tell the user

Give the user the new version's name, and the rollback:
`ALTER AGENT <db>.<schema>.<agent> SET DEFAULT_VERSION = '<default version from step 1>';`. It
names a version, never `LAST`: once the fix is committed, `LAST` is the fix. Say it pins the
default, so a later commit won't reach callers until the default is set again.

For **keep the current default**, callers that ask for the new version by name see it. Tell the
user how to release once they've tested:
`ALTER AGENT <db>.<schema>.<agent> SET DEFAULT_VERSION = '<new version>';`, or `= 'LAST'` if step
1's `default_version_name` was `LAST` and nothing was committed since, which also unpins it.
Snowflake reuses a dropped version's name, so tell them to check first that `SHOW VERSIONS` still
lists that version with the fix's comment.

Then go on to step 6.

#### When the run stops

Recover first, then report, then end the run. Writes in this part are the only ones allowed
after a stop.

**1. Recover**, as far as the run got:

- **Before the `MODIFY` that sets `new.json`:** nothing to recover.
- **After that `MODIFY`, and the fix's `COMMIT` didn't land:** run the check that the live version
  holds `new.json` again now, even if it ran before. Only if it is TRUE does the live version
  still hold this run's spec: put the current spec back, and check it.

  ```sql
  ALTER AGENT <db>.<schema>.<agent> MODIFY LIVE VERSION SET SPECIFICATION = $$<contents of current.json>$$;
  SHOW VERSIONS IN AGENT <db>.<schema>.<agent>;
  SELECT PARSE_JSON("agent_spec") = PARSE_JSON($$<contents of current.json>$$) AS matches
  FROM TABLE(RESULT_SCAN(LAST_QUERY_ID())) WHERE "name" IS NULL OR "name" = '';
  ```

  If either check isn't TRUE, write nothing more: someone else may be editing the live version.
- **After the fix's `COMMIT` landed:** read the default now, with `DESCRIBE AGENT` and
  `SHOW VERSIONS`. If the default is the new version and the release check hasn't returned TRUE,
  run the rollback from "Tell the user", then check the default holds `current.json`, as in the
  recheck. If the release check returned TRUE, the fix is released: nothing to recover.
- **You don't know whether the fix's `COMMIT` landed:** read `SHOW VERSIONS` again now and compare
  it with the list you kept before the commit. A new named version with the fix's comment means
  it landed, and no new named version means it didn't: recover as in the branch above that
  applies. Only if `SHOW VERSIONS` still fails, write nothing more.

**2. Report** what the agent holds after recovery, from `DESCRIBE AGENT` and `SHOW VERSIONS` read
now, not from what you meant to do:

- which version callers that don't name one get, and whether the default is pinned or `LAST`;
- which versions this run committed (the unchanged copy counts), and whether the fix is one;
- if the fix's version failed its check, how its spec differs from `new.json`, or that it
  couldn't be read;
- what the live version holds, if there is one.

If the fix's version is committed but isn't the default, say a later run will list it as waiting
to be released, and that they can drop it. If you don't know whether the fix's `COMMIT` landed,
give them the version list from just before it: a new version there with the fix's comment means
it landed. Give them the rollback for if that version is the default.

**3. Restoring `LAST`.** Only if the pin landed, step 1's `default_version_name` was `LAST`, and
the fix's `COMMIT` didn't land, tell the user the default is pinned and give them the statement
that restores it. The latest commit is then the step 1 default or the unchanged copy, both
holding the current spec. Quote `LAST`: unquoted, it is a syntax error. Afterwards
`DESCRIBE AGENT` shows `default_version_name` as `LAST` again:

```sql
ALTER AGENT <db>.<schema>.<agent> SET DEFAULT_VERSION = 'LAST';
```

If the fix's `COMMIT` landed, or may have, NEVER offer that statement: setting the default to
`'LAST'` would release the fix. Report the default as `DESCRIBE AGENT` shows it now, or as
unknown if it can't be read.

**4. End the run:** skip step 6, "Check it worked", and don't mark the issue fixed.

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
