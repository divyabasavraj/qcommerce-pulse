"""Data for the dashboard (dashboard/src/data/*.json.py call these). Same SQL as the reports; in-memory DuckDB so
loaders can run in parallel. Each function returns plain JSON-able data.

uv run python -c "from qpulse import dashboard_data as d; print(d.method())"
"""
import json

import numpy as np
import pandas as pd

from qpulse import classify
from qpulse.classify import THEMES_OUT
from qpulse.config import ALERT_K, ALERT_MIN_N, APP_NAMES, BASELINE_WEEKS, METRICS_START, ROOT, VERSION_MIN_N
from qpulse.db import connect
from qpulse.evaluate import bootstrap_ci, macro_f1, scores
from qpulse.metrics import SQL, alerts_frame, setup
from qpulse.themes import THEME_KEYS
from qpulse.weekly import LABEL

REPORTS = ROOT / "reports"


def _con():
    con = connect(path=":memory:")
    setup(con, THEMES_OUT)
    return con


def _records(df: pd.DataFrame) -> list[dict]:
    return json.loads(df.to_json(orient="records", date_format="iso"))


def weekly() -> dict:
    """Every weekly metric with its expected range, for weeks scored against a full baseline."""
    con = _con()
    df = alerts_frame(con)
    df = df[df["week"] >= METRICS_START]
    df["week"] = df["week"].dt.strftime("%Y-%m-%d")
    df["label"] = df["metric"].map(LABEL)
    df["scored"] = (df["base_weeks"] == BASELINE_WEEKS) & (df["denom"] >= ALERT_MIN_N)
    cols = ["app", "week", "metric", "label", "kind", "denom", "value", "base_mean", "expected_low",
            "expected_high", "z", "is_alert", "verdict", "worse_if", "scored"]
    return {"apps": APP_NAMES, "k": ALERT_K, "baseline_weeks": BASELINE_WEEKS, "min_n": ALERT_MIN_N,
            "rows": _records(df[cols].sort_values(["metric", "app", "week"]))}


def monthly() -> dict:
    con = _con()
    con.execute((SQL / "monthly_metrics.sql").read_text())
    apps = con.sql("SELECT app, strftime(month, '%Y-%m') AS month, n, avg_rating FROM monthly_app ORDER BY month").df()
    themes = con.sql("""SELECT app, strftime(month, '%Y-%m') AS month, theme, n, k, share, theme_avg_rating,
                               avg_rating, halved_avg_rating, gain FROM monthly_themes ORDER BY month""").df()
    themes["label"] = themes["theme"].map(lambda t: LABEL[f"theme:{t}"])
    return {"apps": _records(apps), "themes": _records(themes)}


def reports() -> dict:
    weekly_ = [json.loads(p.read_text()) for p in sorted((REPORTS / "weekly").glob("*.json"))]
    monthly_ = [json.loads(p.read_text()) for p in sorted((REPORTS / "monthly").glob("*.json"))]
    return {"weekly": weekly_, "monthly": monthly_}


def quotes(per_group: int = 5) -> dict:
    """A few real reviews behind the latest week's actions (or its biggest move if there are none)."""
    latest = json.loads(sorted((REPORTS / "weekly").glob("*.json"))[-1].read_text())
    week = latest["week"]
    targets = [(a["app"], a["metric"].removeprefix("theme:")) for a in latest["actions"]
               if a["metric"].startswith("theme:")]
    con = _con()
    out = []
    for app, theme in targets:
        df = con.sql(f"""
            SELECT r.text, r.rating, r.review_date
            FROM metric_reviews r JOIN review_themes t USING (review_id)
            WHERE r.app = '{app}' AND t.theme = '{theme}' AND r.review_week = DATE '{week}'
              AND NOT r.is_empty_or_symbols AND length(r.text) BETWEEN 50 AND 240
        """).df()
        sample = df.sample(min(per_group, len(df)), random_state=0) if len(df) else df
        out.append({"app": app, "theme": theme, "label": LABEL[f"theme:{theme}"], "week": week,
                    "matching": int(len(df)),
                    "reviews": _records(sample.assign(review_date=sample["review_date"].astype(str)))})
    return {"week": week, "groups": out}


def method() -> dict:
    con = _con()
    totals = con.sql("""SELECT app, count(*) AS reviews, min(review_date)::VARCHAR AS first, max(review_date)::VARCHAR AS last
                        FROM reviews_clean GROUP BY app ORDER BY reviews DESC""").df()

    hand = pd.read_csv(classify.LABELS / "hand_labels.csv")
    notes = hand["note"].fillna("")
    tune, test = classify.hand_data()
    clf = classify.train()
    pred = clf.predict(classify.texts(test))
    truth = test[THEME_KEYS]
    llm = (pd.read_csv(classify.TRAIN_LABELS).set_index("review_id")
           .loc[test["review_id"], THEME_KEYS].reset_index(drop=True))

    def summary(p: pd.DataFrame) -> dict:
        lo, hi = bootstrap_ci(truth, p)
        return {"macro_f1": round(float(macro_f1(truth, p)), 3), "ci": [round(lo, 3), round(hi, 3)],
                "exact": round(float((truth.values == p.values).all(axis=1).mean()), 3)}

    per_theme = scores(truth, pred)[["theme", "support", "f1"]].merge(
        scores(truth, llm)[["theme", "f1"]].rename(columns={"f1": "llm_f1"}), on="theme")
    per_theme["label"] = per_theme["theme"].map(lambda t: LABEL[f"theme:{t}"])

    weekly_ = [json.loads(p.read_text()) for p in sorted((REPORTS / "weekly").glob("*.json"))]
    sources = pd.Series([w["summary_source"] for w in weekly_])
    return {
        "totals": _records(totals), "reviews": int(totals["reviews"].sum()),
        "hand": {"n": len(hand), "tuning": len(tune), "held_out": len(test),
                 "corrected": int(notes.str.startswith("changed after").sum()),
                 "adjudicated": int(notes.str.startswith("adjudicated").sum())},
        "classifier": summary(pred), "llm": summary(llm),
        "per_theme": _records(per_theme.replace({np.nan: None})),
        "train_size": 3000,
        "alerts": {"k": ALERT_K, "baseline_weeks": BASELINE_WEEKS, "min_n": ALERT_MIN_N, "version_min_n": VERSION_MIN_N},
        "fact_check": {"weekly_reports": len(weekly_),
                       "passed_first": int(sources.str.contains("passed first").sum()),
                       "passed_retry": int(sources.str.contains("passed on retry").sum()),
                       "template": int(sources.str.startswith("template").sum())},
    }
