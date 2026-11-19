# Decorator placement

Tier 3 reference for the `instrument-agent` skill. Single concern: which decorator goes where, and how to propose placements safely.

## 1. CRITICAL — never apply edits without user approval

> **CRITICAL — Never modify the customer's source files without explicit per-file user approval.** The skill **proposes** decorator diffs; the customer accepts or rejects them. Apply each diff one file at a time, wait for `yes` per file. This rule mirrors `SKILL.md` and applies to every decorator placement.

**IMPORTANT:** "Apply all" is not a substitute for per-file confirmation. If the customer says "looks good, apply all of them," confirm explicitly: *"I'll apply these N diffs now — confirm?"* Wait for `yes` before doing anything.

## 2. The two decorators in scope

Only two decorators are in scope for v1. Anything else is out of scope (see section 3).

### `@mc.trace_with_workflow(span_name, workflow_name)` — orchestration / entry functions

A function counts as **orchestration** when:

- It coordinates a sequence of operations across one or more LLM calls, tool calls, or task functions.
- It's the entry point of a logical agent flow (e.g., a LangGraph graph node or API handler that calls downstream functions).
- It's a router or controller function that decides which downstream functions to call.

Every instrumented agent should have a workflow decorator on the top-level entry or enclosing function, even when the flow contains only one LLM-calling task.

Examples:

- A `chat_agent(message)` function that coordinates retrieval + LLM call + tool dispatch.
- A `run_agent(message)` function that validates input, calls one LLM task function, and returns the response.
- A LangGraph node function that runs `should_continue → call_model → validate`.
- A planner function that loops over an LLM until success.

### `@mc.trace_with_task(span_name, task_name)` — LLM-calling task functions

A function counts as a **task** when:

- It makes an LLM API call (directly or via the AI library: `ChatOpenAI(...).invoke(...)`, `Anthropic().messages.create(...)`, `bedrock.invoke_model(...)`, etc.).
- It performs a discrete unit of work that's interesting to evaluate (e.g., regex generation, summary, classification).

Examples:

- A `summarize(text)` function that calls an LLM with a summarization prompt.
- A `extract_entities(doc)` function that calls an LLM and parses structured output.
- A `book_flight()` function that calls an LLM to choose flight options.

### Why workflow vs task matters

Tasks are nested within workflows. Both labels propagate down the trace tree, so spans automatically inherit the workflow attribute when called from a workflow-decorated function.

Workflow + task are used at **evaluation time** to filter and differentiate parts of the agent — e.g., *"show me all `chat` task spans inside the `customer-support` workflow."* Without these labels, the trace tree is just a span hierarchy with no semantic meaning to MC's evaluation pipeline.

## 3. Only the two decorators above

> **CRITICAL — `@trace_with_workflow` and `@trace_with_task` are the only decorators this skill proposes.** Tasks-nested-in-workflows is the entire decorator surface for v1; that pair already provides the filtering and propagation surface MC's evaluation pipeline needs.

If the customer asks about other SDK tracing primitives, redirect them to the live SDK docs on PyPI / GitHub for manual usage — but the skill does not scaffold them.

## 4. Placement guidance

Walk the customer's source files (after they've approved which files to inspect — the skill is read-only on source until a diff is approved). For each candidate function:

1. **Identify the entry point.** What's the top-level function the user calls to run the agent? That's the workflow candidate and should always be proposed.
2. **Identify the LLM call sites.** Functions that call `OpenAI().chat.completions.create(...)`, `Anthropic().messages.create(...)`, `LangchainInstrumentor`-instrumented chains, etc. Those are task candidates.
3. **Identify intermediate orchestration nodes.** Multi-step functions between the entry and the LLM call sites are additional workflow candidates only when they represent a distinct logical agent flow.
4. **Match `workflow_name` to a meaningful concept.** Use the customer's domain language: `"customer-support"`, `"travel-planner"`, `"regex-bootstrap"`, etc. Not technical names like `"main"` or `"agent"`.
5. **Match `task_name` to the LLM call's purpose.** `"summarize"`, `"classify"`, `"plan-flight"`, `"create_regex"`. Not `"call_llm"`.

**IMPORTANT — Always propose both decorator types.** Aim for 1 workflow on the agent entry / enclosing function + 1 task per LLM call. Decorating every helper function adds span noise without semantic value, but producing only task spans or only workflow spans leaves the trace without the required workflow/task pairing.

## 5. The canonical placement example

A typical task placement looks like:

```python
@mc.trace_with_task(
    span_name="call_first_model",
    task_name="create_regex",
)
def call_first_model(state, config, logger: Logger):
    # ... function body that invokes the LLM
```

Notice:

- Task name should describe the call's purpose. The function name is fine when it's meaningful and distinct (e.g. `summarize`, `extract_entities`); generic names like `call_llm` are too opaque.
- `span_name` is fine to use the function name for.

The orchestration function that drives the graph (a few levels up the call stack) gets a workflow-level decorator instead. Use this pattern when proposing diffs.

## 6. Conservative defaults — both decorators, few placements

For the first pass, propose decorators on:

- The single highest-level entry function for the logical agent flow → `@trace_with_workflow`.
- The LLM-calling function(s) inside that flow → `@trace_with_task`.

Show these as diffs. Both decorator types should be present in the proposal before asking about additional helper functions or sub-orchestrators. **Don't propose 20 decorators on a first pass.**

## 7. Diff format for proposals

Show each placement as a unified diff so the customer sees the exact line where the decorator lands and the import that needs to be added (if not already present):

```
--- src/agent.py
+++ src/agent.py
@@ -1,3 +1,5 @@
+import montecarlo_opentelemetry as mc
+
 def chat_agent(message: str) -> str:
     ...
@@ -10,2 +12,6 @@
+@mc.trace_with_workflow(
+    span_name="chat_agent",
+    workflow_name="customer-support",
+)
 def chat_agent(message: str) -> str:
```

Wait for `yes` before applying. If the customer says "looks good, apply all of them" — confirm explicitly: *"I'll apply these N diffs now — confirm?"* before doing anything.

## Common mistakes

- **Scaffolding any decorator other than `@trace_with_workflow` or `@trace_with_task`** — those are the only two in scope for v1. Other SDK tracing primitives are not part of the surface this skill proposes.
- **Producing task-only or workflow-only traces** — always propose both `@trace_with_workflow` and `@trace_with_task`. Place `@trace_with_workflow` on the function that calls the LLM-calling function, and `@trace_with_task` on the LLM-calling function itself.
- **Decorating every helper function** — span noise. Aim for 1 workflow on the agent entry / enclosing function + 1 task per LLM call.
- **Using `task_name="call_llm"` or `workflow_name="main"`** — opaque. Match the customer's domain.
- **Applying diffs without explicit per-file confirmation** — violates `SKILL.md` guardrail.
- **Skipping the workflow decorator because the flow has only one LLM call** — wrong. The enclosing function is still the workflow boundary.
- **Treating "apply all" as blanket approval** — always re-confirm before bulk-applying multiple diffs.
- **Inferring `workflow_name` / `task_name` from a generic or non-descriptive function name** — match the domain purpose, not opaque names like `main` or `agent`. A meaningful, distinct function name (`summarize`, `extract_entities`) is fine to reuse.
