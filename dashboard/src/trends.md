---
title: Trends
---

```js
import {APPS, APP_NAME, COMPLAINTS, fmt, weekSpan, rangeChart} from "./components/pulse.js";
const weekly = FileAttachment("data/weekly.json").json();
```

# Trends

<p class="lede">Pick a metric to see it week by week for all four apps, against the range each app's own recent weeks would predict.</p>

```js
const METRICS = ["avg_rating", "pct_1star", "reviews", ...COMPLAINTS.map((t) => `theme:${t}`), "theme:positive", "theme:other"];
const labels = Object.fromEntries(weekly.rows.map((d) => [d.metric, d.label]));
const metric = view(Inputs.select(METRICS, {label: "Metric", value: "theme:refund_support", format: (m) => labels[m]}));
```

```js
const rows = weekly.rows.filter((d) => d.metric === metric);
const kind = rows[0].kind;
const latestWeek = rows.map((d) => d.week).sort().at(-1);
// One shared scale so the panels compare directly, except review counts (Blinkit gets ~7× the others).
const lo = Math.min(...rows.map((d) => Math.min(d.value, d.expected_low ?? Infinity)));
const hi = Math.max(...rows.map((d) => Math.max(d.value, d.expected_high ?? -Infinity)));
const yDomain = kind === "count" ? undefined : [kind === "share" ? 0 : lo, hi];

function panel(app, width) {
  const r = rows.filter((d) => d.app === app);
  const now = r.find((d) => d.week === latestWeek);
  return html`<div>
    <h3>${APP_NAME[app]}</h3>
    <p class="caption">${now ? `${fmt(kind, now.value)} in the week of ${weekSpan(now.week)}` : ""}</p>
    ${rangeChart(r, {width, height: 200, kind, color: `var(--app-${app})`, yDomain})}
  </div>`;
}
```

<p class="caption">Each panel: the weekly ${labels[metric]} (line), the expected range from the previous ${weekly.baseline_weeks} weeks (shaded), and weeks outside it (red worse, blue better). ${kind === "count" ? "Each panel has its own scale: Blinkit gets about seven times the reviews of the others." : "All four panels share one scale."}</p>

<div class="grid grid-cols-2">
  <div>${resize((width) => panel("blinkit", width))}</div>
  <div>${resize((width) => panel("zepto", width))}</div>
  <div>${resize((width) => panel("instamart", width))}</div>
  <div>${resize((width) => panel("bigbasket", width))}</div>
</div>

<details><summary>Show the numbers as a table</summary>

```js
Inputs.table(rows.filter((d) => d.scored).slice().sort((a, b) => b.week.localeCompare(a.week)), {
  columns: ["week", "app", "value", "base_mean", "expected_low", "expected_high", "verdict", "denom"],
  header: {week: "Week of", app: "App", value: labels[metric], base_mean: "Normal", expected_low: "Expected from", expected_high: "to", verdict: "Verdict", denom: "Reviews"},
  format: {app: (a) => APP_NAME[a], value: (v) => fmt(kind, v), base_mean: (v) => fmt(kind, v), expected_low: (v) => fmt(kind, v),
    expected_high: (v) => fmt(kind, v), verdict: (v) => v ?? "inside range", denom: (n) => n.toLocaleString("en-US")},
  rows: 16, select: false
})
```

</details>

<p class="caption">The first ${weekly.baseline_weeks} weeks have no shaded range: they are the baseline. Weeks with fewer than ${weekly.min_n} reviews are never flagged.</p>
