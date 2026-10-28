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
| 3 | Theme labelling | 1 day | 🟡 LLM labelled 3,300 reviews; hand labels 300/300 (27 corrected after review); LLM prompt v2: macro-F1 0.60, exact 70% on held-out hand labels 101–300 (v1: 0.59, 66%) |
| 4 | Fast classifier | 0.5 day | ✅ Done 2026-10-28: TF-IDF + logistic regression, held-out macro-F1 0.59 (LLM 0.60), all 370k reviews in 10 s; running in the daily job |
| 5 | SQL metrics + expected-range alerts | 1 day | ✅ Done 2026-10-28: rating, volume and theme-share metrics; alerts at k = 3 (0.7/week in backtest) |
| 6 | Weekly report | 0.5 day | ⬜ |
| 7 | Monthly memo + Diwali deep-dive | 1 day | ⬜ Diwali analysis needs data from after Nov 8 |
| 8 | Dashboard | 0.5 day | ⬜ |
| 9 | Ship | 0.5 day | ⬜ |

**Open decisions (from PLAN.md §17):**
- [x] Swiggy Instamart app ID → standalone app `in.swiggy.android.instamart` (2026-10-20)
- [x] Number of hand labels → 300, all labelled by hand (2026-10-24)
- [x] Alert sensitivity → k = 3 × SD of an 8-week baseline, min 200 reviews/week (2026-10-28, with theme metrics; was 2.5 from 2026-10-20)
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

## 2026-10-21: Hand labelling restarted

### Work done
- **Checked the first 101 hand labels** (`data/labels/hand_labels.csv`, done 2026-10-20). No blanks or gaps, but most
  labels don't match their review text: "very good" → refund_support, "nice" → availability_stock, "great" →
  pricing_fees, "6 minutes bol ke 47 minutes me delivery" → pricing_fees. Only 2 of 101 were tagged delivery_delay.
- **Set the file aside** as `data/labels/hand_labels_discarded_2026-10-20.csv` (kept, not deleted). Labelling
  restarts at 0/300.
- **`src/qpulse/hand_label.py`:** now prints `saved: <themes>` after every review so a wrong entry is visible at
  once; new `--review [N]` mode walks back through saved labels (Enter keeps, numbers replace).

### Decisions
**Label fully by hand, no suggestions.** Divya chose this over the model-assisted plan from 2026-10-20: the
"accuracy vs hand labels" number is only meaningful if the labels are independent of any model.

**Discard rather than repair the 101.** Tested whether the labels were shifted by one or two reviews (overlap with
the LLM labels at shifts -2…+2 was 8–13%, flat), so no offset explains it and it can't be fixed automatically.

### Failures and fixes
- **Labels drifted from the reviews they belonged to.** Divya remembered pressing Enter on some reviews without a
  theme. The tool rejects empty input and re-shows the same review, so if the screen wasn't watched the next
  numbers could go to a review other than the one being read. The tool gave no confirmation of what was saved, so
  nothing showed the drift. Caught by reading labels next to the text. Fix: the `saved:` echo after each review.
  **Lesson: a labelling tool should always echo what it saved; spot-check the first 10 labels before doing the rest.**

- **Second attempt also discarded.** A spot-check after 14 labels showed the same mismatch ("very good" →
  app_payment_bug, "Very bad system of cancellation" → positive). Divya said the numbers were being picked freely
  rather than from the text. Set aside as `data/labels/hand_labels_discarded_2026-10-21.csv`; restarted at 0/300
  with Divya reading each review. **Lesson: the spot-check after the first 10–15 labels is what caught this; keep it.**

- **Third attempt: 30/300 labelled, read from the text.** Spot-check: labels now follow the reviews ("6 minutes bol
  ke 47 minutes" → delivery_delay, "no offers" → pricing_fees, expired face wash → quality_expiry). A few clashed with
  the theme definitions and were flagged for Divya to decide on: #1 app not starting → missing_wrong_item, #5 not
  available in village → missing_wrong_item, #10 poor customer service → partner_behaviour, #11 "good 👍" → other,
  #25 praise for a delivery partner → partner_behaviour (a complaint theme), #28 surcharge + late → delay only.

- **100/300 labelled.** Spot-check of 31–100: labels follow the text. Counts so far: positive 30, delivery_delay 24,
  refund_support 19, pricing_fees 15, other 15, quality_expiry 10, missing_wrong_item 5, partner_behaviour 5,
  availability_stock 2, app_payment_bug 1. Flagged for Divya: #81 has 8 of 10 themes ticked (likely typed 1–8),
  #34 "can't deliver in my place" → delay (definition says availability), #52 "best app" → other, #54 "charge more
  than MRP" → refund only, #66 coupon praise → pricing only. The six flagged at 30 were not changed yet.

- **11 of the 100 labels corrected after review.** Divya went through Claude's flags and approved all 11 changes
  (#1, 5, 10, 11, 25, 28, 34, 52, 54, 66, 81); Claude applied them. Each changed row says so in its `note`
  column, with the old label. Report as "100 hand labels, 11 corrected after a review pass" in the README.

### Next
- **Open choice for reviews 101–300 (decide 2026-10-22):** continue fully by hand; Claude suggests + Divya
  confirms (logged per row and disclosed); or stop at 100 and report wider error bars. Claude will not write
  labels into `hand_labels.csv` itself.
- **Divya:** continue at ~30+/day
  (`uv run python -m qpulse.hand_label`), spot-check each batch, then run `qpulse.evaluate`.


## 2026-10-24: Hand labels 300/300

### Work done
- **Divya labelled reviews 101–300 by hand** in `src/qpulse/hand_label.py`. Committed as-is first (`f56f87a`) so
  the history keeps the unreviewed labels.
- **Checks on `data/labels/hand_labels.csv`:** 300 rows, 300 unique IDs matching `hand_label_set.csv`, no row
  without a theme, only 0/1 values, first 100 identical to the committed version. `positive` is on 97% of 5★
  and 4% of 1★ reviews.
- **Flagged 16 of reviews 101–300** for Divya: 13 had `other` ticked alongside other themes, and a scan of
  short reviews (≤4 words) found vague text given specific themes. Common pattern: `delivery_delay +
  missing_wrong_item` on reviews that mention neither ("bad", "very bad service", "faltu company hai").
  Reviews with 3+ themes had gone from 4 in 1–100 to 20 in 101–300.
- **16 labels corrected** (#124, 126, 149, 151, 159, 160, 178, 195, 197, 217, 223, 226, 232, 242, 256, 294).
  Divya asked Claude to apply the fixes Claude had proposed. Each row's `note` says
  "changed after Claude review flag; approved by Divya; was <old labels>". 9 vague reviews → `other`;
  support complaints → `refund_support`; "not available in city" → `availability_stock`. 3+ theme rows now 11.

### Decisions
- **Vague complaints ("bad", "very bad service") are `other`**, as the theme definition says, even when 1★.
  Reason: a specific theme needs the text to name the problem; guessing would inflate those themes.
- **Commit before corrections**, so the change from Divya's own labels to reviewed labels is visible in git.

### Failures and fixes
- **Batch 101–300 had a habit error:** the same `1 2` (+10) pairing on vague reviews, likely typed from muscle
  memory. Caught by the `other`-plus-theme check and the short-review scan, not by reading every row.
  **Lesson: run these two checks after every batch.**

- **LLM vs hand labels** (`uv run python -m qpulse.evaluate data/labels/llm_labels_qwen2.5-7b.csv` →
  `docs/LABEL_EVAL.md`): **macro-F1 0.62 (95% CI 0.56–0.67)**, exact match 67%, at least one theme right 82%.
  Best: positive 0.94, pricing_fees 0.76, quality_expiry 0.74. Worst: app_payment_bug 0.29, missing_wrong_item
  0.43 (only 8 and 12 hand examples, so these F1s are very noisy).
- **Added a bootstrap 95% CI for macro-F1** to `src/qpulse/evaluate.py` (1,000 resamples of reviews), so the
  classifier in M4 gets the same interval.
- **Where the LLM differs from Divya:** it under-calls delivery_delay (30 vs 53; precision 0.87, recall 0.49)
  and over-calls refund_support (51 vs 36), app_payment_bug (22 vs 12) and partner_behaviour (20 vs 11).
  It tags any mention of "customer service" as refund_support.
- **By batch:** macro-F1 0.68 on reviews 1–100, 0.59 on 101–300. Could be the reviews or label noise in the
  second batch; the planned self-consistency re-label will help tell.

- **Prompt v2** (`src/qpulse/llm_label.py`, `--prompt v2`; v1 kept with its original file names). Seven rules
  added from the theme definitions: judge text not stars; generic anger → other; refund_support needs a
  refund/return/cancel/support complaint; app_payment_bug only for technical faults; "not delivering to my
  area" → availability_stock; app-cancelled / never-delivered → delivery_delay; referral/coupon → pricing_fees.
  Rules written from disagreements on **reviews 1–100 only**; 101–300 held out.
- **v1 vs v2** (`data/labels/llm_labels_qwen2.5-7b-v2.csv`, 300 reviews in 2.5 min at ~1.9/s):

  | Set | v1 macro-F1 | v2 macro-F1 | v1 exact | v2 exact |
  |---|---|---|---|---|
  | Tuning 1–100 | 0.68 | 0.75 | 71% | 74% |
  | **Held-out 101–300** | **0.59** | **0.60** | **66%** | **70%** |

  Paired bootstrap on held-out: exact match +4 pts (95% CI +1 to +8), macro-F1 +0.01 (−0.03 to +0.05, noise).
  10 held-out reviews became exactly right, 2 stopped being. The tuning-set jump (+0.07) is mostly fit to
  those 100 reviews; the held-out number is the one to quote. `docs/LABEL_EVAL.md` now shows v2 on all 300.
- **Re-labelled the 3,000-review training set with v2** for the M4 classifier: 3,000/3,000, no skips, ~40 min
  (1.25/s, slower than the 1.9/s on the hand set). 13.9% of training reviews changed labels vs v1. Biggest shifts:
  pricing_fees 319 → 367, positive 1,027 → 1,081, app_payment_bug 231 → 194, partner_behaviour 159 → 128,
  other 425 → 383. `data/labels/llm_labels_qwen2.5-7b-v2.csv` now has 3,300 rows (hand set + training set).
- **Adjudicated 8 hand labels** (#55, 61, 69, 86, 87, 90, 95, 100): removed `delivery_delay` only; none of the
  texts names a delay. Divya asked Claude to apply this. Each row's note says "adjudicated after LLM comparison".
  Nothing was added from the model's answers. Scores, original → adjudicated labels:

  | | 1–100 | Held-out 101–300 | All 300 | delivery_delay recall |
  |---|---|---|---|---|
  | v1 | 0.68 → 0.69 | 0.59 → 0.59 | 0.62 → 0.62 | 0.49 → 0.58 |
  | v2 | 0.75 → 0.77 | 0.60 → 0.60 | 0.64 → 0.65 | 0.53 → 0.62 |

  Macro-F1. The held-out score doesn't move because all 8 rows are in the tuning set.
- **Adjudicated #55 and #90 further** at Divya's request: #55 pricing_fees → missing_wrong_item + refund_support
  (4 items ordered, 3 delivered, support didn't respond); #90 refund_support + pricing_fees → pricing_fees (review
  is only about fees). Both now match the v2 model fully (#90) or partly (#55). All 300 with v2: macro-F1 0.66,
  exact 72%. Held-out 101–300 unchanged at 0.60 / 70%.

### Decisions
- **Tune on 1–100, score on 101–300.** Reason: rules written from the same reviews they are scored on would
  overstate the gain. Caveat: the v1 report's "first 15 disagreements" list (sorted by review ID) included some
  101–300 reviews, so the held-out set isn't perfectly unseen; the rules are general, not copied from those.
- **Did not push the prompt toward more delivery_delay.** Most "missed" delays in 1–100 (#55, 61, 69, 86, 87,
  90, 95, 100) are hand labels with delivery_delay on reviews that don't mention a delay, the same `1`-key habit
  found in 101–300. Raising model recall there would fit label errors.
- **Adjudicated labels are kept separate from review corrections.** Fixing only rows where the model disagrees
  can only raise the model's score, so these 8 are labelled as adjudicated and both scores are reported.
  The held-out 101–300 number is unaffected and stays the headline.
- **Otherwise, don't edit hand labels to match the model.** Some disagreements look like hand-label misses (e.g.
  "sabse ghatiya customer service… 2 hours" has no refund_support in the hand labels), but changing labels
  after seeing the model's answers would inflate the score. They stay as they are.

### Next
- Report in the README as "300 hand labels; 27 corrected after a review pass, 8 more adjudicated after comparing
  with the LLM (delivery_delay removed; #55 and #90 fully relabelled), each noted per row".
- M4: train the fast classifier on the v2 training labels; score on held-out hand labels 101–300.
- In a week, Divya re-labels 30 random reviews blind to measure her own consistency.

---

## 2026-10-28: Milestone 4, fast theme classifier

### Work done
- **Pushed** the 8 commits from 2026-10-21 to 2026-10-24 to GitHub (`ee7d34b..215d1c7`).
- **Compared four classifiers** (one logistic regression per theme, balanced class weights), all trained on the
  3,000 LLM v2 training labels. C and threshold were picked on hand labels 1–100. Best tuning macro-F1 per feature set:

  | Features | Best tuning macro-F1 (1–100) | Speed |
  |---|---|---|
  | **TF-IDF word 1–2-grams + char 2–5-grams** | **0.713** (C = 10, threshold 0.7) | ~20,000 reviews/s |
  | TF-IDF + multilingual MiniLM-L12 embeddings | 0.690 | ~70 reviews/s (embedding) |
  | paraphrase-multilingual-mpnet-base-v2 embeddings | 0.613 | ~44 reviews/s |
  | paraphrase-multilingual-MiniLM-L12-v2 embeddings | 0.652 | ~75 reviews/s |

  Embeddings via `fastembed` (ONNX, CPU). TF-IDF won on score and speed, so `fastembed` was removed again.
- **`src/qpulse/classify.py`**: retrains from the label files in git on every run (a few seconds) and labels any
  review not yet in `data/themes.parquet`. A review with no theme over the threshold gets its most likely theme,
  like the hand labels, where every review has at least one. `--rebuild` re-labels everything; `--evaluate` writes `docs/CLASSIFIER_EVAL.md`.
- **Held-out score (hand labels 101–300, 200 reviews):** classifier macro-F1 **0.59** (95% CI 0.50–0.66), exact
  match 66%; its teacher, the LLM v2, scores 0.60 (0.52–0.68) and 70%. Paired bootstrap difference −0.01
  (−0.07 to +0.05): no measurable loss. Weakest themes: partner_behaviour F1 0.29 (9 reviews), availability_stock
  0.42, app_payment_bug 0.46. Better than the LLM on app_payment_bug, missing_wrong_item, pricing_fees.
- **Labelled all 370,006 reviews in 10 s** → `data/themes.parquet` (gitignored; lives in the `data` release).
  Shares: positive 67.9%, other 9.4%, refund_support 6.8%, pricing_fees 6.2%, delivery_delay 4.8%,
  quality_expiry 3.8%, app_payment_bug 2.2%, missing_wrong_item 2.0%, partner_behaviour 1.6%, availability_stock 1.6%.
- **Daily job** (`.github/workflows/daily.yml`): downloads `themes.parquet` from the release, runs
  `qpulse.classify` after collection, uploads it back. Not yet run in CI.
- **Metrics** (`src/qpulse/metrics.py`): uses `data/themes.parquet` by default when present; `--themes` also takes
  `.parquet`. Latest full week in local data (w/c Oct 12): 5 alerts, all theme shares (BigBasket missing/wrong
  items and quality worse; Blinkit positive up, partner_behaviour down; Zepto availability_stock down).
- **Re-ran the alert backtest with theme metrics** (52 series instead of 12): k = 2.0 → 5.7 alerts/week,
  **k = 2.5 → 2.5/week** (4.7% of metric-weeks; 17 worse, 14 better, 6 volume), k = 3.0 → 0.7/week.
  `docs/ALERT_CALIBRATION.md` was **not** updated: its fixed "Chosen" text says "under one alert a week",
  which is no longer true, and the choice of k is an open decision for Divya.

### Decisions
- **TF-IDF over sentence embeddings**, against PLAN.md §11. Reason: higher tuning macro-F1 (0.71 vs 0.65), ~250×
  faster, and no 220 MB model download in CI. Likely why: the training labels come from an LLM reading surface
  words, and character n-grams catch Hinglish spelling variants ("bekar"/"bekaar") that the embedding models,
  trained mostly on formal text, don't place close together.
- **Retrain every run instead of saving a model file.** Training takes seconds, it avoids a binary in git and
  pickle-version breakage, and the model always matches the label files in git. Old predictions are not
  re-labelled unless `--rebuild` is passed, so after a label or setting change, run `--rebuild` once.
- **Selected on 1–100 only.** The prototype printed held-out scores next to tuning scores, but the pick follows
  the tuning column: the chosen setting scores 0.590 held-out; another TF-IDF setting scored 0.593 there and was not chosen.
  Caveat: the chosen setting is at the edge of the grid (largest C, highest threshold).
- **The classifier can't be better than its teacher on average**, and 0.59 vs 0.60 says it isn't worse. Its
  ceiling is the LLM's labels, so better theme accuracy has to come from better training labels.

### Failures and fixes
- **Two embedding models silently merged:** the prototype keyed results by the model name cut to 22 characters,
  both became `paraphrase-multilingua`, and mpnet overwrote MiniLM. Caught because only one block of results printed
  for two models. Fixed with explicit keys and re-ran.
- **Late-binding lambda:** the combined-features prediction function looked up the TF-IDF features from a dict
  entry that had since been deleted (`KeyError: 'tfidf'`). Fixed by binding the function before deleting.
- **Crash when there are no new reviews:** a second `qpulse.classify` run passed 0 rows to the vectorizer
  (`ValueError: Found array with 0 sample(s)`). In CI this would fail the job on any day with nothing new.
  Caught by running it twice locally; it now returns early. Tested all three paths: full (370,006), none (0),
  incremental (500).

- **Alert width set to k = 3** (`ALERT_K` in `src/qpulse/config.py`), regenerated `docs/ALERT_CALIBRATION.md`
  with theme metrics and new reasoning. Backtest: 11 alerts in 15 weeks (0.7/week; 5 worse, 5 better, 1 volume),
  8 of them theme shares. Latest full week in local data (w/c Oct 12): 0 alerts (5 at k = 2.5).

### Decisions (continued)
- **k = 3 for all metrics (Divya's call).** Reason: at k = 2.5 the theme series push alerts to ~2.5/week, more
  than a weekly report with room for 2–3 actions can carry. Cost, from the k = 2.5 backtest: misses BigBasket's
  1★ jump (w/c Aug 10, z = 2.8) and the second week of Blinkit's rating improvement (Oct 5); the first week
  (Sep 28) is still caught by both rating metrics. Not chosen: a separate k for theme shares (one more knob to
  justify).

- **Verified in CI:** pushed (`4cb9f2e`) and ran the daily workflow by hand
  ([run](https://github.com/divyabasavraj/qcommerce-pulse/actions/runs/40640794985), success). No themes file
  existed in the release yet, so it labelled all 385,009 stored reviews in 18 s and uploaded `themes.parquet`
  (14 MB) to the `data` release. From now on each run labels only new reviews.

### Next
- M6 weekly report.
- In a week, Divya re-labels 30 random reviews blind to measure her own consistency.

