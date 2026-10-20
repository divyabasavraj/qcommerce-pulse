# Q-Commerce Pulse

A live customer-feedback monitor for India's quick-commerce apps: Blinkit, Zepto, BigBasket and Swiggy Instamart.
New Play Store reviews are collected every day. Every week the CX team gets an action list, and every month
a decision memo with a new deep-dive.

> 🚧 **In progress.** Milestones 1–2 are done (daily collector, 6-month backfill of 370k reviews, data-quality report).
> Theme labelling is underway. See [PLAN.md](PLAN.md) for the full design.

## Run it
```bash
uv sync
uv run python -m qpulse.collect            # daily incremental collection (CI runs this at 07:00 IST)
uv run python -m qpulse.collect --backfill # pull the last 6 months
uv run python -m qpulse.quality            # -> docs/DATA_QUALITY.md
```
Review data is kept as monthly Parquet files in this repo's [`data` release](../../releases/tag/data), not in git.

## Docs
- [Data-quality report](docs/DATA_QUALITY.md): every issue, with a decision and a reason
- [Project log](docs/PROJECT_LOG.md): decisions and failures, including a silent-truncation bug caught by the coverage check

## Privacy
Only public reviews are collected. Reviewer names and profile images are never stored,
and phone numbers and emails inside review text are masked.
