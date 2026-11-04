---
name: monte-carlo-account-analytics
description: Answers questions about your Monte Carlo account (alerts, data quality, coverage, monitors, credits, monitor runs) from the Analytics API, helps sharpen vague questions, and builds dashboards on request.
when_to_use: |
  The user asks for numbers, lists, trends or a dashboard about their own Monte Carlo account: "how many alerts did we get last week", "which tables have no monitor", "which monitors are erroring and since when", "coverage per data product", "how many credits this quarter", "how is our data quality", "build a data quality dashboard". Not for investigating one alert (incident-response) or one table's health (asset-health).
bucket: Monitoring
---

# Account analytics

Answer questions about the user's own Monte Carlo account from the Analytics API. Every number comes from a request you
ran; never estimate, never fill a gap from memory. The API serves only the account the Monte Carlo MCP server is
connected to: never compare with, or answer for, other accounts.

> **Monte Carlo tool routing (required):** Always call Monte Carlo MCP tools through this plugin's
> bundled server, whose fully-qualified tool names are
> `mcp__plugin_mc-agent-toolkit_monte-carlo-mcp__<tool>` (e.g.
> `mcp__plugin_mc-agent-toolkit_monte-carlo-mcp__query_account_analytics`). Bare tool names used in this skill
> (`get_account_analytics_catalog`, `query_account_analytics`, `get_mc_webapp_url`) refer to that bundled server. If the session also has a
> separately-configured `monte-carlo-mcp` server, do **not** route to it — it may point at a
> different endpoint or credentials.

## Tools

- **`get_account_analytics_catalog`**: without arguments, every metric you can query (name, label, description); with
  `metrics`, the dimensions all of them can be grouped and filtered by; `search` keeps the items whose name, label or description contains a text.
- **`query_account_analytics`**: runs one request (`metrics`, `group_by`, `filters`, `order_by`, `limit`) and returns `columns`,
  `rows`, `data_as_of` and `truncated`. A request the data cannot answer is refused with the reason and what works.
- **`get_mc_webapp_url`**: the address of the user's Monte Carlo instance (such as `https://getmontecarlo.com` or
  `https://eu1.getmontecarlo.com`), for links to items. Call it once, before the first answer that names items.

If `get_account_analytics_catalog` or `query_account_analytics` is not in the session, or either returns a 404, the
Analytics API is not enabled for this account: say so and stop. Do not retry, and do not work the numbers out from
other tools (`get_alerts`, `get_monitors` and the like): they count differently and would not match the Analytics API.

## Docs

The Analytics API, on the Monte Carlo docs:

- Overview: https://docs.getmontecarlo.com/docs/analytics-api.md
- How to query: https://docs.getmontecarlo.com/docs/analytics-api-querying.md
- Data catalog (Metrics, Dimensions, Glossary): https://docs.getmontecarlo.com/docs/analytics-api-data-catalog.md
- Dashboard examples: https://docs.getmontecarlo.com/docs/analytics-api-dashboard-examples.md
- Dashboard style: https://docs.getmontecarlo.com/docs/analytics-api-dashboard-style.md

Fetch only the page you need, at its `.md` address: it returns the page as written, where the address without `.md`
can come back summarised. A page's links lead to more pages; add `.md` to them too. When the docs cannot be reached, use `get_account_analytics_catalog` for names and descriptions,
and say that the topic rules could not be read.

## Workflow

Follow [references/core.md](references/core.md): find the business question, build the request, run and check, answer
in the chat, and build a dashboard only when asked. The core is shared with an internal twin of this skill; keep
anything specific to this skill here, not there.

Here a request runs as `query_account_analytics`; a request it refuses names what works. Use `get_account_analytics_catalog` to list
the metrics when the user asks what they can ask, and before you decline (core.md, section 3).
