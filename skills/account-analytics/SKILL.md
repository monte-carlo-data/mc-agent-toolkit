---
name: monte-carlo-account-analytics
description: Answers questions about your Monte Carlo account (alerts, data quality, coverage, monitors, credits, monitor runs) from the metrics API, helps sharpen vague questions, and builds dashboards on request.
when_to_use: |
  The user asks for numbers, lists, trends or a dashboard about their own Monte Carlo account: "how many alerts did we get last week", "which tables have no monitor", "coverage per data product", "how many credits this quarter", "how is our data quality", "build a data quality dashboard". Not for investigating one alert (incident-response) or one table's health (asset-health).
bucket: Monitoring
---

# Account analytics

> **Draft.** The metrics API (`get_metrics_catalog`, `query_metrics`) and its docs are not released yet. Tool names
> and the docs links below are the planned ones.

Answer questions about the user's own Monte Carlo account from the metrics API. Every number comes from a request you
ran; never estimate, never fill a gap from memory. The API serves only the account the Monte Carlo MCP server is
connected to: never compare with, or answer for, other accounts.

> **Monte Carlo tool routing (required):** Always call Monte Carlo MCP tools through this plugin's
> bundled server, whose fully-qualified tool names are
> `mcp__plugin_mc-agent-toolkit_monte-carlo-mcp__<tool>` (e.g.
> `mcp__plugin_mc-agent-toolkit_monte-carlo-mcp__query_metrics`). Bare tool names used in this skill
> (`get_metrics_catalog`, `query_metrics`, `get_mc_webapp_url`) refer to that bundled server. If the session also has a
> separately-configured `monte-carlo-mcp` server, do **not** route to it — it may point at a
> different endpoint or credentials.

## Tools

- **`get_metrics_catalog`**: without arguments, every metric you can query (name, label, description); with
  `metrics`, the dimensions all of them can be grouped and filtered by.
- **`query_metrics`**: runs one request (`metrics`, `group_by`, `filters`, `order_by`, `limit`) and returns `columns`,
  `rows`, `data_as_of` and `truncated`. A request the data cannot answer is refused with the reason and what works.
- **`get_mc_webapp_url`**: the address of the user's Monte Carlo instance (such as `https://getmontecarlo.com` or
  `https://eu1.getmontecarlo.com`), for links to items. Call it once, before the first answer that names items.

## Docs

Composable dashboards, on the Monte Carlo docs:

- Overview: https://docs.getmontecarlo.com/docs/composable-dashboards
- How to query: https://docs.getmontecarlo.com/docs/composable-dashboards-querying
- Data catalog (Metrics, Dimensions, Glossary): https://docs.getmontecarlo.com/docs/composable-dashboards-data-catalog
- Dashboard examples: https://docs.getmontecarlo.com/docs/composable-dashboards-examples
- Dashboard style: https://docs.getmontecarlo.com/docs/composable-dashboards-style

Fetch only the page you need. When the docs cannot be reached, use `get_metrics_catalog` for names and descriptions,
and say that the topic rules could not be read.

## Workflow

Follow [references/core.md](references/core.md): find the business question, build the request, run and check, answer
in the chat, and build a dashboard only when asked. The core is shared with an internal twin of this skill; keep
anything specific to this skill here, not there.

Here a request runs as `query_metrics`; a request it refuses names what works. Use `get_metrics_catalog` to list
the metrics when the user asks what they can ask, and before you decline (core.md, section 3).
