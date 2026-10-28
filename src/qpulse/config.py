from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
RAW_DIR = DATA / "raw"          # monthly Parquet files: reviews_YYYY-MM.parquet
RUN_LOG = DATA / "run_log.csv"  # one row per app per collection run
DB_PATH = DATA / "qpulse.duckdb"

# Package IDs verified against the Play Store on 2026-10-20.
# Swiggy Instamart has its own app, so the main Swiggy (food) app is not used.
APPS = {
    "blinkit": "com.grofers.customerapp",
    "zepto": "com.zeptoconsumerapp",
    "bigbasket": "com.bigbasket.mobileapp",
    "instamart": "in.swiggy.android.instamart",
}

APP_NAMES = {"blinkit": "Blinkit", "zepto": "Zepto", "instamart": "Instamart", "bigbasket": "BigBasket"}

# Play Store review language filters. Hinglish is mostly Latin script and arrives under "en".
LANGS = ["en", "hi"]
COUNTRY = "in"

BACKFILL_DAYS = 183
# Daily runs re-read this many days before the newest stored review, to catch late-indexed reviews.
OVERLAP_DAYS = 2

# First full week used for metrics. Before May 6 2026 the Play Store served only a skewed subset of
# reviews (fewer, longer, far more negative, all four apps at once): ~167 days back from the backfill.
METRICS_START = "2026-05-11"
# Expected-range alerts: baseline weeks, range width in standard deviations, minimum reviews in the week.
# Width and minimum chosen from the backtest in docs/ALERT_CALIBRATION.md.
BASELINE_WEEKS = 8
ALERT_K = 3.0
ALERT_MIN_N = 200
# Version watch: a version needs this many reviews with text in the week to be judged.
VERSION_MIN_N = 100

# Weekly report text: small local model so it can run in CI (Ollama on the GitHub runner).
REPORT_MODEL = "qwen2.5:3b"
