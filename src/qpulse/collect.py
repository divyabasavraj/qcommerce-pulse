"""Collect Play Store reviews for the four apps.

Backfill:  uv run python -m qpulse.collect --backfill
Daily:     uv run python -m qpulse.collect

Reviewer identity (name, avatar) is dropped at fetch time and never written to disk.
Phone numbers and email addresses inside review text are masked.
"""
import argparse
import re
import time
from datetime import datetime, timedelta, timezone

import pandas as pd
from google_play_scraper import Sort, reviews

from qpulse.config import APPS, BACKFILL_DAYS, COUNTRY, LANGS, OVERLAP_DAYS, RAW_DIR, RUN_LOG

PAGE = 200
COLUMNS = [
    "review_id", "app", "rating", "text", "review_at", "app_version",
    "thumbs_up", "has_reply", "replied_at", "lang_query", "collected_at",
]

PHONE_RE = re.compile(r"(?<!\d)(?:\+?91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}(?!\d)")
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
# Review times are stored as naive IST. The scraper converts with datetime.fromtimestamp, i.e. the machine's
# local time (IST on a laptop, UTC on GitHub Actions), so convert explicitly. collected_at stays naive UTC.
IST = timezone(timedelta(hours=5, minutes=30))


def to_ist(dt: datetime | None) -> datetime | None:
    return None if dt is None else dt.astimezone(IST).replace(tzinfo=None)


def mask_pii(text: str | None) -> str:
    if not text:
        return ""
    text = EMAIL_RE.sub("[email]", text)
    return PHONE_RE.sub("[phone]", text)


def to_row(r: dict, app: str, lang: str, collected_at: datetime) -> dict:
    return {
        "review_id": r["reviewId"],
        "app": app,
        "rating": int(r["score"]),
        "text": mask_pii(r["content"]),
        "review_at": r["at"],
        "app_version": r.get("reviewCreatedVersion") or r.get("appVersion"),
        "thumbs_up": int(r.get("thumbsUpCount") or 0),
        "has_reply": r.get("replyContent") is not None,
        "replied_at": r.get("repliedAt"),
        "lang_query": lang,
        "collected_at": collected_at,
    }


class IncompleteFetch(Exception):
    pass


def fetch_since(app: str, package: str, lang: str, since: datetime, collected_at: datetime) -> list[dict]:
    """Page through newest-first reviews until we pass `since`.

    When throttled, the scraper returns an empty page instead of raising, which looks the same as
    "no more reviews". Empty pages are retried; if we still haven't reached `since`, raise so the
    run is logged as incomplete rather than silently truncated.
    """
    rows, token, oldest = [], None, None
    while True:
        batch, next_token = [], token
        for attempt in range(5):
            try:
                batch, next_token = reviews(
                    package, lang=lang, country=COUNTRY, sort=Sort.NEWEST,
                    count=PAGE, continuation_token=token,
                )
            except Exception:
                if attempt == 4:
                    raise
            if batch:
                break
            time.sleep(10 * (attempt + 1))
        if not batch:
            # Still empty after retries. Fine on the first page (no reviews at all), truncation otherwise.
            if oldest is not None:
                raise IncompleteFetch(f"{lang}: stopped at {oldest:%Y-%m-%d} before reaching {since:%Y-%m-%d}")
            break
        token = next_token
        for r in batch:
            r["at"], r["repliedAt"] = to_ist(r["at"]), to_ist(r.get("repliedAt"))
        oldest = batch[-1]["at"]
        rows += [to_row(r, app, lang, collected_at) for r in batch if r["at"] >= since]
        if oldest < since or token is None or token.token is None:
            break
        time.sleep(0.3)
    return rows


def load_existing() -> pd.DataFrame:
    files = sorted(RAW_DIR.glob("reviews_*.parquet"))
    if not files:
        return pd.DataFrame(columns=COLUMNS)
    return pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)


def save(df: pd.DataFrame) -> None:
    """Rewrite the monthly Parquet files touched by `df`, merging with what's already stored."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    df = df.assign(month=pd.to_datetime(df["review_at"]).dt.strftime("%Y-%m"))
    for month, part in df.groupby("month"):
        path = RAW_DIR / f"reviews_{month}.parquet"
        part = part.drop(columns="month")
        if path.exists():
            part = pd.concat([pd.read_parquet(path), part], ignore_index=True)
        # An edited review keeps its ID; keep the newest version.
        part = (part.sort_values(["review_at", "collected_at"])
                    .drop_duplicates("review_id", keep="last")
                    .sort_values("review_at")[COLUMNS])
        part.to_parquet(path, index=False)


def log_run(rows: list[dict]) -> None:
    RUN_LOG.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(RUN_LOG, mode="a", header=not RUN_LOG.exists(), index=False)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backfill", action="store_true", help=f"pull the last {BACKFILL_DAYS} days")
    parser.add_argument("--apps", nargs="+", choices=list(APPS), default=list(APPS))
    args = parser.parse_args()

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    now_ist = datetime.now(IST).replace(tzinfo=None)
    existing = load_existing()
    run_rows, new_frames, failed = [], [], []

    for app in args.apps:
        package = APPS[app]
        if args.backfill or existing.empty or app not in set(existing["app"]):
            since = now_ist - timedelta(days=BACKFILL_DAYS)
        else:
            newest = pd.to_datetime(existing.loc[existing["app"] == app, "review_at"]).max()
            since = newest.to_pydatetime() - timedelta(days=OVERLAP_DAYS)

        started = time.time()
        try:
            rows = [r for lang in LANGS for r in fetch_since(app, package, lang, since, now)]
            status, error = "ok", ""
        except IncompleteFetch as e:
            rows, status, error = [], "incomplete", str(e)
            failed.append(app)
        except Exception as e:
            rows, status, error = [], "failed", f"{type(e).__name__}: {e}"[:300]
            failed.append(app)

        fetched = pd.DataFrame(rows, columns=COLUMNS)
        known = set(existing.loc[existing["app"] == app, "review_id"])
        n_new = fetched["review_id"].nunique() - len(known & set(fetched["review_id"]))
        new_frames.append(fetched)
        run_rows.append({
            "run_at": now.isoformat(timespec="seconds"), "app": app, "mode": "backfill" if args.backfill else "daily",
            "since": since.isoformat(timespec="seconds"), "fetched": len(fetched), "new_reviews": n_new,
            "seconds": round(time.time() - started, 1), "status": status, "error": error,
        })
        print(f"{app:10s} {status:6s} fetched={len(fetched):6d} new={n_new:6d}")

    combined = pd.concat([f for f in new_frames if not f.empty], ignore_index=True) if any(
        not f.empty for f in new_frames) else pd.DataFrame(columns=COLUMNS)
    if not combined.empty:
        save(combined)
    log_run(run_rows)
    if failed:
        raise SystemExit(f"collection failed for: {', '.join(failed)}")


if __name__ == "__main__":
    main()
