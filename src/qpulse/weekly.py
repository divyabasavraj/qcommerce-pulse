"""Weekly action list (PLAN.md section 8).

Code computes every number; a small local LLM writes only the summary paragraph, from a list of facts written by
code. The summary is checked sentence by sentence against those facts (check_summary); if it fails it is
regenerated once with the errors named, then replaced by a template.

uv run python -m qpulse.weekly                      # latest full week -> reports/weekly/<monday>.md + .json
uv run python -m qpulse.weekly --week 2026-10-12    # a past week
uv run python -m qpulse.weekly --no-llm             # template summary only
uv run python -m qpulse.weekly --skip-existing      # CI: do nothing if this week's report exists
"""
import argparse
import json
from datetime import date, timedelta

import numpy as np
import pandas as pd

from qpulse.classify import THEMES_OUT
from qpulse.config import (ALERT_K, ALERT_MIN_N, APP_NAMES, BASELINE_WEEKS, REPORT_MODEL, ROOT, VERSION_MIN_N)
from qpulse.db import connect
from qpulse.factcheck import llm_summary
from qpulse.metrics import SQL, alerts_frame, setup
from qpulse.quality import md_table
from qpulse.themes import THEME_KEYS

REPORTS = ROOT / "reports" / "weekly"
APPS = APP_NAMES
LABEL = {
    "reviews": "review count", "avg_rating": "average rating", "pct_1star": "1★ share",
    **{f"theme:{k}": k.replace("_", " ") for k in THEME_KEYS},
    "theme:missing_wrong_item": "missing / wrong item", "theme:quality_expiry": "quality / expiry",
    "theme:refund_support": "refund / support", "theme:pricing_fees": "pricing / fees",
    "theme:app_payment_bug": "app / payment bug", "theme:availability_stock": "availability / stock",
    "theme:positive": "positive reviews", "theme:other": "other / vague",
}
# Who acts on a theme, and what they look at first.
ACTION = {
    "delivery_delay": ("Ops", "check rider capacity and promised delivery times"),
    "missing_wrong_item": ("Ops", "audit picking and packing accuracy at dark stores"),
    "quality_expiry": ("Ops", "check freshness and expiry checks on fresh and dairy stock"),
    "availability_stock": ("Ops", "review stock-outs and unserviceable areas"),
    "partner_behaviour": ("Ops", "review delivery-partner conduct complaints and partner briefings"),
    "refund_support": ("Support", "review refund turnaround and support response times"),
    "pricing_fees": ("Product", "review recent fee or price changes and how they are shown in the app"),
    "app_payment_bug": ("Product", "investigate crashes, login and payment failures"),
    "other": ("CX lead", "read a sample of this week's vague reviews for an issue the themes miss"),
}
COMPLAINTS = [k for k in THEME_KEYS if k not in ("positive", "other")]


def fmt(kind: str, v: float) -> str:
    return f"{100 * v:.1f}%" if kind == "share" else f"{v:.2f}" if kind == "mean" else f"{v:,.0f}"


def fmt_delta(kind: str, d: float) -> str:
    return f"{100 * d:+.1f} pts" if kind == "share" else f"{d:+.2f}" if kind == "mean" else f"{d:+,.0f}"


def day(d) -> str:
    return f"{d.day} {d:%b %Y}"


def load(con, week: date | None) -> tuple[pd.DataFrame, date]:
    setup(con, THEMES_OUT)
    df = alerts_frame(con)
    se = con.sql("SELECT app, week, metric, se FROM all_metrics").df()
    df = df.merge(se, on=["app", "week", "metric"], how="left")
    df["week"] = df["week"].dt.date
    week = week or df["week"].max()
    if week not in set(df["week"]):
        raise SystemExit(f"no metrics for week {week}; latest full week is {df['week'].max()}")
    con.execute(f"SET VARIABLE report_week = DATE '{week}'")
    con.execute(f"SET VARIABLE version_min_n = {VERSION_MIN_N}")
    con.execute((SQL / "version_watch.sql").read_text())
    return df, week


def row_dict(r: pd.Series) -> dict:
    return {"app": r["app"], "metric": r["metric"], "kind": r["kind"], "denom": int(r["denom"]),
            "value": float(r["value"]), "se": None if pd.isna(r["se"]) else float(r["se"]),
            "base_mean": float(r["base_mean"]), "expected_low": float(r["expected_low"]),
            "expected_high": float(r["expected_high"]), "z": float(r["z"])}


def actions(cur: pd.DataFrame, versions: pd.DataFrame) -> list[dict]:
    """2-3 actions from alerts in the bad direction and flagged versions, strongest first."""
    out = []
    for _, r in cur[(cur["verdict"] == "worse")].iterrows():
        a = row_dict(r)
        theme = r["metric"].removeprefix("theme:") if r["metric"].startswith("theme:") else None
        if theme not in ACTION:
            # Rating-level alert or fewer positive reviews: hand it to the owner of the complaint rising most.
            rising = cur[(cur["app"] == r["app"]) & cur["metric"].isin([f"theme:{k}" for k in COMPLAINTS])]
            top = rising.sort_values("z", ascending=False).iloc[0] if len(rising) else None
            theme = top["metric"].removeprefix("theme:") if top is not None and top["z"] > 1 else "other"
            a["led_by"] = None if theme == "other" else theme
        a["owner"], a["todo"] = ACTION[theme]
        a["strength"] = abs(a["z"])
        out.append(a)
    for _, v in versions[versions["is_flag"]].iterrows():
        out.append({"app": v["app"], "metric": f"version:{v['metric']}", "version": v["app_version"],
                    "n": int(v["n"]), "value": float(v["share"]), "base_mean": float(v["base_share"]),
                    "z": float(v["z"]), "owner": "Product", "strength": abs(float(v["z"])),
                    "todo": f"look into version {v['app_version']}"})
    return sorted(out, key=lambda a: -a["strength"])[:3]


def action_text(a: dict) -> str:
    app = APPS[a["app"]]
    if a["metric"].startswith("version:"):
        what = "app / payment bug" if a["metric"].endswith("app_payment_bug") else "complaint"
        return (f"**{a['owner']}**: {app}: {a['todo']}. "
                f"Reason: {what} share {100 * a['value']:.1f}% on its {a['n']:,} reviews this week, vs "
                f"{100 * a['base_mean']:.1f}% for {app} over the last {BASELINE_WEEKS} weeks. "
                f"Expected effect: below {100 * 2 * a['base_mean']:.1f}% (2× normal) on this version next week.")
    k, label = a["kind"], LABEL[a["metric"]]
    led = f", led by {LABEL['theme:' + a['led_by']]} complaints" if a.get("led_by") else ""
    return (f"**{a['owner']}**: {app}: {a['todo']}. "
            f"Reason: {label} {fmt(k, a['value'])} vs {fmt(k, a['base_mean'])} normal "
            f"(expected {fmt(k, a['expected_low'])}–{fmt(k, a['expected_high'])}){led}. "
            f"Expected effect: back inside {fmt(k, a['expected_low'])}–{fmt(k, a['expected_high'])} within 2 weeks.")


def followup(prev: dict | None, cur: pd.DataFrame, versions: pd.DataFrame) -> pd.DataFrame | None:
    if prev is None:
        return None
    rows = []
    for a in prev["actions"]:
        app = APPS[a["app"]]
        if a["metric"].startswith("version:"):
            v = versions[(versions["app"] == a["app"]) & (versions["app_version"] == a["version"])
                         & (versions["metric"] == a["metric"].removeprefix("version:"))]
            if v.empty or v["n"].iloc[0] < VERSION_MIN_N:
                status, now = "too few reviews this week to tell", "–"
            else:
                now = f"{100 * v['share'].iloc[0]:.1f}%"
                status = "still flagged" if v["is_flag"].iloc[0] else "no longer flagged"
            rows.append({"app": app, "flagged": f"version {a['version']} {a['metric'].split(':')[1].replace('_', ' ')}",
                         "last week": f"{100 * a['value']:.1f}%", "this week": now, "result": status})
            continue
        r = cur[(cur["app"] == a["app"]) & (cur["metric"] == a["metric"])]
        k = a["kind"]
        if r.empty:
            rows.append({"app": app, "flagged": LABEL[a["metric"]], "last week": fmt(k, a["value"]),
                         "this week": "–", "result": "no data"})
            continue
        r = r.iloc[0]
        d = r["value"] - a["value"]
        if k == "share":
            se = np.sqrt(a["value"] * (1 - a["value"]) / a["denom"] + r["value"] * (1 - r["value"]) / r["denom"])
        else:
            se = np.sqrt((a["se"] or 0) ** 2 + (r["se"] if pd.notna(r["se"]) else 0) ** 2)
        bad_up = r["worse_if"] == "up"
        if se and abs(d) < 2 * se:
            status = "no clear change"
        else:
            status = "worse" if (d > 0) == bad_up else "better"
        inside = r["expected_low"] <= r["value"] <= r["expected_high"]
        rows.append({"app": app, "flagged": LABEL[a["metric"]], "last week": fmt(k, a["value"]),
                     "this week": fmt(k, r["value"]), "change": fmt_delta(k, d), "result": status,
                     "inside expected range": "yes" if inside else "no"})
    return pd.DataFrame(rows)


def body(week: date, cur: pd.DataFrame, versions: pd.DataFrame, acts: list[dict],
         follow: pd.DataFrame | None, prev_week: date) -> str:
    scored = cur[(cur["base_weeks"] == BASELINE_WEEKS) & (cur["denom"] >= ALERT_MIN_N)].copy()
    scored["|z|"] = scored["z"].abs()

    def table(rows: pd.DataFrame) -> pd.DataFrame:
        return pd.DataFrame({
            "app": rows["app"].map(APPS), "metric": rows["metric"].map(LABEL),
            "this week": [fmt(k, v) for k, v in zip(rows["kind"], rows["value"])],
            "normal": [fmt(k, v) for k, v in zip(rows["kind"], rows["base_mean"])],
            "expected range": [f"{fmt(k, lo)}–{fmt(k, hi)}" for k, lo, hi in
                               zip(rows["kind"], rows["expected_low"], rows["expected_high"])],
            "z": rows["z"].map(lambda z: f"{z:+.1f}"),
            "verdict": [v if a else "inside range" for v, a in zip(rows["verdict"], rows["is_alert"])],
        })

    top = scored.sort_values("|z|", ascending=False).head(3)
    alerts = scored[scored["is_alert"]].sort_values("|z|", ascending=False)

    metrics = ["avg_rating", "pct_1star", "reviews"] + [f"theme:{k}" for k in THEME_KEYS]
    comp = []
    for m in metrics:
        row = {"metric": LABEL[m]}
        for app, name in APPS.items():
            r = cur[(cur["app"] == app) & (cur["metric"] == m)]
            if r.empty:
                row[name] = "–"
                continue
            r = r.iloc[0]
            cell = f"{fmt(r['kind'], r['value'])} ({fmt_delta(r['kind'], r['value'] - r['base_mean'])})"
            row[name] = f"**{cell} {r['verdict']}**" if r["is_alert"] else cell
        comp.append(row)

    flagged = versions[versions["is_flag"]]
    big = versions[versions["n"] >= VERSION_MIN_N]
    if len(flagged):
        vtext = md_table(pd.DataFrame({
            "app": flagged["app"].map(APPS), "version": flagged["app_version"],
            "theme": flagged["metric"].str.replace("_", " "), "reviews": flagged["n"].map("{:,}".format),
            "share": flagged["share"].map("{:.1%}".format), "app normal": flagged["base_share"].map("{:.1%}".format),
            "ratio": flagged["ratio"].map("{:.1f}×".format), "z": flagged["z"].map("{:+.1f}".format)}))
    else:
        vtext = (f"No version flagged. {big['app_version'].nunique()} versions had at least {VERSION_MIN_N} "
                 f"reviews this week; none had at least 2× its app's normal bug or complaint share.")

    if acts:
        act_text = "\n".join(f"{i}. {action_text(a)}" for i, a in enumerate(acts, 1))
    else:
        act_text = "No metric is outside its expected range in the bad direction this week, and no version is flagged: no new actions."
    if follow is None:
        follow_text = f"_No report for the week of {day(prev_week)}, so nothing to follow up._"
    elif follow.empty:
        follow_text = "Last week's report had no actions."
    else:
        follow_text = md_table(follow)

    return f"""## Actions

{act_text}

## Last week's follow-up

{follow_text}

## Top 3 changes this week

Largest moves against each metric's normal (z = distance from the {BASELINE_WEEKS}-week mean in standard deviations).

{md_table(table(top))}

## Alerts

{md_table(table(alerts)) if len(alerts) else "_No metric outside its expected range._"}

## Competitor view

This week's value and change from each app's own {BASELINE_WEEKS}-week normal. Bold: outside the expected range.

{md_table(pd.DataFrame(comp))}

## Version watch

{vtext}

## How to read this

- Expected range: the mean of the previous {BASELINE_WEEKS} weeks ± {ALERT_K:g} standard deviations (or ± {ALERT_K:g}
  sampling errors if the baseline was unusually flat). Only weeks with at least {ALERT_MIN_N} reviews are judged.
- Theme shares are among reviews with text, from a classifier that matches hand labels with macro-F1 0.59
  (docs/CLASSIFIER_EVAL.md). Small themes (partner behaviour, availability) are the least reliable.
- Play Store reviewers are not all customers, and unhappy customers review more. Changes are signals to check, not proof.
"""


def facts(cur: pd.DataFrame, acts: list[dict], follow: pd.DataFrame | None, total: int) -> list[dict]:
    """The only material the LLM sees: sentences written by code, each tied to one app (or none) and a status."""
    out = [{"app": None, "status": None, "text": f"{total:,} reviews across the 4 apps this week."}]

    def rng(k, r):
        return f"{fmt(k, r['expected_low'])} to {fmt(k, r['expected_high'])}"

    for i, a in enumerate(acts, 1):
        app = APPS[a["app"]]
        if a["metric"].startswith("version:"):
            what = "app / payment bug" if a["metric"].endswith("app_payment_bug") else "complaint"
            text = (f"Action {i}, owner {a['owner']}: {app} version {a['version']} had a {what} share of "
                    f"{100 * a['value']:.1f}% on its {a['n']:,} reviews, against {100 * a['base_mean']:.1f}% "
                    f"normally for {app}. Next step: {a['todo']}.")
        else:
            k = a["kind"]
            text = (f"Action {i}, owner {a['owner']}: {app} {LABEL[a['metric']]} was {fmt(k, a['value'])} this week "
                    f"against a normal {fmt(k, a['base_mean'])}; outside the expected range of {rng(k, a)} "
                    f"(worse than normal). Next step: {a['todo']}.")
        out.append({"app": a["app"], "status": "outside", "text": text})
    if not acts:
        out.append({"app": None, "status": None, "text": "No actions this week: nothing is worse than its expected range."})

    scored = cur[(cur["base_weeks"] == BASELINE_WEEKS) & (cur["denom"] >= ALERT_MIN_N)]
    for _, r in scored[scored["verdict"] == "better"].iterrows():
        out.append({"app": r["app"], "status": "outside", "text":
                    f"{APPS[r['app']]} {LABEL[r['metric']]} was {fmt(r['kind'], r['value'])} against a normal "
                    f"{fmt(r['kind'], r['base_mean'])}; outside the expected range of {rng(r['kind'], r)} (better than normal)."})
    quiet = scored[~scored["is_alert"]]
    for _, r in quiet.loc[quiet["z"].abs().sort_values(ascending=False).index].head(2).iterrows():
        out.append({"app": r["app"], "status": "inside", "text":
                    f"{APPS[r['app']]} {LABEL[r['metric']]} was {fmt(r['kind'], r['value'])} against a normal "
                    f"{fmt(r['kind'], r['base_mean'])}; inside the expected range of {rng(r['kind'], r)} "
                    f"(normal variation, no action)."})
    if follow is not None:
        for _, f in follow.iterrows():
            key = next(k for k, v in APPS.items() if v == f["app"])
            out.append({"app": key, "status": None, "text":
                        f"Follow-up on last week's action: {f['app']} {f['flagged']} went from {f['last week']} "
                        f"to {f['this week']}: {f['result']}."})
    return out


PROMPT = """You write the summary at the top of a weekly customer-feedback report for the Head of Customer
Experience at an Indian quick-commerce company. The facts below were computed by code from Play Store reviews.

Write 3 to 4 plain sentences (under 100 words), addressed to them directly, saying what matters most this week
and what to act on.
Rules:
- Use only these facts. Copy numbers exactly as written (e.g. "4.8%", "3.82").
- Keep each number in the same sentence as the name of the app it belongs to.
- Do not calculate anything new: no differences, ratios or totals.
- Say a metric is outside or inside its expected range only if its fact says so.
- Recommend only the actions listed. If there are none, say so.
- No headings, no bullet points, no greeting.

FACTS:
"""


def template_summary(acts: list[dict], cur: pd.DataFrame) -> str:
    if not acts:
        scored = cur[(cur["base_weeks"] == BASELINE_WEEKS) & (cur["denom"] >= ALERT_MIN_N)]
        r = scored.loc[scored["z"].abs().idxmax()]
        return (f"A normal week: no metric is outside its expected range in the bad direction. The largest move was "
                f"{APPS[r['app']]}'s {LABEL[r['metric']]} at {fmt(r['kind'], r['value'])} "
                f"against a normal {fmt(r['kind'], r['base_mean'])}.")
    parts = []
    for a in acts:
        if a["metric"].startswith("version:"):
            parts.append(f"{APPS[a['app']]} version {a['version']} ({a['owner']})")
        else:
            parts.append(f"{APPS[a['app']]} {LABEL[a['metric']]} at {fmt(a['kind'], a['value'])} "
                         f"vs {fmt(a['kind'], a['base_mean'])} normal ({a['owner']})")
    lead = "One thing" if len(acts) == 1 else f"{len(acts)} things"
    return f"{lead} to act on this week: " + "; ".join(parts) + "."


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--week", type=date.fromisoformat, help="Monday of the week to report (default: latest full week)")
    parser.add_argument("--model", default=REPORT_MODEL)
    parser.add_argument("--no-llm", action="store_true")
    parser.add_argument("--skip-existing", action="store_true", help="do nothing if the week's report exists (CI)")
    args = parser.parse_args()

    con = connect()
    df, week = load(con, args.week)
    if args.skip_existing and (REPORTS / f"{week}.md").exists():
        print(f"reports/weekly/{week}.md already exists; skipping")
        return
    cur = df[df["week"] == week]
    versions = con.sql("SELECT * FROM version_watch").df()
    acts = actions(cur, versions)
    prev_week = week - timedelta(days=7)
    prev_path = REPORTS / f"{prev_week}.json"
    prev = json.loads(prev_path.read_text()) if prev_path.exists() else None
    follow = followup(prev, cur, versions)
    report_body = body(week, cur, versions, acts, follow, prev_week)
    total = int(cur.loc[cur["metric"] == "reviews", "value"].sum())
    fact_list = facts(cur, acts, follow, total)

    if args.no_llm:
        summary, attempts, source = None, [], "template (LLM not used)"
    else:
        summary, attempts = llm_summary(PROMPT, fact_list, args.model)
        source = (f"{args.model}, fact check passed first time" if summary and len(attempts) == 1 else
                  f"{args.model}, fact check passed on retry" if summary else
                  f"template: {args.model} failed the fact check twice")
    summary = summary or template_summary(acts, cur)
    header = (f"# Weekly action list: {day(week)} – {day(week + timedelta(days=6))}\n\n"
              f"_{total:,} reviews across 4 apps. Generated {date.today().isoformat()} by "
              f"`uv run python -m qpulse.weekly`. Every number comes from SQL (`sql/`). "
              f"Summary: {source}._\n\n## Summary\n\n{summary}\n\n")
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / f"{week}.md").write_text(header + report_body)
    (REPORTS / f"{week}.json").write_text(json.dumps({
        "week": str(week), "reviews": total, "actions": acts, "summary_source": source,
        "summary": summary, "facts": [f["text"] for f in fact_list], "llm_attempts": attempts,
        "followup": None if follow is None else follow.to_dict("records"),
    }, indent=2, default=str) + "\n")
    print(header + report_body)
    print(f"wrote reports/weekly/{week}.md and .json")


if __name__ == "__main__":
    main()
