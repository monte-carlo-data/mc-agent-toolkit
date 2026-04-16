---
name: connection-auth-rules
description: "Build a Connection Auth Rules for a Monte Carlo connection type. Fetches live connector schemas and transform steps from the apollo-agent repo."
version: 1.0.0
---

# Connection Auth Rules Builder

Use this skill when the user wants to build a Connection Auth Rules (stored as `ctp_config`) for a Monte Carlo connection. The config is stored on the `Connection` object in the monolith and tells the Apollo agent how to transform flat credentials into the driver-specific `connect_args` format.

## When to activate this skill

Activate when the user:

- Asks to create, build, or generate a Connection Auth Rules
- Asks what fields are needed for a connection type's Connection Auth Rules
- Wants to customize credential transformation for a connection
- Asks about `MapperConfig`, `TransformStep`, or `CtpConfig`
- Says things like "help me write Connection Auth Rules for X", "what's the connection auth rules format for X"

## When NOT to activate this skill

Do not activate when the user is:

- Creating monitors (use the monitor-creation skill)
- Investigating data incidents (use the analyze-root-cause skill)
- Setting up a connection in the UI (this skill builds the JSON config, not UI flows)

---

## Step 1 — Fetch available connection types (Connection Auth Rules)

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

If the connector's default config (from Step 2) already includes steps, or if the user indicates they need custom transform steps, fetch the transforms directory listing:

```
https://api.github.com/repos/monte-carlo-data/apollo-agent/contents/apollo/integrations/ctp/transforms
```

For each `.py` file (excluding `__init__`), fetch the raw source using its `download_url`.

Parse each transform file's docstring for:
- `Step input:` — fields the step reads from the pipeline state
- `Step output:` — derived fields the step writes, which can then be referenced as `{{ derived.<key> }}` in the mapper
- `Step field_map:` — typical mapper entry to wire the step's output into `connect_args` (e.g. `{"private_key": "{{ derived.private_key_der }}"}`)

Present the available steps with their full contracts (input, output, and field_map hint).

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

If the connector needs steps (e.g. decoding a PEM certificate, constructing a derived field), help the user configure each step. A step dict has these fields:

| Field | Required | Description |
|-------|----------|-------------|
| `type` | yes | Step type name (e.g. `"load_private_key"`) |
| `input` | yes | Dict of template strings the step reads (e.g. `{"pem": "{{ raw.private_key_pem }}"}`) |
| `output` | yes | Dict mapping the step's logical output names to derived key names (e.g. `{"private_key": "private_key_der"}`) |
| `when` | no | Jinja2 boolean expression — step only runs if this evaluates to true (e.g. `"raw.ssl_ca_pem is defined"`) |
| `field_map` | no | Mapper entries contributed only when this step runs — useful for conditional fields |

Walk the user through `type`, `input`, and `output` for each step. Ask about `when` if the step should only run under certain credential conditions (e.g. when an optional SSL cert is present).

Steps run in order before the mapper. The mapper can reference step outputs via `{{ derived.<key> }}`.

---

## Step 6 — Output the final config

Produce the complete Connection Auth Rules as a Python dict (ready to serialize to JSON for storage). This is stored as `ctp_config` on the `Connection` model:

```python
{
    "steps": [
        # each step as a dict, e.g.:
        {
            "type": "load_private_key",
            "input": {
                "pem": "{{ raw.private_key_pem }}"
            },
            "output": {
                "private_key": "private_key_der"
            }
            # optional: "when": "raw.private_key_pem is defined"
        }
    ],
    "mapper": {
        "field_map": {
            "output_key": "{{ raw.credential_field }}",
            # step output referenced as: "private_key": "{{ derived.private_key_der }}"
            # ...
        }
    }
}
```

Also show the equivalent JSON, since this is what gets stored in the monolith's `Connection.ctp_config` field and entered in the "Connection auth rules" field in the UI.

Remind the user that validation happens server-side via `validateConnectionCtpConfig` — they should test the config through that mutation (or the Validate button in the UI) after saving it.

---

## Notes

- **No in-skill validation.** The skill helps construct the config but does not execute or validate it. The user validates via the monolith's `validateConnectionCtpConfig` GraphQL mutation or the Validate button in the "Connection auth rules" UI section.
- **`is not None` pattern.** An empty `field_map` (`{}`) is valid — do not treat it as missing. The monolith checks `ctp_config is not None`, not truthiness.
- **Steps are optional.** Most simple connectors use `steps: []`. Only add steps when the user needs credential transformation (e.g. PEM decoding, composite field construction).
- **Fetch failures are recoverable.** If the GitHub API fetch fails, tell the user exactly what failed and offer to retry. Do not silently fall back to guessed schemas.
- **Naming:** The user-facing name for this feature is "Connection auth rules". The underlying field and backend model remain `ctp_config` / `CtpConfig`.
