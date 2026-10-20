# Q-Commerce Pulse: Plan

> A live customer-feedback monitor for India's quick-commerce apps (Blinkit, Zepto, Swiggy Instamart, BigBasket). New Play Store reviews arrive every day; every week the CX team gets an action list; every month they get a decision memo with a new deep-dive, and a check on whether last month's advice was right.

## 1. The business situation
Quick commerce in India is a price-and-speed war. App ratings drive installs, and unhappy customers switch to a competitor. Customers say exactly what's going wrong in their reviews: missing items, late delivery, refunds, surge fees, app bugs. Companies get this feedback for free but rarely turn it into a weekly, ranked view of what to fix.

## 2. The decision
**Scenario:** I am the data analyst for the Head of Customer Experience at a quick-commerce company.
**Their brief:** "Every week, tell me what's breaking for our customers and what to do about it. Every month, tell me the biggest problems to fix, what fixing them is worth, and whether last month's advice was right."

| Question | Answer |
|---|---|
| Who is deciding? | Head of CX, with Operations, Product and Support |
| What are they deciding? | Weekly: what to act on now. Monthly: which 3 problems get money and people |
| What are the options? | Fix delivery speed, missing items, refunds, fees, app bugs, partner behaviour (can't fix everything at once) |
| What does the data say? | Complaint themes, trends, unusual changes, competitor comparison |
| Recommendation and its value? | Ranked fixes with estimated rating gain |
| How will we know it worked? | Next week and next month the system checks whether the problem improved and whether predictions came true |

## 3. What exists and our gap
- **Commercial:** review-analytics tools (AppFollow, Appbot, Sensor Tower). Paid, generic, they stop at charts.
- **Portfolios / GitHub:** many one-off "sentiment analysis of Play Store reviews" notebooks. Static, no decisions, no tracking over time.
- **Our gap:**
  1. **Live:** data collected daily, not a one-time scrape
  2. **Actions and decisions, not charts:** weekly action list + monthly ranked recommendations with estimated impact
  3. **New question every month:** a deep-dive on a different business problem
  4. **Closed loop:** every week and month checks the previous one's flags and predictions
  5. **Checked AI:** AI labels and AI-written text measured against hand labels and computed numbers

## 4. Architecture
```
DAILY (GitHub Actions cron, free)
  Play Store ─▶ collect new reviews ─▶ clean + dedupe ─▶ classify themes ─▶ DuckDB / Parquet ─▶ dashboard refresh
  (4 apps)      (google-play-scraper)   (PII dropped)     (small classifier)

WEEKLY (Monday)
  DuckDB ─▶ SQL metrics ─▶ expected-range alerts ─▶ action list ─▶ AI writes text ─▶ number check ─▶ weekly report
                                                     + last week's follow-up

MONTHLY (1st of month)
  DuckDB ─▶ impact sizing ─▶ top 3 fixes ─▶ deep-dive of the month ─▶ predictions + last month's scorecard ─▶ decision memo

ALWAYS ON
  Streamlit dashboard on Hugging Face Spaces (free): theme trends per app, rating by theme, alerts
```

## 5. Data
- **Source:** Google Play reviews via `google-play-scraper` (unofficial; modest volume; public data only)
- **Apps (verify package IDs in milestone 1):** Blinkit (`com.grofers.customerapp`), Zepto (`com.zeptoconsumerapp`), BigBasket (`com.bigbasket.mobileapp`), Swiggy Instamart (standalone app ID to confirm; else Swiggy app with Instamart-related reviews only)
- **Fields kept:** review ID, app, rating, text, date, app version, thumbs-up count, developer reply (yes/no + date)
- **Never stored:** usernames, profile images, anything identifying the reviewer
- **Backfill:** on day one pull the last ~6 months of reviews, so trends exist immediately
- **Languages:** English, Hindi, Hinglish; classifier must handle code-mixed text
- **Context:** a hand-kept `events.csv` of public events (fee changes, new cities, outages, sales, festivals, app releases from news) to explain changes

## 6. Theme taxonomy (v1, refine after reading 300 reviews)
| Theme | Examples |
|---|---|
| Delivery delay | "said 10 min, came in 45" |
| Missing / wrong item | "eggs missing", "got wrong brand" |
| Quality / expiry | "rotten vegetables", "expired milk" |
| Refund / customer support | "refund not received", "chat bot useless" |
| Pricing / fees | "surge fee", "handling charge", "costlier than market" |
| App / payment bug | "app crashes", "UPI failed but money cut" |
| Delivery partner behaviour | "rude", "asked for extra money" |
| Availability / stock | "everything out of stock" |
| Positive / praise | "super fast", "great offers" |
| Other | everything else |

A review can have more than one theme.

## 7. Daily (automatic)
1. Collect new reviews for the 4 apps
2. Clean: remove duplicates and spam, drop personal details, flag text/star mismatches ("great app" with 1★)
3. Classify themes with the fast classifier
4. Save to DuckDB / Parquet
5. Refresh the dashboard
6. Log the run (reviews collected, failures) for pipeline reliability

## 8. Weekly: an action list
Every Monday. Code calculates every number; AI writes the text; code checks every number in the text matches.

1. **Top 3 changes this week** across all 4 apps
2. **Alerts:** a theme is flagged when this week's share is outside its **expected range**: the average of the last 8 weeks ± normal week-to-week variation, with a minimum review count so tiny apps or quiet weeks don't cause false alarms. No forecast model (see section 13).
3. **Competitor view:** who improved or got worse on each theme
4. **Version watch:** any app version linked to a jump in bug or complaint themes
5. **Action list:** 2–3 actions, each with an **owner** (Ops / Product / Support), a **reason** and an **expected effect**. Example:
   - Ops: add rider capacity in high-delay areas this weekend; delay complaints 2× normal range
   - Product: look into app version 24.10; payment-bug complaints tripled after release
   - Support: refund complaints rising for 3 weeks; review refund turnaround time
6. **Last week's follow-up:** did last week's flagged problems get better, worse, or stay the same?

**Decision it drives:** what the team acts on this week.

## 9. Monthly: decision memo + new deep-dive
One page, on the 1st of each month.

### 9.1 Regular memo (same structure every month)
- **Impact sizing:** for each theme, the average review rating if that theme's complaints were halved (re-weight reviews; clearly stated as an estimate from review ratings, not the store rating formula)
- **Top 3 fixes per app**, ranked by estimated rating gain and how often the issue appears
- **Competitor comparison:** where each app is ahead or behind, per theme
- **Predictions for next month:** simple, numeric, testable statements (e.g. "Zepto missing-item share stays above 12% unless a fix ships"), based on recent trend and judgement
- **Scorecard:** last month's predictions marked right/wrong, with reasons

### 9.2 Deep-dive of the month (a different business question each month)
| Month | Deep-dive | Decision it supports |
|---|---|---|
| 1 (Nov 2026) | **Festival readiness:** before/after comparison of complaints in Diwali week (Nov 8) vs normal weeks, by theme and app | How many extra riders and support staff, and which themes to prepare for, next festival / sale |
| 2 | **Fees and pricing:** do handling and surge fees cause more 1★ reviews than delays do? | Change the fee structure, or explain fees better in the app |
| 3 | **Developer replies:** do reviews that get a reply lead to better ratings later? | Whether to fund a review-reply team |
| 4 | **Competitor switching:** what triggers reviews saying "moving to Blinkit / Zepto"? | Which problems actually lose customers |

Each deep-dive: question → analysis → decision → checked the following month.

## 10. Checked AI (and the AI log)
| AI use | Check |
|---|---|
| LLM labels ~3,000 training reviews | Accuracy / F1 per theme vs 300 hand labels |
| Fast classifier labels daily reviews | Same hand-label test set; re-checked monthly on 50 fresh hand labels (drift) |
| LLM writes weekly/monthly text | Every number in the text must match the SQL output; otherwise regenerate once, then fall back to a template |
| AI drafts SQL | Results cross-checked with simple counts; mistakes go in the AI log |

`docs/AI_LOG.md`: where AI helped, where it was wrong, how it was caught.
`docs/PROJECT_LOG.md`: decisions and failures (interview prep, same as PatchPilot).

## 11. Tech stack (₹0)
- Python 3.12, `uv`, **DuckDB** + Parquet; all metrics as `.sql` files
- Collection: `google-play-scraper` in a **GitHub Actions** daily cron; data stored as monthly Parquet files in a GitHub release
- Classification: **LLM labels a training set** (Gemini free tier is fine because reviews are public; local Qwen via Ollama as fallback) → train a **small fast classifier** (multilingual sentence embeddings + logistic regression) that runs daily in CI for free
- Reports: local Qwen via Ollama writes the text; code checks every number
- Dashboard: Streamlit on Hugging Face Spaces
- Stats: pandas, scipy/statsmodels

## 12. Milestones (~6 days of building)
| # | What | Time |
|---|---|---|
| 1 | **Collector + 6-month backfill**: confirm app IDs, schema, dedupe, PII drop; start the daily cron **first** so data builds up | 0.5 day |
| 2 | **Data-quality report**: duplicates, spam, very short reviews, version gaps, text/star mismatches; each issue gets a decision and a reason | 0.5 day |
| 3 | **Theme labelling**: read and hand-label 300 reviews, refine taxonomy, LLM-label ~3,000, measure LLM accuracy | 1 day |
| 4 | **Fast classifier**: train, evaluate on hand labels, deploy in the daily job | 0.5 day |
| 5 | **SQL metrics + expected-range alerts** | 1 day |
| 6 | **Weekly report**: action list, follow-up, AI text + number check | 0.5 day |
| 7 | **Monthly memo + first deep-dive** (Diwali readiness) | 1 day |
| 8 | **Dashboard** | 0.5 day |
| 9 | **Ship**: README (decision and latest result first), sample reports, AI log, limitations, LinkedIn post | 0.5 day |

After that it runs by itself: a new weekly report every Monday, a new memo and deep-dive every month. By interview time there are several weeks of real, dated reports to show.

## 13. Why no forecasting
- Only ~6 months of history, so long seasonal patterns can't be learned; complaint-share forecasts would be noisy and hard to defend.
- Last Diwali (Oct 2025) is outside the 6-month backfill, so a festival forecast has nothing to learn from; a before/after comparison is more honest.
- Expected ranges catch unusual weeks almost as well and are easy to explain.
- Forecasting is shown properly in a separate project built for it.

## 14. Evaluation metrics
- Theme classification: accuracy / macro-F1 vs hand labels (LLM and fast classifier)
- Number-check pass rate of AI-written reports
- Weekly follow-up: % of flagged problems that improved / worsened
- Prediction scorecard: % of monthly predictions that came true
- Pipeline reliability: % of days collected successfully

## 15. Limitations (state in README)
- Play Store reviewers are not all customers; unhappy users review more
- Review rating ≠ the store's overall rating formula
- Impact estimates are correlations, not proven causes
- No internal company data (orders, delivery times)
- We can't make the companies act on recommendations; the loop checks whether flagged problems and predictions moved, not whether a fix was shipped

## 16. Interview story
"I built a live system that tracks India's four quick-commerce apps through their Play Store reviews. It sorts reviews into complaint themes with a classifier that is X% accurate against my hand labels. Every week it gives the CX team an action list with owners; every month a decision memo with a new deep-dive, like Diwali readiness, which showed delay complaints were Y× normal during festival week. Every number the AI writes is checked against SQL, and over N weeks Z% of its predictions came true."

## 17. Open decisions
- [ ] Swiggy Instamart app ID (standalone vs main Swiggy app)
- [ ] Number of hand labels (300 proposed)
- [ ] Alert sensitivity (how many "normal variations" away counts as unusual; set after looking at real week-to-week noise)
- [ ] Dashboard: Streamlit (proposed) vs Looker Studio
