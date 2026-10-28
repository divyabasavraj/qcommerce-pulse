"""Monthly decision memo (PLAN.md section 9.1): impact sizing, top 3 fixes per app, competitor comparison,
predictions for next month and last month's scorecard. Code computes every number, makes every prediction and,
by default, writes the summary too: on the first three memos qwen2.5:3b wrote false claims that passed the
fact check ("stayed above 3.25" when the value was 3.24; praise for predictions that didn't exist), so the LLM
summary is opt-in (--llm), still fact-checked (qpulse.factcheck).

uv run python -m qpulse.monthly                     # latest complete month -> reports/monthly/<YYYY-MM>.md + .json
uv run python -m qpulse.monthly --month 2026-09     # a past month
uv run python -m qpulse.monthly --llm               # try an LLM-written summary
uv run python -m qpulse.monthly --skip-existing     # CI: do nothing if the month's memo exists
"""
import argparse
import json
from datetime import date

import numpy as np
import pandas as pd

from qpulse.classify import THEMES_OUT
from qpulse.config import APP_NAMES, REPORT_MODEL, ROOT
from qpulse.db import connect
from qpulse.factcheck import llm_summary
from qpulse.metrics import SQL, setup
from qpulse.quality import md_table
from qpulse.weekly import COMPLAINTS, LABEL

REPORTS = ROOT / "reports" / "monthly"
APPS = APP_NAMES
HISTORY_MONTHS = 3  # months behind each prediction's range
# Deep-dive of the month (PLAN.md section 9.2), keyed by the month the memo covers.
DEEP_DIVES: dict[str, str] = {}


def name(theme: str) -> str:
    return LABEL[f"theme:{theme}"]


def month_label(m: date) -> str:
    return f"{m:%B %Y}"


def load(con, month: date | None) -> tuple[pd.DataFrame, pd.DataFrame, date]:
    setup(con, THEMES_OUT)
    con.execute((SQL / "monthly_metrics.sql").read_text())
    apps = con.sql("SELECT * FROM monthly_app").df()
    themes = con.sql("SELECT * FROM monthly_themes").df()
    for df in (apps, themes):
        df["month"] = pd.to_datetime(df["month"]).dt.date
    month = month or apps["month"].max()
    if month not in set(apps["month"]):
        raise SystemExit(f"no complete month {month}; latest is {apps['month'].max()}")
    return apps, themes, month


def top_fixes(themes: pd.DataFrame, month: date) -> pd.DataFrame:
    cur = themes[(themes["month"] == month) & themes["theme"].isin(COMPLAINTS)]
    return cur.sort_values("gain", ascending=False).groupby("app").head(3)


def predictions(apps: pd.DataFrame, themes: pd.DataFrame, month: date, fixes: pd.DataFrame) -> list[dict]:
    """No-change predictions for next month, two per app: its #1 fix theme's share and its average rating stay
    within the range of the last few months, widened by 2 sampling errors at this month's review count.
    A miss means something changed and is worth a look."""
    out = []
    for app in APPS:
        a = apps[(apps["app"] == app) & (apps["month"] <= month)].sort_values("month").tail(HISTORY_MONTHS)
        if len(a) < 2:
            continue
        n = a["n"].iloc[-1]
        se = a["sd_rating"].iloc[-1] / np.sqrt(n)
        out.append({"app": app, "metric": "avg_rating", "low": round(a["avg_rating"].min() - 2 * se, 2),
                    "high": round(a["avg_rating"].max() + 2 * se, 2), "months": len(a)})
        top = fixes[fixes["app"] == app].iloc[0]["theme"]
        t = themes[(themes["app"] == app) & (themes["theme"] == top) & (themes["month"] <= month)]
        t = t.sort_values("month").tail(HISTORY_MONTHS)
        p = t["share"].iloc[-1]
        se = np.sqrt(p * (1 - p) / n)
        out.append({"app": app, "metric": f"theme:{top}", "low": round(max(0.0, t["share"].min() - 2 * se), 3),
                    "high": round(t["share"].max() + 2 * se, 3), "months": len(t)})
    return out


def fmt_pred(p: dict) -> tuple[str, str]:
    if p["metric"] == "avg_rating":
        return "average rating", f"{p['low']:.2f}–{p['high']:.2f}"
    return name(p["metric"].removeprefix("theme:")) + " share", f"{100 * p['low']:.1f}%–{100 * p['high']:.1f}%"


def scorecard(prev: dict | None, apps: pd.DataFrame, themes: pd.DataFrame, month: date) -> list[dict] | None:
    if prev is None:
        return None
    rows = []
    for p in prev["predictions"]:
        if p["metric"] == "avg_rating":
            v = apps[(apps["app"] == p["app"]) & (apps["month"] == month)]["avg_rating"]
            actual = None if v.empty else float(v.iloc[0])
            shown = "–" if actual is None else f"{actual:.2f}"
        else:
            v = themes[(themes["app"] == p["app"]) & (themes["month"] == month)
                       & (themes["theme"] == p["metric"].removeprefix("theme:"))]["share"]
            actual = None if v.empty else float(v.iloc[0])
            shown = "–" if actual is None else f"{100 * actual:.1f}%"
        what, rng = fmt_pred(p)
        hit = None if actual is None else p["low"] <= round(actual, 3 if p["metric"] != "avg_rating" else 2) <= p["high"]
        rows.append({"app": APPS[p["app"]], "prediction": f"{what} stays within {rng}", "actual": shown,
                     "result": "no data" if hit is None else "right" if hit else "wrong"})
    return rows


def body(apps, themes, month, fixes, preds, score) -> str:
    cur_apps = apps[apps["month"] == month].set_index("app")
    cur = themes[themes["month"] == month]
    prev_month = (pd.Timestamp(month) - pd.DateOffset(months=1)).date()
    prev = themes[themes["month"] == prev_month]

    fix_rows = []
    for app in APPS:
        f = fixes[fixes["app"] == app]
        if f.empty:
            continue
        a = cur_apps.loc[app]
        for rank, (_, r) in enumerate(f.iterrows(), 1):
            fix_rows.append({
                "app": APPS[app] if rank == 1 else "", "#": rank, "theme": name(r["theme"]),
                "share of reviews": f"{100 * r['share']:.1f}%", "their avg rating": f"{r['theme_avg_rating']:.2f}",
                "app avg rating": f"{a['avg_rating']:.2f}" if rank == 1 else "",
                "if halved": f"{r['halved_avg_rating']:.2f}", "gain": f"{r['gain']:+.2f}",
            })

    impact = []
    for t in COMPLAINTS:
        row = {"theme": name(t)}
        for app, label in APPS.items():
            r = cur[(cur["app"] == app) & (cur["theme"] == t)]
            row[label] = "–" if r.empty else f"{r['gain'].iloc[0]:+.3f}"
        impact.append(row)

    comp = [{"metric": "average rating",
             **{label: f"{cur_apps.loc[app, 'avg_rating']:.2f}" for app, label in APPS.items() if app in cur_apps.index}}]
    for t in COMPLAINTS:
        row = {"metric": name(t)}
        shares = cur[cur["theme"] == t].set_index("app")["share"]
        order = shares.rank(method="min").astype(int)
        for app, label in APPS.items():
            if app not in shares.index:
                row[label] = "–"
                continue
            p = prev[(prev["app"] == app) & (prev["theme"] == t)]["share"]
            change = "" if p.empty else f", {100 * (shares[app] - p.iloc[0]):+.1f} pts"
            row[label] = f"{100 * shares[app]:.1f}% (#{order[app]}{change})"
        comp.append(row)

    pred_rows = []
    for p in preds:
        what, rng = fmt_pred(p)
        pred_rows.append({"app": APPS[p["app"]], "metric": what, "range for next month": rng,
                          "based on": f"last {p['months']} months"})

    if score is None:
        score_text = f"_No memo for {month_label(prev_month)}, so no predictions to score._"
    else:
        right = sum(r["result"] == "right" for r in score)
        judged = sum(r["result"] != "no data" for r in score)
        score_text = f"{right} of {judged} predictions right.\n\n" + md_table(pd.DataFrame(score))

    key = f"{month:%Y-%m}"
    deep = DEEP_DIVES.get(key) or (
        "No deep-dive this month. The first one, festival readiness around Diwali (Nov 8), comes in the "
        "November 2026 memo." if month < date(2026, 11, 1) else "_Deep-dive not written yet._")

    return f"""## Top 3 fixes per app

Ranked by the estimated gain in the app's average review rating if that theme's complaints were halved
(reviews carrying the theme re-weighted by 0.5). Themes overlap, so gains for different themes don't add up.

{md_table(pd.DataFrame(fix_rows))}

## Impact sizing: rating gain if each complaint were halved

{md_table(pd.DataFrame(impact))}

## Competitor comparison

Share of each app's reviews with the theme; #1 = fewest complaints among the four apps; change vs {month_label(prev_month)}.

{md_table(pd.DataFrame(comp))}

## Predictions for {month_label((pd.Timestamp(month) + pd.DateOffset(months=1)).date())}

No-change predictions: each app's average rating and its #1 fix theme's share stay within the range of recent
months, widened by 2 sampling errors. A miss means something changed and is worth a look.

{md_table(pd.DataFrame(pred_rows))}

## Scorecard: last month's predictions

{score_text}

## Deep-dive of the month

{deep}

## How to read this

- Reviews with text in {month_label(month)}, without copy-paste or link reviews (docs/DATA_QUALITY.md). Ratings are
  review stars, not the Play Store's overall rating, which uses its own formula.
- Themes come from a classifier that matches hand labels with macro-F1 0.59 (docs/CLASSIFIER_EVAL.md).
- Rating gains are estimates from review ratings: they assume the removed complaints would have taken their
  ratings with them, and say nothing about cost. Correlation, not proof of cause.
"""


PROMPT = """You write the summary at the top of a monthly decision memo for the Head of Customer Experience at an
Indian quick-commerce company. The facts below were computed by code from Play Store reviews.

Write 3 to 4 plain sentences (under 100 words), addressed to them directly: which fixes are worth the most and
for which app, and how last month's predictions did.
Rules:
- Use only these facts. Copy numbers exactly as written (e.g. "20.6%", "+0.24").
- Keep each number in the same sentence as the name of the app it belongs to.
- Do not calculate anything new: no differences, ratios or totals.
- Rating gains are estimates; say so once.
- No headings, no bullet points, no greeting.

FACTS:
"""


def facts(apps, month, fixes, score) -> list[dict]:
    n = int(apps[apps["month"] == month]["n"].sum())
    out = [{"app": None, "status": None, "text": f"{n:,} reviews with text across the 4 apps in {month_label(month)}."}]
    for app in APPS:
        f = fixes[fixes["app"] == app]
        if f.empty:
            continue
        r = f.iloc[0]
        out.append({"app": app, "status": None, "text":
                    f"{APPS[app]}'s most valuable fix is {name(r['theme'])}: {100 * r['share']:.1f}% of its reviews, "
                    f"averaging {r['theme_avg_rating']:.2f} stars; halving these complaints would raise {APPS[app]}'s "
                    f"average review rating from {r['avg_rating']:.2f} to {r['halved_avg_rating']:.2f} "
                    f"({r['gain']:+.2f}, an estimate)."})
    if score:
        right = sum(r["result"] == "right" for r in score)
        judged = sum(r["result"] != "no data" for r in score)
        out.append({"app": None, "status": None, "text": f"{right} of {judged} of last month's predictions were right."})
        for r in score:
            if r["result"] == "wrong":
                key = next(k for k, v in APPS.items() if v == r["app"])
                out.append({"app": key, "status": None, "text":
                            f"Wrong prediction: {r['app']} {r['prediction']}; actual {r['actual']}."})
    return out


def template_summary(apps, month, fixes, score) -> str:
    best = fixes.sort_values("gain", ascending=False).iloc[0]
    firsts = fixes.groupby("app").head(1)
    text = (f"The most valuable fix is {name(best['theme'])} at {APPS[best['app']]}: {100 * best['share']:.1f}% of its "
            f"reviews, averaging {best['theme_avg_rating']:.2f} stars; halving them would raise its average review "
            f"rating from {best['avg_rating']:.2f} to {best['halved_avg_rating']:.2f} (an estimate). ")
    if firsts["theme"].nunique() == 1:
        text += (f"{name(best['theme']).capitalize()} is the #1 fix at all four apps ("
                 + ", ".join(f"{APPS[r['app']]} {r['gain']:+.2f}" for _, r in firsts.iterrows()) + "). ")
    else:
        text += "#1 fix by app: " + ", ".join(
            f"{APPS[r['app']]} {name(r['theme'])} ({r['gain']:+.2f})" for _, r in firsts.iterrows()) + ". "
    if score:
        right = sum(r["result"] == "right" for r in score)
        judged = sum(r["result"] != "no data" for r in score)
        missed = [f"{r['app']} {r['prediction'].replace(' stays within ', ' (predicted ')}, actual {r['actual']})"
                  for r in score if r["result"] == "wrong"]
        text += f"{right} of {judged} of last month's predictions were right" + (
            "; missed: " + "; ".join(missed) + "." if missed else ".")
    return text.strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--month", type=lambda s: date.fromisoformat(s + "-01"), help="YYYY-MM (default: latest complete)")
    parser.add_argument("--model", default=REPORT_MODEL)
    parser.add_argument("--llm", action="store_true", help="try an LLM-written summary (off by default)")
    parser.add_argument("--skip-existing", action="store_true", help="do nothing if the month's memo exists (CI)")
    args = parser.parse_args()

    con = connect()
    apps, themes, month = load(con, args.month)
    key = f"{month:%Y-%m}"
    if args.skip_existing and (REPORTS / f"{key}.md").exists():
        print(f"reports/monthly/{key}.md already exists; skipping")
        return
    fixes = top_fixes(themes, month)
    preds = predictions(apps, themes, month, fixes)
    prev_path = REPORTS / f"{(pd.Timestamp(month) - pd.DateOffset(months=1)):%Y-%m}.json"
    score = scorecard(json.loads(prev_path.read_text()) if prev_path.exists() else None, apps, themes, month)
    report_body = body(apps, themes, month, fixes, preds, score)
    fact_list = facts(apps, month, fixes, score)

    if not args.llm:
        summary, attempts, source = None, [], "written by code"
    else:
        summary, attempts = llm_summary(PROMPT, fact_list, args.model)
        source = (f"{args.model}, fact check passed first time" if summary and len(attempts) == 1 else
                  f"{args.model}, fact check passed on retry" if summary else
                  f"template: {args.model} failed the fact check twice")
    summary = summary or template_summary(apps, month, fixes, score)

    n = int(apps[apps["month"] == month]["n"].sum())
    header = (f"# Monthly memo: {month_label(month)}\n\n"
              f"_{n:,} reviews with text across 4 apps. Generated {date.today().isoformat()} by "
              f"`uv run python -m qpulse.monthly`. Every number comes from SQL (`sql/monthly_metrics.sql`). "
              f"Summary: {source}._\n\n## Summary\n\n{summary}\n\n")
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / f"{key}.md").write_text(header + report_body)
    (REPORTS / f"{key}.json").write_text(json.dumps({
        "month": key, "reviews": n, "predictions": preds, "scorecard": score,
        "top_fixes": fixes[["app", "theme", "share", "theme_avg_rating", "avg_rating", "halved_avg_rating", "gain"]]
        .to_dict("records"),
        "summary_source": source, "summary": summary, "facts": [f["text"] for f in fact_list], "llm_attempts": attempts,
    }, indent=2, default=str) + "\n")
    print(header + report_body)
    print(f"wrote reports/monthly/{key}.md and .json")


if __name__ == "__main__":
    main()
