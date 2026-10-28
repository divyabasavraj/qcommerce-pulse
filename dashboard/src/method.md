---
title: How it works
---

```js
import {APP_NAME} from "./components/pulse.js";
const m = FileAttachment("data/method.json").json();
```

# How it works

<p class="lede">Every number on this site comes from public Google Play reviews, sorted into complaint themes and checked against what a person would say. Here is how, and how far to trust it.</p>

```js
const n = (v) => v.toLocaleString("en-US");
const first = m.totals.map((d) => d.first).sort()[0];
const DAY = (iso) => new Date(iso + "T00:00:00").toLocaleDateString("en-IN", {day: "numeric", month: "short", year: "numeric"});
```

<div class="facts">
  <div><b>${n(m.reviews)}</b>reviews since ${DAY(first)}, collected every morning</div>
  <div><b>${m.hand.n}</b>reviews labelled by hand, the yardstick for everything else</div>
  <div><b>${m.classifier.macro_f1.toFixed(2)}</b>macro-F1 of the theme classifier on ${m.hand.held_out} hand labels it never saw</div>
  <div><b>${m.fact_check.weekly_reports}</b>weekly reports so far, every AI sentence checked against the data</div>
</div>

## From review to action

1. **Collect.** A scheduled job pulls new reviews for Blinkit, Zepto, Swiggy Instamart and BigBasket every morning. Reviewer names and photos are never stored; phone numbers and emails in the text are masked.
2. **Clean.** Copy-paste spam, link spam and emoji-only reviews are flagged and left out of the metrics.
3. **Label.** A local language model (qwen2.5, 7 billion parameters) labelled ${n(m.train_size)} reviews with up to ten themes. A small, fast classifier learned from those labels and now labels every review in seconds.
4. **Measure.** Each week, every metric is compared with its own previous ${m.alerts.baseline_weeks} weeks. It's flagged when it leaves that range by more than ${m.alerts.k} standard deviations, and only with at least ${m.alerts.min_n} reviews.
5. **Report.** Flags become actions with an owner. A weekly report goes out every Monday and a memo on the 1st of each month. Next week checks whether last week's problems eased.

## How good are the themes?

<p class="caption">Measured on ${m.hand.held_out} hand-labelled reviews that played no part in building either labeller. ${m.hand.tuning} other hand labels were used to tune the prompt and pick the classifier's settings.</p>

```js
Inputs.table([
  {who: "Fast classifier (runs daily)", f1: m.classifier.macro_f1, ci: m.classifier.ci, exact: m.classifier.exact},
  {who: "Language model it learned from", f1: m.llm.macro_f1, ci: m.llm.ci, exact: m.llm.exact}
], {
  header: {who: "Labeller", f1: "Macro-F1", ci: "95% interval", exact: "All themes exactly right"},
  format: {f1: (v) => v.toFixed(2), ci: (c) => `${c[0].toFixed(2)}–${c[1].toFixed(2)}`, exact: (v) => `${Math.round(100 * v)}%`},
  select: false
})
```

<p>The classifier is as good as its teacher (the difference is inside the noise) and about ten thousand times faster. Some themes are much harder than others:</p>

```js
function f1chart(width) {
  const rows = m.per_theme.slice().sort((a, b) => b.f1 - a.f1);
  return Plot.plot({
    width,
    height: rows.length * 34 + 40,
    marginLeft: 170,
    marginRight: 24,
    style: {fontFamily: "var(--sans-serif)", fontSize: "13px", color: "var(--muted)"},
    x: {domain: [0, 1], grid: true, label: null, tickFormat: (v) => v.toFixed(1)},
    y: {domain: rows.map((d) => d.theme), tickFormat: (t) => {
      const d = rows.find((r) => r.theme === t);
      return `${d.label} (${d.support})`;
    }, label: null},
    marks: [
      Plot.link(rows, {x1: "f1", x2: "llm_f1", y1: "theme", y2: "theme", stroke: "var(--grid)", strokeWidth: 2}),
      Plot.dot(rows, {x: "llm_f1", y: "theme", r: 5, stroke: "var(--muted)", strokeWidth: 2, fill: "var(--page)"}),
      Plot.dot(rows, {x: "f1", y: "theme", r: 5, fill: "var(--ink)", stroke: "var(--page)", strokeWidth: 2}),
      Plot.tip(rows, Plot.pointerY({x: "f1", y: "theme", title: (d) => `${d.label}: classifier ${d.f1.toFixed(2)}, language model ${d.llm_f1?.toFixed(2)}\n${d.support} hand-labelled examples`}))
    ]
  });
}
```

<p class="caption">Filled dot: the fast classifier. Hollow dot: the language model. F1 per theme; the number in brackets is how many of the ${m.hand.held_out} test reviews a person gave that theme. Themes with few examples, like partner behaviour, are the least reliable.</p>

<figure>${resize((width) => f1chart(width))}</figure>

## About the hand labels

<p>All ${m.hand.n} were labelled by hand. A review pass flagged likely slips, and ${m.hand.corrected} labels were changed, each one approved and noted in the file. After comparing with the language model, ${m.hand.adjudicated} more were re-read against their text and corrected. Nothing was ever changed just to agree with the model.</p>

## Checking what the AI writes

<p>The weekly summary is written by a small language model, but it only sees facts that code has already computed. Every sentence is then checked: each number must belong to the app named in that sentence, and any claim that something is inside or outside its expected range must match the data. A summary that fails is rewritten once, then replaced by one written by code.</p>
<p>So far: ${m.fact_check.passed_first} of ${m.fact_check.weekly_reports} passed first time, ${m.fact_check.passed_retry} on a retry, ${m.fact_check.template} fell back to code. The first version of the check only made sure every number appeared somewhere in the report. Three of four early summaries passed it and were still wrong, for example calling a value "outside the expected range" when it was inside. The monthly memo's summary is written by code, because the model kept making confident claims the rules couldn't catch.</p>

## What this can't tell you

- People who write Play Store reviews aren't all customers, and unhappy ones write more. These are signals to check, not a measure of every order.
- Review stars aren't the Play Store rating, which uses its own formula.
- There's no internal data here: no orders, no delivery times, no refunds issued. A rise in complaints is a reason to look, not proof of cause.
- The themes are right most of the time, not always. Small themes are the weakest.

<p class="caption">Code, SQL, label files and the full project log: <a href="https://github.com/divyabasavraj/qcommerce-pulse">github.com/divyabasavraj/qcommerce-pulse</a>.</p>
