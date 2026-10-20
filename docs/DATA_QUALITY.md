# Data-quality report

_Generated 2026-10-20 by `uv run python -m qpulse.quality`. Do not edit numbers by hand._

## Overview

| app | reviews | first_day | last_day | avg_rating | pct_devanagari | pct_dev_reply | versions |
|---|---|---|---|---|---|---|---|
| blinkit | 251378 | 2026-04-20 | 2026-10-19 | 4.09 | 0.4 | 98.1 | 229 |
| zepto | 42070 | 2026-04-20 | 2026-10-19 | 3.24 | 0.5 | 42.9 | 176 |
| bigbasket | 38457 | 2026-04-20 | 2026-10-19 | 4.11 | 0.6 | 97.1 | 118 |
| instamart | 38101 | 2026-04-20 | 2026-10-19 | 4.04 | 0.3 | 97.9 | 59 |


**Usable rows:** 369,983 of 370,006 for rating metrics; 361,903 for theme metrics.

## Issues and decisions

| Issue | Rows | Share | Decision | Reason |
|---|---|---|---|---|
| Empty or emoji/symbol-only text | 8,080 | 2.2% | Keep for rating metrics; exclude from theme metrics | The star rating is still a real signal, but there's no text to classify. |
| Very short (≤2 words, e.g. 'good', 'worst app') | 186,588 | 50.4% | Keep; classify as usual (most become `positive` or `other`) | These are a large, real part of the review stream; dropping them would inflate complaint shares. |
| Same ≥40-character text posted ≥3 times for one app | 23 | 0.0% | Exclude from all metrics | Copy-paste campaigns or bots; one person/script shouldn't count several times. In practice these are mostly the same delivery partner's name praised over and over, i.e. partners soliciting 5★ reviews. |
| Contains a URL or t.me / wa.me link | 0 | 0.0% | Exclude from all metrics | Promotion or scam text, not customer feedback. The word 'WhatsApp' alone is NOT flagged: most such reviews are customers reporting scam WhatsApp messages, which is real feedback (found in v1 of this rule). |
| Text and stars disagree ('great app' with 1★, 'worst' with 5★) | 2,629 | 0.7% | Keep; report separately as a caveat on rating metrics | Often users who misunderstand the stars. Themes come from the text, so theme metrics are unaffected; rating-by-theme numbers carry this noise. |
| App version missing | 45,308 | 12.2% | Keep; exclude only from version-watch analysis | Version is optional metadata (e.g. reviews posted from the web); the review itself is valid. |


Duplicates by review ID are removed at collection time (the same review can come back from both the `en` and `hi` queries, and edited reviews keep their ID; the newest version is kept).

### Share of each issue by app

| app | is_empty_or_symbols | is_very_short | is_repeated_text | has_link | star_text_mismatch | missing_version |
|---|---|---|---|---|---|---|
| blinkit | 2.3% | 51.9% | 0.0% | 0.0% | 0.8% | 13.1% |
| zepto | 1.6% | 36.3% | 0.0% | 0.0% | 0.4% | 12.2% |
| bigbasket | 1.9% | 48.9% | 0.0% | 0.0% | 0.3% | 8.5% |
| instamart | 2.6% | 57.7% | 0.0% | 0.0% | 0.9% | 10.1% |

## Privacy

Reviewer names and profile images are never written to disk. Phone numbers and email addresses in review text are masked at collection: 1 phone numbers and 2 emails masked so far.

## Daily volume and gaps

| app | median_per_day | zero_days | low_days | last_low_day |
|---|---|---|---|---|
| bigbasket | 183.0 | 0 | 1 | 2026-04-29 |
| blinkit | 1366.0 | 0 | 0 | – |
| instamart | 218.0 | 0 | 6 | 2026-05-02 |
| zepto | 235.0 | 0 | 0 | – |


A *low day* has under 20% of the app's median daily reviews. A run of low days means a collection gap (see the run log), not customers going quiet.

### Examples: Same ≥40-character text posted ≥3 times for one app

| app | rating | text |
|---|---|---|
| bigbasket | 5 | excellent Utkarsh kulshrestha on time delivery |
| bigbasket | 5 | excellent utkarsh kulshrestha on time delivery |
| bigbasket | 5 | excellent utkarsh kulshrestha on time delivery |
| blinkit | 4 | sometimes cash on delivery is not available |
| zepto | 3 | My zepto referral link not showing problem, please fix this problem |
| bigbasket | 5 | excellent Utkarsh kulshreshth on time delivery |

### Examples: Contains a URL or t.me / wa.me link

_none_

### Examples: Text and stars disagree ('great app' with 1★, 'worst' with 5★)

| app | rating | text |
|---|---|---|
| blinkit | 1 | good |
| blinkit | 4 | zapto se to acha hi hai fraud kam to nahi krte jase zapto krta hai. acha hai mera 3 order  |
| zepto | 1 | nice service |
| blinkit | 1 | nice |
| instamart | 2 | good |
| blinkit | 5 | worst app they didn't refund our money even the order was canceled by the delivery partner |

## Collection runs

6 app-runs logged, 100% succeeded.

| run_at | app | mode | fetched | new_reviews | seconds | status |
|---|---|---|---|---|---|---|
| 2026-10-20T08:51:26 | blinkit | backfill | 154068 | 154068 | 1037.0 | ok |
| 2026-10-20T08:51:26 | zepto | backfill | 9699 | 9699 | 47.1 | ok |
| 2026-10-20T08:51:26 | bigbasket | backfill | 38457 | 38457 | 139.2 | ok |
| 2026-10-20T08:51:26 | instamart | backfill | 38101 | 38101 | 166.6 | ok |
| 2026-10-20T09:15:59 | zepto | backfill | 42070 | 32371 | 167.9 | ok |
| 2026-10-20T09:15:59 | blinkit | backfill | 251378 | 97310 | 1419.9 | ok |
