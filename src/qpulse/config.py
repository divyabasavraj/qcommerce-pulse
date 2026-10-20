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

# Play Store review language filters. Hinglish is mostly Latin script and arrives under "en".
LANGS = ["en", "hi"]
COUNTRY = "in"

BACKFILL_DAYS = 183
# Daily runs re-read this many days before the newest stored review, to catch late-indexed reviews.
OVERLAP_DAYS = 2
