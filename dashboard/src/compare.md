---
title: Compare apps
---

```js
import {APPS, APP_NAME, COMPLAINTS, appColor, appKey, fmt, weekSpan} from "./components/pulse.js";
const monthly = FileAttachment("data/monthly.json").json();
const weekly = FileAttachment("data/weekly.json").json();
```

# Compare apps

<p class="lede">Where each app is ahead or behind its rivals, complaint by complaint, for a whole month of reviews.</p>

```js
const MONTH_NAME = (m) => new Date(m + "-01T00:00:00").toLocaleDateString("en-IN", {month: "long", year: "numeric"});
const months = [...new Set(monthly.apps.map((d) => d.month))].sort();
const month = view(Inputs.select(months.slice().reverse(), {label: "Month", format: MONTH_NAME}));
```

```js
const cur = monthly.themes.filter((d) => d.month === month && COMPLAINTS.includes(d.theme));
const order = COMPLAINTS.slice().sort((a, b) =>
  Math.max(...cur.filter((d) => d.theme === b).map((d) => d.share)) - Math.max(...cur.filter((d) => d.theme === a).map((d) => d.share)));
const worst = order.map((t) => cur.filter((d) => d.theme === t).sort((a, b) => b.share - a.share)[0]);
const labelOf = Object.fromEntries(cur.map((d) => [d.theme, d.label]));
```

## Share of reviews with each complaint, ${MONTH_NAME(month)}

<p class="caption">Further right is worse. The app with the highest share on each row is named at the end.</p>

${appKey()}

```js
function dots(width) {
  return Plot.plot({
    width,
    height: order.length * 46 + 40,
    marginLeft: 150,
    marginRight: 96,
    style: {fontFamily: "var(--sans-serif)", fontSize: "13px", color: "var(--muted)"},
    x: {grid: true, label: null, tickFormat: (v) => `${Math.round(100 * v)}%`, domain: [0, Math.max(...cur.map((d) => d.share)) * 1.05], nice: true},
    y: {domain: order, tickFormat: (t) => labelOf[t], label: null},
    color: appColor,
    marks: [
      Plot.ruleX([0], {stroke: "var(--axis)"}),
      Plot.link(order.map((t) => {
        const s = cur.filter((d) => d.theme === t).map((d) => d.share);
        return {theme: t, lo: Math.min(...s), hi: Math.max(...s)};
      }), {x1: "lo", x2: "hi", y1: "theme", y2: "theme", stroke: "var(--grid)", strokeWidth: 2}),
      Plot.dot(cur, {x: "share", y: "theme", fill: (d) => APP_NAME[d.app], r: 6, stroke: "var(--page)", strokeWidth: 2}),
      Plot.text(worst, {x: "share", y: "theme", text: (d) => `${APP_NAME[d.app]} ${fmt("share", d.share)}`, dx: 12, textAnchor: "start", fill: "var(--ink)"}),
      Plot.tip(cur, Plot.pointer({x: "share", y: "theme", title: (d) => `${APP_NAME[d.app]}, ${d.label}\n${fmt("share", d.share)} of ${d.n.toLocaleString("en-US")} reviews\nThose reviews average ${d.theme_avg_rating?.toFixed(2)}★`}))
    ]
  });
}
```

<figure>${resize((width) => dots(width))}</figure>

<details><summary>Show the numbers as a table</summary>

```js
Inputs.table(order.flatMap((t) => APPS.map((a) => cur.find((d) => d.theme === t && d.app === a)).filter(Boolean)), {
  columns: ["label", "app", "share", "k", "n", "theme_avg_rating"],
  header: {label: "Complaint", app: "App", share: "Share", k: "Reviews with it", n: "All reviews", theme_avg_rating: "Their avg rating"},
  format: {app: (a) => APP_NAME[a], share: (v) => fmt("share", v), k: (v) => v.toLocaleString("en-US"), n: (v) => v.toLocaleString("en-US"), theme_avg_rating: (v) => v?.toFixed(2)},
  rows: 12, select: false
})
```

</details>

## Average review rating, week by week

```js
const r = weekly.rows.filter((d) => d.metric === "avg_rating");
const lowest = APPS.find((a) => APPS.filter((b) => b !== a).every((b) =>
  Math.max(...r.filter((d) => d.app === a).map((d) => d.value)) < Math.min(...r.filter((d) => d.app === b).map((d) => d.value))));
```

<p class="caption">Review stars, not the Play Store's overall rating, which uses its own formula.${lowest ? ` ${APP_NAME[lowest]}'s best week is still below every other app's worst.` : ""}</p>

${appKey()}

```js
function ratings(width) {
  const rows = weekly.rows.filter((d) => d.metric === "avg_rating");
  const parse = (d) => new Date(d.week + "T00:00:00");
  return Plot.plot({
    width,
    height: 300,
    marginLeft: 40,
    style: {fontFamily: "var(--sans-serif)", fontSize: "13px", color: "var(--muted)"},
    x: {type: "utc", label: null, ticks: width > 640 ? 8 : 4, tickFormat: (d) => d.toLocaleDateString("en-IN", {day: "numeric", month: "short", timeZone: "UTC"})},
    y: {grid: true, label: null, tickFormat: (v) => v.toFixed(1)},
    color: appColor,
    marks: [
      Plot.lineY(rows, {x: parse, y: "value", stroke: (d) => APP_NAME[d.app], strokeWidth: 2, curve: "monotone-x"}),
      Plot.tip(rows, Plot.pointer({x: parse, y: "value", title: (d) => `${APP_NAME[d.app]}, week of ${weekSpan(d.week)}\n${d.value.toFixed(2)}★ from ${d.denom.toLocaleString("en-US")} reviews`}))
    ]
  });
}
```

<figure>${resize((width) => ratings(width))}</figure>
