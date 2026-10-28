"""Weekly metrics and expected-range alerts.

uv run python -m qpulse.metrics                      # alerts for the latest full week
uv run python -m qpulse.metrics --calibrate          # backtest alert widths -> docs/ALERT_CALIBRATION.md
uv run python -m qpulse.metrics --themes FILE        # theme shares from another wide 0/1 label file (.csv/.parquet)

Theme shares come from data/themes.parquet (written by qpulse.classify) when it exists.

All numbers come from the .sql files in sql/; this module only wires them together.
"""
import argparse
from datetime import date
from pathlib import Path

import duckdb
import pandas as pd

from qpulse.classify import THEMES_OUT
from qpulse.config import ALERT_K, ALERT_MIN_N, BASELINE_WEEKS, METRICS_START, ROOT
from qpulse.db import connect
from qpulse.quality import md_table
from qpulse.themes import THEME_KEYS

SQL = ROOT / "sql"
CALIBRATION_OUT = ROOT / "docs" / "ALERT_CALIBRATION.md"

# Which way is bad. 'reviews' (volume) has no good/bad direction.
WORSE_IF = {"avg_rating": "down", "pct_1star": "up", "theme:positive": "down"}


def worse_if(metric: str) -> str | None:
    if metric in WORSE_IF:
        return WORSE_IF[metric]
    return "up" if metric.startswith("theme:") else None


def setup(con: duckdb.DuckDBPyConnection, themes_csv: Path | None = None,
          k: float = ALERT_K, min_n: int = ALERT_MIN_N) -> None:
    """Create reviews_clean, weekly metrics, all_metrics and alerts views on `con`."""
    con.execute(f"SET VARIABLE metrics_start = '{METRICS_START}'")
    con.execute(f"SET VARIABLE baseline_weeks = {BASELINE_WEEKS}")
    con.execute(f"SET VARIABLE alert_k = {k}")
    con.execute(f"SET VARIABLE alert_min_n = {min_n}")
    con.execute((SQL / "reviews_clean.sql").read_text())
    con.execute((SQL / "weekly_metrics.sql").read_text())

    parts = ["SELECT * FROM weekly_metrics"]
    if themes_csv is not None:
        wide = (pd.read_parquet(themes_csv) if themes_csv.suffix == ".parquet"
                else pd.read_csv(themes_csv, dtype={"review_id": str}))
        long = wide.melt(id_vars="review_id", value_vars=THEME_KEYS, var_name="theme", value_name="on")
        con.register("themes_long", long[long["on"] == 1][["review_id", "theme"]])
        con.execute("CREATE OR REPLACE TEMP TABLE review_themes AS SELECT * FROM themes_long")
        con.execute((SQL / "weekly_theme_metrics.sql").read_text())
        parts.append("SELECT * FROM weekly_theme_metrics")
    con.execute("CREATE OR REPLACE VIEW all_metrics AS " + " UNION ALL ".join(parts))
    con.execute((SQL / "alerts.sql").read_text())


def alerts_frame(con: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    df = con.sql("SELECT * FROM alerts ORDER BY week, app, metric").df()
    df["worse_if"] = df["metric"].map(worse_if)
    df["verdict"] = df.apply(
        lambda r: None if not r["is_alert"] else
        ("change" if pd.isna(r["worse_if"]) else "worse" if r["direction"] == r["worse_if"] else "better"),
        axis=1,
    )
    return df


def calibrate(themes_csv: Path | None) -> None:
    con = connect()
    rows, per_metric = [], {}
    for k in (2.0, 2.5, 3.0):
        setup(con, themes_csv, k=k)
        df = alerts_frame(con)
        scored = df[(df["base_weeks"] == BASELINE_WEEKS) & (df["denom"] >= ALERT_MIN_N)]
        weeks = scored["week"].nunique()
        flagged = scored[scored["is_alert"]]
        rows.append({
            "k": k, "weeks scored": weeks, "series": scored.groupby(["app", "metric"]).ngroups,
            "alerts": len(flagged), "alerts / week": round(len(flagged) / weeks, 1),
            "% of metric-weeks flagged": round(100 * len(flagged) / len(scored), 1),
            "worse": int((flagged["verdict"] == "worse").sum()),
            "better": int((flagged["verdict"] == "better").sum()),
            "volume": int((flagged["verdict"] == "change").sum()),
        })
        per_metric[k] = flagged

    setup(con, themes_csv)
    noise = con.sql("""
        SELECT app, metric, count(*) AS weeks,
               round(min(value), 3) AS min, round(avg(value), 3) AS mean, round(max(value), 3) AS max,
               round(stddev_samp(value), 3) AS week_to_week_sd,
               round(avg(CASE WHEN kind = 'share' THEN sqrt(value * (1 - value) / denom) ELSE se END), 3)
                   AS avg_sampling_error
        FROM all_metrics GROUP BY ALL ORDER BY metric, app
    """).df()

    chosen = per_metric[ALERT_K].copy()
    chosen["week"] = chosen["week"].dt.strftime("%Y-%m-%d")
    for c in ("value", "base_mean", "expected_low", "expected_high", "z"):
        chosen[c] = chosen[c].round(3)
    chosen = chosen[["week", "app", "metric", "denom", "value", "base_mean", "expected_low", "expected_high",
                     "z", "verdict"]]

    first, last = con.sql("SELECT min(week), max(week) FROM all_metrics").fetchone()
    CALIBRATION_OUT.write_text(f"""# Alert calibration

_Generated {date.today():%Y-%m-%d} by `uv run python -m qpulse.metrics --calibrate`._
Weeks {first:%Y-%m-%d} to {last:%Y-%m-%d} (full Monday-Sunday weeks from `METRICS_START`).
Theme metrics: {"from `" + themes_csv.name + "`" if themes_csv else "not included (no theme labels for all reviews yet)"}.

A week is flagged when a metric is outside **baseline mean ± k × max(baseline SD, sampling error)**,
with a baseline of the previous {BASELINE_WEEKS} weeks and at least {ALERT_MIN_N} reviews in the week.
For shares the sampling error is taken at the baseline share, so a week at 0% can't shrink its own range. The first {BASELINE_WEEKS}
weeks only serve as baseline.

## Week-to-week noise

{md_table(noise)}

## Backtest: how many alerts each width would have raised

{md_table(pd.DataFrame(rows))}

Chosen: **k = {ALERT_K}**. The weekly report has room for 2-3 actions, so the alert list must stay short.
k = 2 flags ~15% of metric-weeks, far above the ~5% normal noise would give: the SD of only {BASELINE_WEEKS}
weekly values is itself noisy, so the range is often too narrow. k = 3 misses events that read as real
when checked (Blinkit's rating improving two weeks running, caught by both rating metrics; a BigBasket 1★
jump). k = 2.5 keeps those at under one alert a week. Re-check once theme metrics are added: they add
~10 series per app, roughly 4× the alert count.

## Alerts at k = {ALERT_K}

{md_table(chosen) if len(chosen) else "_None._"}
""")
    print(f"wrote {CALIBRATION_OUT.relative_to(ROOT)}")
    print(pd.DataFrame(rows).to_string(index=False))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--calibrate", action="store_true")
    parser.add_argument("--themes", type=Path, default=THEMES_OUT if THEMES_OUT.exists() else None,
                        help="wide file: review_id + one 0/1 column per theme")
    args = parser.parse_args()
    if args.calibrate:
        calibrate(args.themes)
        return

    con = connect()
    setup(con, args.themes)
    df = alerts_frame(con)
    latest = df["week"].max()
    out = df[(df["week"] == latest) & df["is_alert"]]
    print(f"week of {latest:%Y-%m-%d}: {len(out)} alert(s)")
    if len(out):
        print(out[["app", "metric", "denom", "value", "base_mean", "expected_low", "expected_high", "verdict"]]
              .round(3).to_string(index=False))


if __name__ == "__main__":
    main()
