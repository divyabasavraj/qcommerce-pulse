"""One-off repair (2026-10-28): convert review times collected by CI before the IST fix from UTC to IST.

The scraper returned machine-local times: the laptop backfill (2026-10-20, before 10:00 UTC) stored IST, the
GitHub Actions runs from 2026-10-20 10:06 UTC until the fix (commit a03a2d7, pushed 2026-10-28 06:28:27 UTC)
stored UTC. Those rows get +5:30 on review_at and replied_at, then all rows are re-split into monthly files.
Also removes old copies of edited reviews: an edit keeps the review ID but moves its date, and the collector
deduplicated only within a month file (fixed in collect.save the same day). The newest version is kept.

uv run python scripts/fix_review_timezone_2026_10.py DIR    # DIR holds reviews_*.parquet; files rewritten in place
"""
import sys
from pathlib import Path

import pandas as pd

FIRST_CI = pd.Timestamp("2026-10-20 10:00:00")
FIX_PUSHED = pd.Timestamp("2026-10-28 06:28:27")
SHIFT = pd.Timedelta(hours=5, minutes=30)

root = Path(sys.argv[1])
files = sorted(root.glob("reviews_*.parquet"))
df = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
ids0 = set(df["review_id"])

ci = (df["collected_at"] >= FIRST_CI) & (df["collected_at"] < FIX_PUSHED)
df.loc[ci, "review_at"] += SHIFT
df.loc[ci & df["replied_at"].notna(), "replied_at"] += SHIFT
print(f"{len(df):,} reviews; shifted {ci.sum():,} collected by CI between {FIRST_CI} and {FIX_PUSHED} UTC")

before = len(df)
df = df.sort_values(["review_at", "collected_at"]).drop_duplicates("review_id", keep="last")
print(f"dropped {before - len(df)} old copies of edited reviews")
month = df["review_at"].dt.strftime("%Y-%m")
for f in files:
    f.unlink()
for m, part in df.groupby(month):
    part.sort_values("review_at").to_parquet(root / f"reviews_{m}.parquet", index=False)

check = pd.concat([pd.read_parquet(f) for f in sorted(root.glob("reviews_*.parquet"))], ignore_index=True)
assert set(check["review_id"]) == ids0 and check["review_id"].is_unique and len(check) == len(ids0)
print("files:", ", ".join(f.name for f in sorted(root.glob("reviews_*.parquet"))), f"- {len(check):,} reviews, IDs unchanged")
