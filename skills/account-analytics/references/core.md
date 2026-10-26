<!-- Shared core of two twin skills: account-analytics (this repo) and Monte Carlo's internal
customer-account-analytics (monte-carlo-data/claude-skills). Both hold the same text: a change to how the skills work
belongs in both, so open the matching PR in the other repo. This file speaks of the docs and of requests only; each
SKILL.md says where the docs are and how a request runs. -->

# Account analytics: shared core

## The docs

The Composable dashboards docs hold every fact you use; this file holds only how to work. Read only the page you
need:

| Page | Read it for |
|---|---|
| How to query | the parts of a request, names, time, filters, access |
| Data catalog → Metrics (one page per topic: data quality, coverage, consumption, monitor runs) | the metrics, their rules and example questions |
| Data catalog → Dimensions, Glossary | what a dimension means; words with two meanings; periods and how far back a series goes |
| Dashboard examples | tested dashboards, each with its blocks and one request per block |
| Dashboard style | how any dashboard looks |

Use only metric and dimension names you read in the docs or in the list of metrics the SKILL.md gives you. A metric
marked as not served cannot be used: say so and offer what is served.

## A request

Every number comes from a request of this shape, whatever runs it:

```json
{"metrics": ["incident_count"], "group_by": ["metric_time__week"],
 "filters": [{"field": "metric_time__day", "op": "gte", "values": ["2026-07-22"]}],
 "order_by": [{"field": "incident_count", "descending": true}], "limit": 1000}
```

The answer has `columns` (group-by names, then metrics), `rows`, `data_as_of` and `truncated`. Read columns by name.
The docs describe requests in words; translate them like this:

| The docs say | Request |
|---|---|
| Metrics: `a`, `b` | `"metrics": ["a", "b"]` |
| Grouped by: `x`, `y` | `"group_by": ["x", "y"]` |
| Filter: `f` is `v`, or is one of `v`, `w` | `{"field": "f", "op": "in", "values": ["v", "w"]}` |
| Filter: `f` is not `v`, or is none of `v`, `w` | `{"field": "f", "op": "not_in", "values": ["v", "w"]}` |
| Filter: `f` on or after, or at least, `v` | `{"field": "f", "op": "gte", "values": ["v"]}` |
| Filter: `f` on or before, or at most, `v` | `{"field": "f", "op": "lte", "values": ["v"]}` |
| A date in words: "30 days ago", "the start of this quarter" | that date as `YYYY-MM-DD` |
| Sorted by: `m`, highest first (lowest first) | `"order_by": [{"field": "m", "descending": true}]` (`false`) |
| At most N rows | `"limit": N` (the default and the maximum are in How to query) |

`true` and `false` are JSON booleans; other values are strings. To list the values a dimension has (domain names,
monitor types), request a count grouped by that dimension, for example `monitor_count` grouped by
`monitor__monitor_type`.

## 1. Find the business question

A question is ready when it says four things. Fill each from the question, from the docs' defaults, or from the user:

1. **What to count**: a metric the docs have. Map the user's words with the glossary and the metrics' synonyms
   ("spend" is credits; "incident" is a declared incident; "health" is asset health, not the product's data quality
   score).
2. **Over what**: the whole account, or a grouping (domain, data product, asset tag, monitor tag, warehouse) and which
   members.
3. **When**: a window and a grain for series ("weekly, last 3 months"), or current state (coverage, monitor counts,
   asset health take no dates).
4. **The shape**: one number, a ranking, a trend, or a list of tables or monitors.

If all four are clear, or the docs give a default for the missing one (a default window, which meaning of a word is
the default), go to step 2 and name the defaults under "Choices I made"; never ask about what the docs settle.

If the question is vague ("how is our data quality?", "tell me about domain X", "is our monitoring good?"):

- Offer two or three precise questions the data answers, each one line, with what it would show, and recommend one.
  Keep the whole message short: the options, then one question.
  Take them from the topic's example questions when one fits. Example: "Asset health of your tables this week, per
  data quality dimension (which kind of check fails most)" / "Tables failing this week, worst first (where to look)" /
  "Weekly alerts over the last 3 months (is it getting better)".
- When the purpose is unclear, ask what the answer is for (a weekly review, a report to leadership, finding what to
  fix): the purpose picks the reading.
- Ask once, in one message. If the user says "just answer", answer only the recommended reading and state the
  choices; offer the others as follow-ups.
- Ask only when the purpose is unclear or the readings would answer different questions. When the question names what
  to count and only a detail is open (which window, which of two definitions, which of several close values), answer
  the recommended reading, say so under "Choices I made", and offer the others as follow-ups.
- Say early what the data cannot answer (history it does not keep, cost per table, predictions, other accounts) and
  offer the closest question it can. Lead with what it cannot answer; do not open with a substitute number nobody asked
  for.
- **A named value that does not exist** (a tag, domain, warehouse or data product the account does not have) is not a
  reason to stop. Check it by listing the values, say it does not exist, name the closest values the account has, and
  answer the rest of the question with the nearest reading: without that filter, or with the grouping it stands for
  (all monitor tags for "squad"). Ask only if no reading is close.

## 2. Build the request

- **Topic rules first.** Read the topic's page and apply its rules as written: default filters (deleted monitors,
  deleted data products), which meaning of "domain", credit pricing.
- **Groupings.** To split a metric by domain, data product, asset tag, monitor domain, monitor tag or audience, use its
  per-grouping metric (`domain_...`, `data_product_...`). Tags are `name: value`: group by both unless the user names
  the tag.
- **Entity rows.** For one row per table or monitor, group by `asset` or `monitor` and put its name next to it; never
  by the name alone (names repeat).
- **Time.** Today is the session's current date. "Last N days" is `metric_time__day` on or after today minus N days.
  Group a series by `metric_time__day`, `__week` or `__month`. A series goes back only as far as the data does: when
  it starts later than asked, say where it starts. Do not group current-state metrics by time.
- **Two groupings at once** that one metric does not allow: take two steps, as Dimensions → "Before you group or
  filter" shows.
- **A dashboard example matches the ask:** use its requests, adapting only the window and filters.

## 3. Run and check

- **Errors** list what works; fix the request and retry, at most three times per request.
- **`truncated` is true:** narrow the request or raise `limit`.
- **Empty answer:** check the filter values (list them as above). If the default window is empty, also give the most
  recent value or a wider window. "Nothing matched" is an answer.
- **Never add up rows.** A total, a headline number or an "all" row comes from its own request without the group by.
  Rows of domains, data products, tags, monitor domains and audiences overlap (a table can be in two domains, an alert
  can have two tags), and `limit` cuts rows, so their sum is not a count of anything. When you show members, say that
  they overlap and give the total from its own request next to them. This holds for the first sentence too: write a
  number there only after a request returned it.
- **Counts of things** (how many data products, domains, monitors, tables) come from a count metric such as
  `data_product_count` or `monitor_count`, never from counting rows by hand. This holds for the sentences around a
  dashboard too: a count of what the page lists is the length of its list, computed, not read.
- **Small samples:** say how many rows a median, percentile or rate rests on ("p90 over 2 fixed alerts").
- **Before you decline:** search the topic and dimension pages for the concept, and check the metric's allowed
  dimensions. One failed request or a missing name in your first guess is not proof the data lacks it.

## 4. Answer in the chat

Answer in the chat first; build a dashboard only when the user asks for one. In this order, in every turn that has
numbers (follow-ups too), never leaving out 3 and 4:

```text
<one to three sentences with the numbers>

<a table when there are several rows; at most 25, say how many more>

Data as of <data_as_of in UTC, e.g. 2026-10-22 09:00 UTC>.

Choices I made:
- <window, and the default it came from>
- <metric and its definition, when two could fit>
- <filters the rules added; how ties were broken>
```

Numbers as the docs' Dashboard style writes them: percentages with one decimal (`40.0%`, not `0.4`), counts with
thousands separators, hours with one decimal; an empty member as its own row, last: "Not classified" for monitors
without a data quality dimension (say once that the dimension is set on each monitor and these have none), "No
severity set" for alerts without one. If a number is computed from
returned rows (a share), say how under Choices. No labels the docs do not define
("Good", "Fair") and no scores they do not define (weighted, composite, "overall"): show the metrics and let the user
combine them. End with one or two follow-up questions the data can answer, worded so the user can send them as they
are.

Link each alert, monitor, table, domain or data product you name to its page in Monte Carlo (Dashboard style, Links to
Monte Carlo), only with a UUID or MCON a request returned.

## 5. Dashboards, when asked

Where it will be used decides the format. If the user has not said and the environment does not show it, do not ask:
build one self-contained HTML file that opens in any browser and can be sent by email, with nothing to install. Say in
one line that you can instead give the requests and the code for a tool they set up themselves (a Streamlit app, a
notebook, their BI tool), and what that means: it is theirs to run, and keeping it current (scheduling the requests,
storing the results, hosting the page) is their own data engineering; Monte Carlo does not host, refresh or maintain
it. A follow-up that does not name a format changes the same file. When the environment has its own way to show a
page (an artifact, a canvas), use it. A file is self-contained: inline CSS, charts drawn inside it (SVG, or a charting library pasted into
the file), no external scripts, fonts or images.

- **Start from the docs.** If a dashboard example matches, keep its blocks and requests. Lay out every dashboard as
  Dashboard style says: header with the window in dates and "Data as of", filters, the answer, the breakdown, the
  detail, and "How this was built" at the bottom in its four parts (source, definitions, choices, requests); its
  colours, number formats and status words.
- **Only what was asked.** Put on it the answers the user asked for in the chat, or the example's blocks; nothing
  extra. A grouping named in the request ("by domain") is the page's filter; a block listing its members is built only
  when the dashboard example's Layout has one.
- **One grouping per dashboard** (domains unless data products are asked for); never both side by side.
- **Why a table fails.** Next to a failing table, list its failing data quality dimensions. When some of its failing
  monitors have no data quality dimension, name their monitor types instead of leaving it empty ("accuracy,
  timeliness; not classified: table, comparison"): group the same monitor-by-table request by
  `monitor__monitor_type` as well. Do not use the internal incident type for this.
- **Every number** comes from a request listed under "How this was built"; a share of two returned numbers says so.
- **Values as returned.** Take every value from the rows as data (JSON), never retyped from wrapped or truncated tool
  output: names keep every character, a missing value is empty, never NaN or null on the page. When you can run code, generate
  the page's tables and chart data from the returned rows with a script instead of typing them, and round only once,
  on the page.
- **Every link to a list** opens the same items the block counts: it carries the block's window and filters, as Dashboard
  style, Links to Monte Carlo, says.
- **A block the data cannot fill** stays, with one sentence on why.
- **It is a snapshot:** say the numbers are as of the data refresh, and that running the request again refreshes them.
- **Check it before handing it over.** When you can run code, check that the page's scripts parse (`node --check` on
  them) and open it. Without a shell, keep the script small: the rows as JSON and one function that draws them.
- **Nothing is remembered.** Do not save the user's choices (format, filters) to memory files; the next request starts
  from these rules.
