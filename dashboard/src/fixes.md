---
title: What to fix
---

```js
import {APPS, APP_NAME, COMPLAINTS, fmt} from "./components/pulse.js";
const monthly = FileAttachment("data/monthly.json").json();
const reports = FileAttachment("data/reports.json").json();
```

# What to fix

<p class="lede">Which complaint, if it were halved, would lift each app's average review rating the most. From the monthly memo.</p>

```js
const MONTH_NAME = (m) => new Date(m + "-01T00:00:00").toLocaleDateString("en-IN", {month: "long", year: "numeric"});
const memos = reports.monthly.slice().reverse();
const memo = view(Inputs.select(memos, {label: "Memo", format: (m) => MONTH_NAME(m.month)}));
```

```js
const cur = monthly.themes.filter((d) => d.month === memo.month && COMPLAINTS.includes(d.theme));
const gainMax = Math.max(...cur.map((d) => d.gain));
function bars(app, width) {
  const rows = cur.filter((d) => d.app === app).sort((a, b) => b.gain - a.gain);
  const a = rows[0];
  return html`<div>
    <h3>${APP_NAME[app]}</h3>
    <p class="caption">Average review rating ${a.avg_rating.toFixed(2)}. Halving ${a.label} complaints: ${a.halved_avg_rating.toFixed(2)}.</p>
    ${Plot.plot({
      width,
      height: rows.length * 26 + 30,
      marginLeft: 150,
      marginRight: 48,
      style: {fontFamily: "var(--sans-serif)", fontSize: "13px", color: "var(--muted)"},
      x: {axis: null, domain: [0, gainMax]},
      y: {domain: rows.map((d) => d.theme), tickFormat: (t) => rows.find((d) => d.theme === t).label, label: null, tickSize: 0},
      marks: [
        Plot.barX(rows, {x: "gain", y: "theme", fill: `var(--app-${app})`, insetTop: 4, insetBottom: 4, rx: 2}),
        Plot.text(rows, {x: "gain", y: "theme", text: (d) => `+${d.gain.toFixed(2)}`, dx: 6, textAnchor: "start", fill: "var(--ink)"}),
        Plot.tip(rows, Plot.pointerY({x: "gain", y: "theme", title: (d) => `${d.label}: ${fmt("share", d.share)} of reviews, averaging ${d.theme_avg_rating?.toFixed(2)}★\nHalved: ${d.avg_rating.toFixed(2)} → ${d.halved_avg_rating.toFixed(2)}`}))
      ]
    })}
  </div>`;
}
```

<p>${memo.summary.replace(/ \d+ of \d+ of last month's predictions.*$/, "")}</p>

<p class="caption">Each bar is the estimated rise in the app's average review rating if reviews with that complaint were halved, ${MONTH_NAME(memo.month)}. It's an estimate from review stars: it assumes the removed complaints take their low ratings with them, and it says nothing about what a fix costs. Complaints overlap, so the bars don't add up.</p>

<div class="grid grid-cols-2">
  <div>${resize((width) => bars("blinkit", width))}</div>
  <div>${resize((width) => bars("zepto", width))}</div>
  <div>${resize((width) => bars("instamart", width))}</div>
  <div>${resize((width) => bars("bigbasket", width))}</div>
</div>

## Predictions for next month

<p class="caption">No-change predictions made by code: each app's average rating and its biggest complaint stay within the range of recent months. A miss means something changed and is worth a look.</p>

```js
const fmtRange = (p) => p.metric === "avg_rating" ? `${p.low.toFixed(2)}–${p.high.toFixed(2)}` : `${(100 * p.low).toFixed(1)}%–${(100 * p.high).toFixed(1)}%`;
const fmtMetric = (p) => p.metric === "avg_rating" ? "average rating" : `${cur.find((d) => d.theme === p.metric.slice(6))?.label ?? p.metric.slice(6)} share`;
```

```js
Inputs.table(memo.predictions, {
  columns: ["app", "metric", "low"],
  header: {app: "App", metric: "Metric", low: "Range for next month"},
  format: {app: (a) => APP_NAME[a], metric: (m, i, d) => fmtMetric(d[i]), low: (v, i, d) => fmtRange(d[i])},
  select: false
})
```

## How last month's predictions did

```js
memo.scorecard
  ? html`<p>${memo.scorecard.filter((r) => r.result === "right").length} of ${memo.scorecard.filter((r) => r.result !== "no data").length} right.</p>${Inputs.table(memo.scorecard, {select: false, header: {app: "App", prediction: "Prediction", actual: "Actual", result: "Result"}})}`
  : html`<p class="caption">This is the first memo, so there were no predictions to score.</p>`
```
