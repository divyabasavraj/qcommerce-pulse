# Fast theme classifier

_Generated 2026-10-28 by `uv run python -m qpulse.classify --evaluate`._

TF-IDF (word 1–2-grams + character 2–5-grams) with one logistic regression per theme (balanced class
weights), trained on the 3,000 reviews labelled by qwen2.5-7b with prompt v2. A theme is on when its
probability is at least the threshold; a review with no theme over the threshold gets its most likely one.

## Settings chosen on hand labels 1–100 (macro-F1)

| C | threshold 0.5 | threshold 0.6 | threshold 0.7 |
|---|---|---|---|
| 0.3 | 0.574 | 0.644 | 0.700 |
| 1.0 | 0.636 | 0.649 | 0.692 |
| 3.0 | 0.642 | 0.663 | 0.697 |
| 10.0 | 0.657 | 0.692 | 0.713 |

Chosen: C = 10.0, threshold = 0.7. The 100 tuning reviews are few, so differences of 0.01–0.02 in this grid are noise.

## Held-out score: hand labels 101–300 (200 reviews)

| labeller | macro-F1 | 95% CI | exact match |
|---|---|---|---|
| fast classifier | 0.59 | 0.50–0.66 | 66% |
| LLM qwen2.5-7b v2 (its teacher) | 0.60 | 0.52–0.68 | 70% |

Classifier minus LLM, paired bootstrap: -0.01 macro-F1 (95% CI -0.07 to +0.05).

Speed: about 19,421 reviews/s on one laptop CPU, against 1–2 reviews/s for the LLM (docs/PROJECT_LOG.md).

| theme | support | precision | recall | f1 | LLM f1 |
|---|---|---|---|---|---|
| delivery_delay | 31 | 0.84 | 0.52 | 0.64 | 0.69 |
| missing_wrong_item | 5 | 0.50 | 0.60 | 0.55 | 0.46 |
| quality_expiry | 28 | 0.81 | 0.46 | 0.59 | 0.65 |
| refund_support | 18 | 0.48 | 0.83 | 0.61 | 0.64 |
| pricing_fees | 22 | 0.80 | 0.73 | 0.76 | 0.73 |
| app_payment_bug | 11 | 0.40 | 0.55 | 0.46 | 0.32 |
| partner_behaviour | 9 | 0.40 | 0.22 | 0.29 | 0.40 |
| availability_stock | 12 | 0.57 | 0.33 | 0.42 | 0.53 |
| positive | 79 | 0.95 | 0.90 | 0.92 | 0.96 |
| other | 29 | 0.66 | 0.66 | 0.66 | 0.64 |
