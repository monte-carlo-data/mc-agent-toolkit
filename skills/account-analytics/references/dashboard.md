# Dashboard output

One self-contained HTML file: inline CSS and inline SVG charts, no external scripts, fonts or images, so it opens
offline and in the product.

## Layout

1. **Header**: dashboard title, the account name, the window ("Last 7 days, 2026-10-12 to 2026-10-19"), and
   "Data as of <data_as_of>; not real time".
2. **KPI row**: one card per headline number: the value, its label from the catalog, and a one-line definition.
3. **Charts**: one per series. Bar charts for categories (sorted, largest first unless the tile says otherwise), line
   charts for time. Every chart has an axis title with its unit ("Asset health, %", "Alerts", "Hours"). Empty and unassigned values shown as "Unassigned", never
   dropped.
4. **Tables**: the detail rows (entity name, then the numbers), at most 50 rows each, sorted as the tile says.
5. **How this was built**: every request you ran (JSON), and the "Choices I made" list from the answer rules.

## Rules

- Every number on the page comes from a request in "How this was built". Do not compute a number the API did not return,
  except a share of two returned numbers; say so in its definition. Totals come from their own request without the
  group by, never from adding rows: rows of per-grouping metrics overlap, and rows can be cut by `limit`.
- A grouping (domain, data product, tag) shows only its members, and only those with data: when the ask is about
  everything, add a tile without the grouping, or a note on what is outside every member, and say how many members
  have no value ("9 data products have no result this week").
- A tile the data cannot fill (history it does not keep, a metric not served) stays on the page with one sentence on
  why, instead of being invented or silently removed.
- Percentages with one decimal; counts with thousands separators; durations in hours with one decimal.
- No qualitative labels or colours for "good" and "bad" unless the catalog defines the cut-offs.
- Neutral look: white background, one accent colour, system font stack.
