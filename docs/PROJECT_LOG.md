# Project log

A record of every piece of work done on this project, newest entry at the bottom.
Each entry lists what was done, what came out of it, and the decisions and failures along the way.

Automatic daily collection runs aren't listed here; they're in `run_log.csv` in the
[`data` release](https://github.com/divyabasavraj/qcommerce-pulse/releases/tag/data) and in GitHub Actions.

## Status

| # | Milestone | Plan | Status |
|---|---|---|---|
| 1 | Collector + 6-month backfill | 0.5 day | ✅ Done 2026-10-20 |
| 2 | Data-quality report | 0.5 day | ✅ Done 2026-10-20 |
| 3 | Theme labelling | 1 day | 🟡 LLM labelled 3,300 reviews; waiting on 300 hand labels + accuracy check |
| 4 | Fast classifier | 0.5 day | ⬜ |
| 5 | SQL metrics + expected-range alerts | 1 day | 🟡 Rating/volume metrics + alerts done; theme shares wired, need the classifier (M4) |
| 6 | Weekly report | 0.5 day | ⬜ |
| 7 | Monthly memo + Diwali deep-dive | 1 day | ⬜ Diwali analysis needs data from after Nov 8 |
| 8 | Dashboard | 0.5 day | ⬜ |
| 9 | Ship | 0.5 day | ⬜ |

**Open decisions (from PLAN.md §17):**
- [x] Swiggy Instamart app ID → standalone app `in.swiggy.android.instamart` (2026-10-20)
- [ ] Number of hand labels (300 drawn; confirm after labelling)
- [x] Alert sensitivity → k = 2.5 × SD of an 8-week baseline, min 200 reviews/week (2026-10-20; re-check with theme metrics)
- [ ] Dashboard: Streamlit vs Looker Studio

---

## 2026-10-20: Project setup, Milestones 1–2, Milestone 3 tooling

### Work done
- **Setup:** `uv` project (`qpulse`, Python 3.12), dependencies `google-play-scraper`, `duckdb`, `pandas`, `pyarrow`, `requests`; local git repo.
- **Verified app IDs** on the Play Store for all four apps (see decisions).
- **Measured review volume** per app from a 1,000-review sample to size the backfill.
- **Collector** `src/qpulse/collect.py` + `config.py`: newest-first pagination, `en` + `hi`, PII drop/mask, dedupe by review ID, monthly Parquet files, run log (`data/run_log.csv`), `--backfill` and `--apps` options.
- **DuckDB view** `src/qpulse/db.py`: `reviews` view over the Parquet files.
- **6-month backfill**, run twice (first run silently truncated; see failures). Final: **370,006 reviews, Apr 20 – Oct 19 2026** (Blinkit 251,378 · Zepto 42,070 · BigBasket 38,457 · Instamart 38,101).
- **Daily GitHub Actions workflow** `.github/workflows/daily.yml`: 07:00 IST cron, downloads the Parquet files from the `data` release, collects, uploads them back.
- **Data-quality layer:** `sql/reviews_clean.sql` (flags: empty/symbols, very short, repeated text, link, star/text mismatch, missing version) and `src/qpulse/quality.py` → `docs/DATA_QUALITY.md` (counts, shares by app, decisions, reasons, examples, daily-volume gap check, privacy counts, run summary).
- **Theme taxonomy v1** `src/qpulse/themes.py` (10 themes, multi-label).
- **LLM labeller** `src/qpulse/llm_label.py`: Ollama `qwen2.5:7b`, JSON output restricted to the theme list, per-review cache so runs resume. Smoke-tested on 5 examples.
- **Label sets** `src/qpulse/sample.py`: 300-review hand-label test set and 3,000-review LLM training set, no overlap, stratified by app and rating.
- **Hand-labelling tool** `src/qpulse/hand_label.py` (terminal; saves after every review; back / note / quit).
- **Evaluation script** `src/qpulse/evaluate.py` → `docs/LABEL_EVAL.md` (per-theme precision/recall/F1, macro-F1, disagreements).
- **Published:** public repo https://github.com/divyabasavraj/qcommerce-pulse (commit `d4e26ca`), `data` release with the 7 monthly Parquet files (34 MB) and run log, README.
- **Verified CI:** manual run of the daily workflow [succeeded](https://github.com/divyabasavraj/qcommerce-pulse/actions/runs/39405535055) and collected 106 new reviews.

### Decisions
**Swiggy Instamart app ID (open decision closed).** Instamart has a standalone Play Store app,
`in.swiggy.android.instamart` (50M+ installs, ~127k ratings). Using it instead of filtering Instamart
reviews out of the main Swiggy food app avoids a keyword filter that would have mislabelled reviews.

**All four package IDs verified** against the Play Store: Blinkit `com.grofers.customerapp`,
Zepto `com.zeptoconsumerapp`, BigBasket `com.bigbasket.mobileapp`, Instamart `in.swiggy.android.instamart`.

**Review volume is very uneven.** Blinkit gets ~1,000–1,400 reviews/day; the other three get ~180–240/day.
All metrics must be shares within an app, never raw counts across apps, and alerts need a minimum count.

**Languages.** The scraper filters reviews by language. Pulling both `en` and `hi` and de-duplicating by review ID
covers English, Devanagari Hindi and Hinglish (Latin script, which Play tags as `en`). Only ~0.5% of reviews contain Devanagari.

**Privacy.** Reviewer name and avatar are dropped before anything is written. Phone numbers and emails inside
review text are masked. Developer reply text isn't stored, only whether there was a reply and when.

**Storage.** Monthly Parquet files (`data/raw/reviews_YYYY-MM.parquet`), kept in a GitHub release named `data`
rather than in git, so the repo stays small. DuckDB reads them through a view. Daily runs re-read 2 days before
the newest stored review to catch late-indexed reviews; edited reviews keep their ID and the newest version wins.
The backfill was uploaded to the release before the first CI run, because a cold CI run would have to re-scrape
6 months, and that would exceed the job's 30-minute timeout (Blinkit alone took ~24 minutes locally).

**Labelling model.** No Gemini key on this machine, so the plan's fallback is used: local `qwen2.5:7b` via Ollama,
temperature 0, JSON output restricted to the theme list. Smoke test: ~0.5 s/review, correct on simple
English and Hinglish examples. Real accuracy comes from the hand-label comparison, not the smoke test.
The 3,000-review run (~30 min of GPU) is on hold because the laptop was running hot; option to use `qwen2.5:3b`.

**Label sets.** The test and training sets are stratified by app (equal per app) and rating (55% 1–2★, 15% 3★, 30% 4–5★)
so rare complaint themes get enough examples. That makes theme shares inside these sets non-representative.
That's fine for per-theme F1 but they must never be reported as population shares.
The first draw gave 296 instead of 300 (each bucket rounded down); fixed so the last bucket absorbs rounding,
and redrawn before any labelling started. The test set is never redrawn once labelling begins.

**Repo is public**: a portfolio project, and public repos get unlimited Actions minutes. The review data in the
release is public Play Store content with reviewer identity removed.

### Failures and fixes
**Silent truncation in the first backfill.** The run log said `ok` for all four apps, but Blinkit's English
reviews started on Jul 1 and Zepto's on Sep 2 instead of Apr 20 (Zepto stopped at exactly 9,600 = 48 pages × 200).
Cause: when throttled, `google-play-scraper` returns an empty page instead of raising, and the loop read an empty
page as "no more reviews". Re-running the same pagination by hand went straight past the cutoff.
Fix: empty pages are retried with backoff, and a fetch that stops before its start date raises `IncompleteFetch`,
is logged as `incomplete`, and fails the CI job. Re-ran the backfill for the two affected apps.
Caught by the data-quality report's daily-volume check (Zepto: 77 zero-review days), which was then strengthened
to count *low* days (<20% of the app's median), because Blinkit's gap was hidden by the small Hindi stream
filling in a few reviews a day. **Lesson: a run log saying `ok` isn't evidence of completeness; check coverage.**

**Data-quality rules changed after reading examples.**
- v1 of the spam/link flag matched the word "WhatsApp". Reading flagged rows showed most were customers reporting
  scam WhatsApp messages: real complaints. v2 flags only URLs and t.me / wa.me links (0 rows; the Play Store appears
  to strip URLs). The rule stays as a guard.
- Repeated-text "spam" turned out to be one BigBasket delivery partner's name praised repeatedly
  ("excellent <name> on time delivery"): partners soliciting 5★ reviews. Excluded from metrics.
- 52% of reviews are ≤2 words. Kept, because dropping them would inflate complaint shares.
- Report bugs fixed: example tables were empty (DuckDB `USING SAMPLE` runs before `WHERE`), and dates printed with `00:00:00`.

**Instamart low days checked.** Instamart's 6 "low days" (Apr 25 – May 2) dip smoothly to ~30/day and recover
by May 6, never zero. That's a real lull, not a collection cut. **Wrong — corrected in Milestone 5 below:** it's
a Play Store artifact affecting all four apps before May 6.

### LLM labelling run (later the same day)
- Labelled the 300-review hand set (~3 min) and the 3,000-review training set (~45 min) with `qwen2.5:7b`.
  0 failures/skips. Output: `data/labels/llm_labels_qwen2.5-7b.csv` (3,300 rows).
- Speed fell from ~1.2 to ~0.8 reviews/s midway (likely thermal throttling on the laptop) and recovered to ~1.1/s.
- Training-set theme counts (stratified sample, not population shares): positive 1,027 · refund_support 591 ·
  other 425 · delivery_delay 319 · pricing_fees 319 · quality_expiry 278 · app_payment_bug 231 ·
  missing_wrong_item 218 · partner_behaviour 159 · availability_stock 114. Every theme has ≥100 examples.
- Sanity check on the hand set: `positive` was applied to only 2 of 164 reviews rated 1–2★, both genuinely positive text;
  the extra positives come from mixed 3★ reviews. 16% of reviews got more than one theme.
- The model was unloaded from Ollama after the run to let the laptop cool.

### Next
- **Divya:** hand-label the 300 reviews (`uv run python -m qpulse.hand_label`, ~1–1.5 h); note any missing theme.
- Then `uv run python -m qpulse.evaluate data/labels/llm_labels_qwen2.5-7b.csv` → LLM accuracy vs hand labels; refine taxonomy.
- Milestone 5 (SQL metrics + alerts) can start in parallel; it doesn't need the labels.

### Milestone 5: SQL metrics and expected-range alerts (evening)

#### Work done
- **Found a source artifact before building any metric.** Weekly ratings for the first two backfill weeks were far
  below normal in *every* app (Zepto 1.5★ vs ~3.3★, BigBasket 1.7★ vs ~4.1★). By day, volume and rating step up
  together on **May 6 2026 in all four apps**; before that, reviews are ~⅓ the volume, ~2× as long and much more
  negative (Zepto 1.8★ vs 3.2★, 13% vs 35% very short). Same in `en` and `hi`. Four competitors don't change
  overnight on the same day, so it's the source: the Play Store serves only a skewed subset of reviews older than
  ~5.5 months (167 days before the backfill). Added a computed before/after table and decision to
  `docs/DATA_QUALITY.md` (section "Oldest reviews"), via `src/qpulse/quality.py`.
- `src/qpulse/config.py`: `METRICS_START = 2026-05-11` (first full week after the cutoff), `BASELINE_WEEKS = 8`,
  `ALERT_K = 2.5`, `ALERT_MIN_N = 200`.
- `sql/weekly_metrics.sql`: `metric_reviews` (excludes repeated-text and link reviews, full Mon–Sun weeks only) and
  `weekly_metrics` in long form `(app, week, metric, kind, denom, value, se)`: review count, avg rating, 1★ share.
  23 full weeks × 4 apps (May 11 – Oct 12).
- `sql/weekly_theme_metrics.sql`: theme shares per app-week from a `review_themes(review_id, theme)` table;
  denominator = reviews with text. Ready for the classifier's output.
- `sql/alerts.sql`: expected range = mean of the previous 8 weeks ± k × max(their SD, sampling error);
  alert needs a full 8-week baseline and ≥200 reviews. Reports direction and z.
- `src/qpulse/metrics.py`: sets the SQL variables, unions metric views, labels alerts worse / better / change
  (volume has no good direction). `--calibrate` writes `docs/ALERT_CALIBRATION.md`; `--themes FILE` adds theme
  shares from a wide 0/1 label CSV.
- **Cross-checked the SQL against an independent pandas rebuild from raw reviews:** same 92 app-weeks, review counts,
  avg ratings and 1★ shares identical; 8-week baseline mean/SD match to 1e-16. Theme share for one app-week matched
  a hand count (1 of 1,536).
- **Backtest (15 scored weeks, 12 series):** k = 2 → 27 alerts (1.8/week, 15% of metric-weeks); k = 2.5 → 12 (0.8/week);
  k = 3 → 3 (0.2/week). Latest full week (Oct 12): 0 alerts.

#### Decisions
**Metrics start May 11, rows kept.** The pre-May-6 rows are real reviews but not a fair sample, so they'd make the
first baseline look like a crisis. Kept on disk (useful for long-review text analysis), excluded from metrics.

**k = 2.5 (open decision closed, provisionally).** At k = 2, 15% of metric-weeks flag, three times what normal
noise would give, because an SD from only 8 values is itself noisy. At k = 3 only 3 alerts in 15 weeks, and it
misses events that look real when read: Blinkit's rating improving two weeks running (Sep 28, Oct 5) flagged by
*both* avg rating and 1★ share, and BigBasket's 1★ share jumping to 19.6% (Aug 10). Re-check when ~40 theme
series are added; that's roughly 4× the alerts.

**Developer-reply rate is not a weekly metric.** `has_reply` is the state when the review was collected and the
collector never re-reads old reviews, so recent weeks always look under-replied. Belongs in the reply deep-dive
(month 3), which will need re-collection.

**Long-form metric table.** Every metric (rating, volume, each theme) is a row, so one alert query covers them all
and adding themes needs no change to `alerts.sql`.

#### Failures and fixes
- **Earlier conclusion was wrong:** the Instamart "real lull" (Apr 25 – May 2) is this source artifact. It was
  checked one app at a time; comparing all four apps by day is what showed it. **Lesson: when one app looks odd,
  check whether the others moved on the same day before calling it real.**
- Volume alerts were labelled "better": pandas turns the missing good/bad direction into NaN, so `is None` never
  matched. Caught while reading the cross-check output; fixed with `pd.isna`.
- A theme share of exactly 0 had a sampling error of 0, so a rare theme could alert on almost nothing (seen in a
  smoke test with the sampled LLM labels). For shares the floor now uses the baseline share.
- The noise table applied the share error formula to review counts (sqrt of a negative number → DuckDB error).
  Now computed per metric kind.

#### Next
- **Divya:** hand-label the 300 reviews (`uv run python -m qpulse.hand_label`), then run `qpulse.evaluate`.
- Milestone 4 (classifier) → write its output as `review_themes`, re-run `--calibrate` with themes, re-check k.
- Milestone 6 adds version watch (rating / bug-theme share by app version) and the competitor view on top of
  `all_metrics`.

