---
name: ctp-config
description: "Build a CTP (Credential Transform Pipeline) config for a Monte Carlo connection type. Fetches live connector schemas and transform steps from the apollo-agent repo."
version: 1.0.0
---

# CTP Config Builder

Use this skill when the user wants to build a `ctp_config` dict for a Monte Carlo connection. The config is stored on the `Connection` object in the monolith and tells the Apollo agent how to transform flat credentials into the driver-specific `connect_args` format.

## When to activate this skill

Activate when the user:

- Asks to create, build, or generate a `ctp_config`
- Asks what fields are needed for a connection type's CTP config
- Wants to customize credential transformation for a connection
- Asks about `MapperConfig`, `TransformStep`, or `CtpConfig`
- Says things like "help me write a CTP config", "what's the ctp_config format for X"

## When NOT to activate this skill

Do not activate when the user is:

- Creating monitors (use the monitor-creation skill)
- Investigating data incidents (use the analyze-root-cause skill)
- Setting up a connection in the UI (this skill builds the JSON config, not UI flows)

---

## Step 1 — Fetch available connection types

Use `WebFetch` to load the directory listing from the apollo-agent GitHub API:

```
https://api.github.com/repos/monte-carlo-data/apollo-agent/contents/apollo/integrations/ctp/defaults
```

Parse the response. Each entry with `"type": "file"` and a `.py` extension is a connector. Extract the `name` (filename) and `download_url` for each.

**If this fetch fails:** Tell the user the fetch failed and show the error. Offer to retry. Do not proceed until you have the connector list.

Present the list of available connection types (strip the `.py` extension and `__init__` entry). Ask the user which connection type they want to build a config for.

---

## Step 2 — Fetch the connector schema

Once the user selects a connection type, fetch the raw Python source for that connector using its `download_url` from Step 1.

Parse the file to extract:

1. **`TypedDict` output shape** — the class that defines the output keys. These are the keys the mapper will produce (the `connect_args` fields the driver expects).
2. **`MapperConfig` `field_map`** — the existing default mapping. This shows which credential fields map to which output keys and what Jinja2 template expressions are used.
3. **`CtpConfig` `steps`** — any default transform steps already configured.

Present a summary to the user:

- The output keys (from the TypedDict)
- The default mapper field_map entries
- Any existing steps with their types

---

## Step 3 — Optionally fetch available transform steps

If the user indicates they need custom transform steps (or asks what steps are available), fetch the transforms directory listing:

```
https://api.github.com/repos/monte-carlo-data/apollo-agent/contents/apollo/integrations/ctp/transforms
```

For each `.py` file (excluding `__init__`), fetch the raw source using its `download_url`.

Parse each transform file's docstring or comments for the `Step input:` / `Step output:` contract — these document what fields the step reads from `derived` context and what it adds.

Present the available steps and their input/output contracts.

**If this fetch fails:** Tell the user and offer to retry. You can continue without step data — just describe steps as unknown and ask the user to specify them manually.

---

## Step 4 — Build the mapper

Walk the user through each output key in the TypedDict:

1. Show the default template from the connector's `MapperConfig` (if one exists).
2. Ask if they want to keep the default or customize it.
3. For custom values, help the user write a Jinja2 template expression.

### Jinja2 template help

The template context has two namespaces:

- **`raw`** — the flat credential dict as received. Use `{{ raw.field_name }}` to reference a credential field directly. Example: `{{ raw.client_id }}`
- **`derived`** — fields added by transform steps. Use `{{ derived.field_name }}` to reference a step's output. Example: `{{ derived.private_key_pem }}`

Common patterns:
- Simple field reference: `"{{ raw.username }}"`
- Conditional/default: `"{{ raw.port | default('1433') }}"`
- Concatenation: `"{{ raw.host }}:{{ raw.port }}"`

When the user doesn't know their credential field names, remind them these come from the Data Collector's credential dict — the keys are whatever the DC sends for that connection type.

---

## Step 5 — Configure transform steps (optional)

If the connector needs steps (e.g. decoding a PEM certificate, constructing a derived field), help the user configure each step:

1. Ask which step type they need (from the transforms listing, or let them specify a type name).
2. Ask for the step's parameters (each step type has its own param set — refer to the parsed source or docstring).
3. Build the step dict.

Steps run in order before the mapper. The mapper can reference step outputs via `{{ derived.<key> }}`.

---

## Step 6 — Output the final config

Produce the complete `ctp_config` as a Python dict (ready to serialize to JSON for storage):

```python
{
    "steps": [
        # each step as a dict, e.g.:
        {
            "type": "load_private_key",
            "params": {
                "source_field": "private_key",
                "target_field": "private_key_pem"
            }
        }
    ],
    "field_map": {
        "output_key": "{{ raw.credential_field }}",
        # ...
    }
}
```

Also show the equivalent JSON, since this is what gets stored in the monolith's `Connection.ctp_config` field.

Remind the user that validation happens server-side via `validateConnectionCtpConfig` — they should test the config through that mutation after saving it.

---

## Notes

- **No in-skill validation.** The skill helps construct the config but does not execute or validate it. The user validates via the monolith's `validateConnectionCtpConfig` GraphQL mutation.
- **`is not None` pattern.** An empty `field_map` (`{}`) is valid — do not treat it as missing. The monolith checks `ctp_config is not None`, not truthiness.
- **Steps are optional.** Most simple connectors use `steps: []`. Only add steps when the user needs credential transformation (e.g. PEM decoding, composite field construction).
- **Fetch failures are recoverable.** If the GitHub API fetch fails, tell the user exactly what failed and offer to retry. Do not silently fall back to guessed schemas.
