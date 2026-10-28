---
title: This week
---

```js
import {APPS, APP_NAME, COMPLAINTS, fmt, fmtDelta, weekSpan, rangeChart, verdictMark} from "./components/pulse.js";
const reports = FileAttachment("data/reports.json").json();
const weekly = FileAttachment("data/weekly.json").json();
const quotes = FileAttachment("data/quotes.json").json();
```

```js
// Plain words for the headline; the tables keep the short theme names.
const SAID = {
  delivery_delay: "late or failed deliveries",
  missing_wrong_item: "missing or wrong items",
  quality_expiry: "spoiled or expired products",
  refund_support: "refunds and customer support",
  pricing_fees: "prices and fees",
  app_payment_bug: "app and payment bugs",
  partner_behaviour: "delivery partners' behaviour",
  availability_stock: "items or service being unavailable",
  other: "vague complaints"
};
const latest = reports.weekly.at(-1);
const top = latest.actions[0];
const times = (r) => (r >= 1.9 && r < 2.15 ? "twice" : r >= 2.85 && r < 3.2 ? "three times" : null);

function headline(a) {
  if (!a) return "A normal week. Nothing moved outside its expected range in the wrong direction.";
  const app = APP_NAME[a.app];
  if (a.metric.startsWith("theme:")) {
    const theme = a.metric.slice(6);
    const t = times(a.value / a.base_mean);
    return `${fmt("share", a.value)} of ${app}'s reviews were about ${SAID[theme] ?? theme}, ${t ? `${t} its normal ${fmt("share", a.base_mean)}` : `against a normal ${fmt("share", a.base_mean)}`}.`;
  }
  if (a.metric.startsWith("version:")) return `${app} version ${a.version} drew ${fmt("share", a.value)} ${a.metric.endsWith("app_payment_bug") ? "bug" : "complaint"} reviews, against ${fmt("share", a.base_mean)} normally.`;
  return `${app}'s ${a.metric === "avg_rating" ? "average rating" : "1★ share"} is ${fmt(a.kind, a.value)}, against a normal ${fmt(a.kind, a.base_mean)}.`;
}
```

<p class="hero">${headline(top)}</p>

<p class="hero-sub">From ${latest.reviews.toLocaleString("en-US")} Google Play reviews of four quick-commerce apps in the week of ${weekSpan(latest.week)}. ${top ? `${top.owner}: ${top.todo}.` : ""}</p>

```js
const group = quotes.groups[0];
const MON = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
```

```js
group ? html`<h2>In their words</h2>
<p class="caption">${group.reviews.length} of the ${group.matching} reviews this week that the classifier filed under ${group.label} for ${APP_NAME[group.app]}, picked at random. The classifier makes mistakes (it agrees with hand labels at macro-F1 0.59), so the odd one may be misfiled.</p>
<ul class="quotes">${group.reviews.map((r) => html`<li><q>${r.text}</q><span class="stars">${r.rating}★, ${+r.review_date.slice(8, 10)} ${MON[+r.review_date.slice(5, 7) - 1]}</span></li>`)}</ul>` : html``
```

```js
const focus = top && !top.metric.startsWith("version:")
  ? weekly.rows.filter((d) => d.app === top.app && d.metric === top.metric)
  : null;
```

```js
focus ? html`<h2>How unusual this is</h2>
<p class="caption">${APP_NAME[top.app]}'s ${focus[0].label} share each week. The shaded band is the expected range: the previous ${weekly.baseline_weeks} weeks' average ± ${weekly.k} standard deviations. Filled dots are weeks outside it.</p>
${resize((width) => rangeChart(focus, {width, kind: top.kind, color: `var(--app-${top.app})`}))}` : html``
```

## What to do this week

${latest.actions.length ? html`<ol class="actions">${latest.actions.map((a) => html`<li><span class="owner">${a.owner}</span><span>${APP_NAME[a.app]}: ${a.todo}.<span class="why">${a.metric.startsWith("version:") ? `Version ${a.version}: ${fmt("share", a.value)} against ${fmt("share", a.base_mean)} normally.` : `${fmt(a.kind, a.value)} against a normal ${fmt(a.kind, a.base_mean)}; expected ${fmt(a.kind, a.expected_low)}–${fmt(a.kind, a.expected_high)}. Success: back inside that range within 2 weeks.`}</span></span></li>`)}</ol>` : html`<p>No actions. Nothing is outside its expected range in the wrong direction, and no app version is drawing unusual complaints.</p>`}

## Every metric, every app

<p class="caption">Each line is a metric's weekly distance from its own normal, in standard deviations, over the last 16 weeks. Inside the band (± ${weekly.k}) is ordinary noise. A red dot moved the bad way, a blue dot the good way. The number is this week's value.</p>

```js
const BOARD = ["avg_rating", "pct_1star", "reviews", ...COMPLAINTS.map((t) => `theme:${t}`), "theme:positive"];
const weeks = [...new Set(weekly.rows.filter((d) => d.scored).map((d) => d.week))].sort().slice(-16);
const shownApps = width < 700 ? [boardApp] : APPS;
```

```js
const boardApp = width < 700 ? view(Inputs.radio(APPS, {value: "bigbasket", format: (a) => APP_NAME[a], label: "App"})) : null;
```

```js
function board(width) {
  const rows = weekly.rows.filter((d) => d.scored && weeks.includes(d.week) && BOARD.includes(d.metric) && shownApps.includes(d.app));
  const last = rows.filter((d) => d.week === weeks.at(-1));
  const label = Object.fromEntries(rows.map((d) => [d.metric, d.label]));
  const clamp = (z) => Math.max(-7, Math.min(7, z));
  const x = (d) => weeks.indexOf(d.week);
  return Plot.plot({
    width,
    height: BOARD.length * 46 + 40,
    marginLeft: 150,
    marginRight: 8,
    marginTop: 28,
    style: {fontFamily: "var(--sans-serif)", fontSize: "13px", color: "var(--muted)"},
    fx: {domain: shownApps, tickFormat: (a) => APP_NAME[a], label: null, axis: "top", padding: 0.12},
    fy: {domain: BOARD, tickFormat: (m) => label[m], label: null, padding: 0.18},
    x: {axis: null, domain: [0, weeks.length + 3.5]},
    y: {axis: null, domain: [-7, 7]},
    marks: [
      Plot.rect(shownApps.flatMap((a) => BOARD.map((m) => ({app: a, metric: m}))), {fx: "app", fy: "metric", x1: 0, x2: weeks.length - 1, y1: -weekly.k, y2: weekly.k, fill: "var(--band)"}),
      Plot.ruleY([0], {stroke: "var(--grid)"}),
      Plot.lineY(rows, {fx: "app", fy: "metric", x, y: (d) => clamp(d.z), stroke: "var(--ink-2)", strokeWidth: 1.5, curve: "monotone-x"}),
      Plot.dot(rows.filter((d) => d.is_alert), {fx: "app", fy: "metric", x, y: (d) => clamp(d.z), r: 4, stroke: "var(--page)", strokeWidth: 2,
        fill: (d) => (d.verdict === "worse" ? "var(--worse)" : d.verdict === "better" ? "var(--better)" : "var(--ink)")}),
      Plot.text(last, {fx: "app", fy: "metric", x: weeks.length - 1, y: 0, text: (d) => fmt(d.kind, d.value), dx: 8, textAnchor: "start", fill: "var(--ink)", fontSize: 13}),
      Plot.tip(rows, Plot.pointer({fx: "app", fy: "metric", x, y: (d) => clamp(d.z),
        title: (d) => `${APP_NAME[d.app]}, ${d.label}\nWeek of ${weekSpan(d.week)}: ${fmt(d.kind, d.value)}\nNormal ${fmt(d.kind, d.base_mean)}, expected ${fmt(d.kind, d.expected_low)}–${fmt(d.kind, d.expected_high)}\n${d.z >= 0 ? "+" : "−"}${Math.abs(d.z).toFixed(1)} SD`}))
    ]
  });
}
```

<figure>${resize((width) => board(width))}</figure>

<details><summary>Show this week's numbers as a table</summary>

```js
Inputs.table(weekly.rows.filter((d) => d.week === weeks.at(-1) && BOARD.includes(d.metric)), {
  columns: ["app", "label", "value", "base_mean", "expected_low", "expected_high", "z", "verdict"],
  header: {app: "App", label: "Metric", value: "This week", base_mean: "Normal", expected_low: "Expected from", expected_high: "to", z: "SD from normal", verdict: "Verdict"},
  format: {app: (a) => APP_NAME[a], value: (v, i, d) => fmt(d[i].kind, v), base_mean: (v, i, d) => fmt(d[i].kind, v),
    expected_low: (v, i, d) => fmt(d[i].kind, v), expected_high: (v, i, d) => fmt(d[i].kind, v), z: (z) => z?.toFixed(1), verdict: (v) => v ?? "inside range"},
  rows: 14, select: false
})
```

</details>

## Last week's actions

${latest.followup == null ? html`<p class="caption">No report for the week before, so nothing to follow up.</p>` : latest.followup.length === 0 ? html`<p>Last week's report had no actions to follow up.</p>` : Inputs.table(latest.followup, {select: false})}

## The summary, as the AI wrote it

<p>${latest.summary}</p>
<p class="caption">Written by a small language model running in the weekly job, from facts computed by code. Every sentence is checked: each number must belong to the app named in it, and "inside" or "outside the range" must match the data. If it fails twice, code writes the summary instead. This week: ${latest.summary_source}.</p>
