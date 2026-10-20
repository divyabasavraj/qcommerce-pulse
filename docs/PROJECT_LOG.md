# Project log

Decisions and failures, newest last.

## 2026-10-20: Milestones 1–3 (collector, data quality, labelling)

**Swiggy Instamart app ID (open decision closed).** Instamart has a standalone Play Store app,
`in.swiggy.android.instamart` (50M+ installs, ~127k ratings). Using it instead of filtering Instamart
reviews out of the main Swiggy food app avoids a keyword filter that would have mislabelled reviews.

**All four package IDs verified** against the Play Store: Blinkit `com.grofers.customerapp`,
Zepto `com.zeptoconsumerapp`, BigBasket `com.bigbasket.mobileapp`, Instamart `in.swiggy.android.instamart`.

**Review volume is very uneven.** Blinkit gets ~1,000 reviews/day; the other three get ~150–250/day.
All metrics must be shares within an app, never raw counts across apps, and alerts need a minimum count.

**Languages.** The scraper filters reviews by language. Pulling both `en` and `hi` and de-duplicating by review ID
covers English, Devanagari Hindi and Hinglish (Latin script, which Play tags as `en`).

**Privacy.** Reviewer name and avatar are dropped before anything is written. Phone numbers and emails inside
review text are masked. Developer reply text isn't stored, only whether there was a reply and when.

**Storage.** Monthly Parquet files (`data/raw/reviews_YYYY-MM.parquet`), kept in a GitHub release named `data`
rather than in git, so the repo stays small. DuckDB reads them through a view. Daily runs re-read 2 days before
the newest stored review to catch late-indexed reviews; edited reviews keep their ID and the newest version wins.

**Labelling model.** No Gemini key on this machine, so the plan's fallback is used: local `qwen2.5:7b` via Ollama,
temperature 0, JSON output restricted to the theme list. Smoke test: ~0.5 s/review, correct on simple
English and Hinglish examples. Real accuracy comes from the hand-label comparison, not the smoke test.

**Label sets.** The test and training sets are stratified by app (equal per app) and rating (55% 1–2★, 15% 3★, 30% 4–5★)
so rare complaint themes get enough examples. That makes theme shares inside these sets non-representative.
That's fine for per-theme F1 but they must never be reported as population shares.

**Failure: silent truncation in the first backfill.** The run log said `ok` for all four apps, but Blinkit's English
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

**Backfill re-run result.** 370,006 reviews, Apr 20 – Oct 19 2026, zero zero-review days for any app
(Blinkit 251k, Zepto 42k, BigBasket 38k, Instamart 38k). Instamart's 6 "low days" (Apr 25 – May 2) were checked:
volume dips smoothly to ~30/day and recovers by May 6, never zero. That's a real lull, not a collection cut.
