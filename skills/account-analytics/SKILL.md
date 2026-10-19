---
name: monte-carlo-account-analytics
description: Answers questions about the user's own Monte Carlo account (alerts, data quality, coverage, monitors, credits, monitor runs) and builds dashboards from them, using the Monte Carlo metrics API and its data catalog.
when_to_use: |
  The user asks for numbers, lists, trends or a dashboard about their Monte Carlo usage: "how many alerts did we get last week", "which tables have no monitor", "coverage per data product", "how many credits this quarter", "show my validation monitor results", "build a data quality dashboard". Not for investigating one alert (incident-response) or one table's health (asset-health).
bucket: Monitoring
---

# Account analytics

Answer from the metrics API only. Every number in an answer or a dashboard comes from a request you ran; never estimate,
never fill a gap from memory.

## Tools

- **Data catalog** (docs): `data-catalog` index first, then only the topic, object or dashboard page you need. Topic
  pages hold the rules for their metrics; follow them.
- **`get_metrics_catalog`**: metric names, or the dimensions every one of the given metrics can use.
- **`get_dimension_values`**: the values a dimension has in this account. Use it before filtering on a value you did
  not get from a previous answer (a domain name, a monitor type, a status).
- **`query_metrics`**: one request: `metrics`, `group_by`, `filters` (`in`, `not_in`, `gte`, `lte`), `order_by`,
  `limit`. The answer has `columns`, `rows`, `data_as_of` and `truncated`.

## Workflow

1. **Find the topic.** Read the catalog index, pick the topic (data quality, coverage, monitor runs, consumption) and
   read its page: rules, metrics, example requests. If the ask matches a dashboard example, read that page too: its
   requests are tested.
2. **Pick names from the catalog.** Use only metric and dimension names you read in the catalog or got from
   `get_metrics_catalog`. A metric marked as not served cannot be used: say so and offer what is served.
3. **Resolve time.** Today is the date the user is in. "Last N days" is `metric_time__day` `gte` today minus N days
   (N calendar days before today plus today). Use the topic's default window when none is given, and say which. Dates
   are `YYYY-MM-DD`. Respect the grain limits: daily series at most 7 days, weekly 3 months, monthly 13 full months.
   Current-state metrics (coverage, monitor counts, asset health) take no date.
4. **Apply the topic rules** as written: default filters (deleted monitors, deleted data products, credit pricing),
   which meaning of "domain", per-grouping metrics (`domain_`, `data_product_`, `monitor_tag_` ...), entity rows (group
   by `asset` or `monitor` with the name next to it, never by the name alone).
5. **Before you decline or ask back**, check that the data really lacks it: search the topic page and the object
   pages for the concept (a per-grouping or per-monitor metric, an object dimension), and ask `get_metrics_catalog`
   for the dimensions of the metric you would use. An error from one request is not proof; a missing name in your first
   guess is not proof. When the ask names something vague ("our main data product", "X"), answer for a reasonable
   reading you state (the largest, all of them) and offer the others, rather than only asking back.
6. **Words with two meanings.** When the glossary or a topic gives a word two meanings (alert vs declared incident,
   domain of a table vs domain of a monitor, severity vs priority), answer the meaning the rules name as default and
   give the other in one line, or both when they differ a lot.
7. **Run and check.** On an error, read the message (it lists what works), fix the request and retry, at most three
   times per request. If `truncated` is true, narrow the request or raise `limit`. An empty answer is an answer: say
   that nothing matched, after checking the filter values with `get_dimension_values`, and when the default window was
   empty give the most recent value or a wider window as well.
8. **Small samples.** A median, percentile or rate over a handful of rows is fragile: say how many it rests on ("p90
   over 2 fixed alerts").

## Answers

Reply with what was asked, in this order. Items 3 and 4 are never left out, also when the answer is "none":

1. **The answer** in one to three sentences, with the numbers.
2. **A table** when there are several rows (at most 25; say how many more there are).
3. **Data as of** `<data_as_of>`; the data is not real time. Do not estimate how far behind it is.
4. **Choices I made**: the window, the metric and its definition when two could fit (asset health vs the product's
   data quality score, time to fixed, domain of a table vs domain of a monitor), filters added by the rules, and how
   ties were broken. One line each.

Use this shape, also when you write the answer from a script:

```text
<one to three sentences with the numbers>

<table, when there are several rows>

Data as of <data_as_of from the answer>; the data is not real time.

Choices I made:
- <window>
- <metric and definition, when two could fit>
- <filters added by the rules, ties>
```

Every number you give comes from a request you list; if you computed it from returned rows (a share), say how in
Choices. A total comes from its own request without the group by, never from adding rows: an alert can have two alert
types, a table can be in two domains, and `limit` can cut rows.

Say plainly what the data cannot answer (history it does not keep, cost per table, predictions, other accounts) and
offer the closest thing it can. Do not add labels the catalog does not define (such as "Good" or "Fair" for a score):
show the number. Do not build scores the catalog does not define (weighted, composite, "overall"): offer the
metrics it has and let the user combine them.

## Dashboards

When the user asks for a dashboard, build one self-contained HTML file as described in
[references/dashboard.md](references/dashboard.md). Start from the dashboard example page when one matches; keep its
tiles and requests, and adapt windows and filters to the ask.
