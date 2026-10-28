import * as Plot from "npm:@observablehq/plot";
import {html} from "npm:htl";

// Fixed app order and colours (validated all-pairs in light and dark; see style.css). Colour follows the app,
// never its rank, and every chart also names the app in text.
export const APPS = ["blinkit", "zepto", "instamart", "bigbasket"];
export const APP_NAME = {blinkit: "Blinkit", zepto: "Zepto", instamart: "Instamart", bigbasket: "BigBasket"};
export const appColor = {
  type: "ordinal",
  domain: APPS.map((a) => APP_NAME[a]),
  range: APPS.map((a) => `var(--app-${a})`)
};

export const COMPLAINTS = [
  "delivery_delay", "missing_wrong_item", "quality_expiry", "refund_support",
  "pricing_fees", "app_payment_bug", "partner_behaviour", "availability_stock"
];

export function fmt(kind, v) {
  if (v == null) return "–";
  if (kind === "share") return `${(100 * v).toFixed(1)}%`;
  if (kind === "mean") return v.toFixed(2);
  return Math.round(v).toLocaleString("en-US");
}

export function fmtDelta(kind, d) {
  const s = d >= 0 ? "+" : "−";
  if (kind === "share") return `${s}${Math.abs(100 * d).toFixed(1)} pts`;
  if (kind === "mean") return `${s}${Math.abs(d).toFixed(2)}`;
  return `${s}${Math.abs(Math.round(d)).toLocaleString("en-US")}`;
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
export function day(iso) {
  const [y, m, d] = iso.slice(0, 10).split("-").map(Number);
  return `${d} ${MONTHS[m - 1]}`;
}
export function weekSpan(iso) {
  const start = new Date(iso.slice(0, 10) + "T00:00:00");
  const end = new Date(start);
  end.setDate(start.getDate() + 6);
  const same = start.getMonth() === end.getMonth();
  return `${start.getDate()}${same ? "" : " " + MONTHS[start.getMonth()]}–${end.getDate()} ${MONTHS[end.getMonth()]} ${end.getFullYear()}`;
}

export function appKey(apps = APPS) {
  return html`<div class="key">${apps.map((a) => html`<span style="--swatch: var(--app-${a})">${APP_NAME[a]}</span>`)}</div>`;
}

export function verdictMark(r) {
  if (!r.is_alert) return "inside range";
  if (r.verdict === "worse") return html`<span class="mark-worse">worse</span>`;
  if (r.verdict === "better") return html`<span class="mark-better">better</span>`;
  return "outside range";
}

// One metric for one app over time: the expected range as a wash, the value as a 2px line,
// weeks outside the range as filled markers (red = worse, blue = better).
export function rangeChart(rows, {width, height = 240, kind = "share", color = "var(--ink)", title, yDomain} = {}) {
  const scored = rows.filter((d) => d.scored);
  const tick = kind === "share" ? (v) => `${(100 * v).toFixed(v < 0.1 ? 1 : 0)}%` : kind === "mean" ? (v) => v.toFixed(1) : (v) => v.toLocaleString("en-US");
  const parse = (d) => new Date(d.week + "T00:00:00");
  return Plot.plot({
    width,
    height,
    marginLeft: 48,
    marginRight: 16,
    style: {fontFamily: "var(--sans-serif)", fontSize: "13px", color: "var(--muted)"},
    x: {type: "utc", label: null, ticks: width > 640 ? 8 : 4, tickFormat: (d) => `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]}`},
    y: {grid: true, label: null, tickFormat: tick, nice: true, zero: kind === "share", domain: yDomain},
    marks: [
      Plot.areaY(scored, {x: parse, y1: "expected_low", y2: "expected_high", fill: "var(--band)", curve: "step"}),
      Plot.lineY(rows, {x: parse, y: "value", stroke: color, strokeWidth: 2, curve: "monotone-x"}),
      Plot.dot(scored.filter((d) => d.is_alert), {
        x: parse, y: "value", r: 5, stroke: "var(--page)", strokeWidth: 2,
        fill: (d) => (d.verdict === "worse" ? "var(--worse)" : d.verdict === "better" ? "var(--better)" : "var(--ink)")
      }),
      Plot.ruleY(kind === "share" ? [0] : [], {stroke: "var(--axis)"}),
      Plot.tip(rows, Plot.pointerX({
        x: parse, y: "value",
        title: (d) => `Week of ${weekSpan(d.week)}\n${title ?? d.label}: ${fmt(d.kind, d.value)}` +
          (d.scored ? `\nNormal ${fmt(d.kind, d.base_mean)}, expected ${fmt(d.kind, d.expected_low)}–${fmt(d.kind, d.expected_high)}` : "\nNot enough history to judge yet") +
          `\n${d.denom.toLocaleString("en-US")} reviews`
      }))
    ]
  });
}
