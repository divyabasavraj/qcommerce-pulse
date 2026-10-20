"""Data-quality report: uv run python -m qpulse.quality  ->  docs/DATA_QUALITY.md

Every issue gets a count, a share, a decision and a reason. Numbers are recomputed on each run;
decisions are kept here so they are reviewed whenever the numbers change.
"""
from datetime import date

import pandas as pd

from qpulse.config import ROOT, RUN_LOG
from qpulse.db import connect

OUT = ROOT / "docs" / "DATA_QUALITY.md"

# flag column -> (issue, decision, reason)
DECISIONS = {
    "is_empty_or_symbols": (
        "Empty or emoji/symbol-only text",
        "Keep for rating metrics; exclude from theme metrics",
        "The star rating is still a real signal, but there's no text to classify.",
    ),
    "is_very_short": (
        "Very short (≤2 words, e.g. 'good', 'worst app')",
        "Keep; classify as usual (most become `positive` or `other`)",
        "These are a large, real part of the review stream; dropping them would inflate complaint shares.",
    ),
    "is_repeated_text": (
        "Same ≥40-character text posted ≥3 times for one app",
        "Exclude from all metrics",
        "Copy-paste campaigns or bots; one person/script shouldn't count several times. In practice these are "
        "mostly the same delivery partner's name praised over and over, i.e. partners soliciting 5★ reviews.",
    ),
    "has_link": (
        "Contains a URL or t.me / wa.me link",
        "Exclude from all metrics",
        "Promotion or scam text, not customer feedback. The word 'WhatsApp' alone is NOT flagged: most such "
        "reviews are customers reporting scam WhatsApp messages, which is real feedback (found in v1 of this rule).",
    ),
    "star_text_mismatch": (
        "Text and stars disagree ('great app' with 1★, 'worst' with 5★)",
        "Keep; report separately as a caveat on rating metrics",
        "Often users who misunderstand the stars. Themes come from the text, so theme metrics are unaffected; "
        "rating-by-theme numbers carry this noise.",
    ),
    "missing_version": (
        "App version missing",
        "Keep; exclude only from version-watch analysis",
        "Version is optional metadata (e.g. reviews posted from the web); the review itself is valid.",
    ),
}


def md_table(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for row in df.itertuples(index=False):
        lines.append("| " + " | ".join(str(v) for v in row) + " |")
    return "\n".join(lines)


def main() -> None:
    con = connect()
    con.execute((ROOT / "sql" / "reviews_clean.sql").read_text())

    overview = con.sql("""
        SELECT app, count(*) AS reviews,
               strftime(min(review_date), '%Y-%m-%d') AS first_day, strftime(max(review_date), '%Y-%m-%d') AS last_day,
               round(avg(rating), 2) AS avg_rating,
               round(100 * avg(has_devanagari::INT), 1) AS pct_devanagari,
               round(100 * avg(has_reply::INT), 1) AS pct_dev_reply,
               count(DISTINCT app_version) AS versions
        FROM reviews_clean GROUP BY app ORDER BY reviews DESC
    """).df()

    flags = list(DECISIONS)
    by_app = con.sql(f"""
        SELECT app, count(*) AS n, {", ".join(f"sum({f}::INT) AS {f}" for f in flags)}
        FROM reviews_clean GROUP BY app ORDER BY n DESC
    """).df()
    total = by_app[["n", *flags]].sum()

    issues = pd.DataFrame([{
        "Issue": DECISIONS[f][0],
        "Rows": f"{int(total[f]):,}",
        "Share": f"{100 * total[f] / total['n']:.1f}%",
        "Decision": DECISIONS[f][1],
        "Reason": DECISIONS[f][2],
    } for f in flags])

    flag_pct = by_app[["app"]].copy()
    for f in flags:
        flag_pct[f] = (100 * by_app[f] / by_app["n"]).round(1).astype(str) + "%"

    examples = {
        f: con.sql(f"""
            SELECT app, rating, left(regexp_replace(text, '[\\r\\n|]+', ' ', 'g'), 90) AS text
            FROM reviews_clean WHERE {f} ORDER BY hash(review_id) LIMIT 6
        """).df()
        for f in ["is_repeated_text", "has_link", "star_text_mismatch"]
    }

    # Days far below an app's normal volume point to a collection gap rather than real silence.
    gaps = con.sql("""
        WITH days AS (
            SELECT app, unnest(generate_series(min(review_date), max(review_date), INTERVAL 1 DAY))::DATE AS d
            FROM reviews_clean GROUP BY app
        ), counts AS (SELECT app, review_date AS d, count(*) AS n FROM reviews_clean GROUP BY ALL),
        daily AS (SELECT days.app, days.d, coalesce(counts.n, 0) AS n FROM days LEFT JOIN counts USING (app, d)),
        med AS (SELECT app, median(n) AS m FROM daily GROUP BY app)
        SELECT app, round(m) AS median_per_day,
               count(*) FILTER (WHERE n = 0) AS zero_days,
               count(*) FILTER (WHERE n < 0.2 * m) AS low_days,
               coalesce(strftime(max(d) FILTER (WHERE n < 0.2 * m), '%Y-%m-%d'), '–') AS last_low_day
        FROM daily JOIN med USING (app) GROUP BY app, m ORDER BY app
    """).df()

    # Play Store serves only a skewed subset of older reviews; see "Oldest reviews" in the report.
    cutoff = con.sql("""
        SELECT app,
               CASE WHEN review_date < DATE '2026-05-06' THEN 'before May 6' ELSE 'May 6 on' END AS period,
               round(count(*) / count(DISTINCT review_date)) AS reviews_per_day,
               round(avg(rating), 2) AS avg_rating,
               round(avg(n_words), 1) AS avg_words,
               round(100 * avg(is_very_short::INT), 1) AS pct_very_short
        FROM reviews_clean
        WHERE review_date < DATE '2026-05-06' + 14
        GROUP BY ALL ORDER BY app, period
    """).df()

    usable = con.sql("""
        SELECT count(*) FILTER (WHERE NOT (is_repeated_text OR has_link)) AS for_ratings,
               count(*) FILTER (WHERE NOT (is_repeated_text OR has_link OR is_empty_or_symbols)) AS for_themes,
               count(*) AS total
        FROM reviews_clean
    """).fetchone()

    masked = con.sql("""
        SELECT count(*) FILTER (WHERE text LIKE '%[phone]%') AS phones,
               count(*) FILTER (WHERE text LIKE '%[email]%') AS emails
        FROM reviews_clean
    """).fetchone()

    runs = pd.read_csv(RUN_LOG) if RUN_LOG.exists() else pd.DataFrame()

    parts = [
        "# Data-quality report",
        f"_Generated {date.today().isoformat()} by `uv run python -m qpulse.quality`. Do not edit numbers by hand._",
        "## Overview",
        md_table(overview),
        f"\n**Usable rows:** {usable[0]:,} of {usable[2]:,} for rating metrics; "
        f"{usable[1]:,} for theme metrics.",
        "## Issues and decisions",
        md_table(issues),
        "\nDuplicates by review ID are removed at collection time (the same review can come back from both the "
        "`en` and `hi` queries, and edited reviews keep their ID; the newest version is kept).",
        "### Share of each issue by app",
        md_table(flag_pct),
        "## Privacy",
        "Reviewer names and profile images are never written to disk. Phone numbers and email addresses in review "
        f"text are masked at collection: {masked[0]:,} phone numbers and {masked[1]:,} emails masked so far.",
        "## Daily volume and gaps",
        md_table(gaps),
        "\nA *low day* has under 20% of the app's median daily reviews. A run of low days means a collection gap "
        "(see the run log), not customers going quiet.",
        "## Oldest reviews: a skewed subset before May 6",
        "On May 6 2026 volume and rating step up on the same day in all four apps. Before it, reviews are fewer, "
        "longer and much more negative (table: all days before May 6 vs the 14 days after). Four competitors "
        "don't change together overnight, so this is the source: the Play Store serves only part of the reviews "
        "older than ~5.5 months (May 6 was 167 days before the backfill on Oct 20), and short positive ones drop "
        "out. **Decision:** keep the rows, but metrics start at the first full week after it "
        "(`METRICS_START = 2026-05-11` in `config.py`).",
        md_table(cutoff),
    ]
    for f, ex in examples.items():
        parts += [f"### Examples: {DECISIONS[f][0]}", md_table(ex) if len(ex) else "_none_"]
    if len(runs):
        ok = (runs["status"] == "ok").mean()
        parts += ["## Collection runs", f"{len(runs)} app-runs logged, {100 * ok:.0f}% succeeded.",
                  md_table(runs.tail(8)[["run_at", "app", "mode", "fetched", "new_reviews", "seconds", "status"]])]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n\n".join(parts) + "\n")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
