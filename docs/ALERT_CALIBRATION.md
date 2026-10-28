# Alert calibration

_Generated 2026-10-28 by `uv run python -m qpulse.metrics --calibrate`._
Weeks 2026-05-11 to 2026-10-12 (full Monday-Sunday weeks from `METRICS_START`).
Theme metrics: from `themes.parquet`.

A week is flagged when a metric is outside **baseline mean ± k × max(baseline SD, sampling error)**,
with a baseline of the previous 8 weeks and at least 200 reviews in the week.
For shares the sampling error is taken at the baseline share, so a week at 0% can't shrink its own range. The first 8
weeks only serve as baseline.

## Week-to-week noise

| app | metric | weeks | min | mean | max | week_to_week_sd | avg_sampling_error |
|---|---|---|---|---|---|---|---|
| bigbasket | avg_rating | 23 | 3.954 | 4.139 | 4.378 | 0.116 | 0.04 |
| blinkit | avg_rating | 23 | 4.064 | 4.112 | 4.164 | 0.032 | 0.015 |
| instamart | avg_rating | 23 | 4.006 | 4.08 | 4.138 | 0.045 | 0.038 |
| zepto | avg_rating | 23 | 2.994 | 3.318 | 3.484 | 0.112 | 0.046 |
| bigbasket | pct_1star | 23 | 0.121 | 0.172 | 0.22 | 0.028 | 0.01 |
| blinkit | pct_1star | 23 | 0.142 | 0.155 | 0.166 | 0.007 | 0.004 |
| instamart | pct_1star | 23 | 0.149 | 0.167 | 0.18 | 0.009 | 0.009 |
| zepto | pct_1star | 23 | 0.341 | 0.382 | 0.458 | 0.027 | 0.012 |
| bigbasket | reviews | 23 | 970.0 | 1587.435 | 3106.0 | 597.386 | nan |
| blinkit | reviews | 23 | 9028.0 | 10107.913 | 12294.0 | 819.412 | nan |
| instamart | reviews | 23 | 1389.0 | 1564.478 | 1892.0 | 124.202 | nan |
| zepto | reviews | 23 | 1296.0 | 1677.0 | 2038.0 | 188.583 | nan |
| bigbasket | theme:app_payment_bug | 23 | 0.012 | 0.022 | 0.028 | 0.005 | 0.004 |
| blinkit | theme:app_payment_bug | 23 | 0.017 | 0.02 | 0.023 | 0.002 | 0.001 |
| instamart | theme:app_payment_bug | 23 | 0.012 | 0.02 | 0.026 | 0.004 | 0.004 |
| zepto | theme:app_payment_bug | 23 | 0.018 | 0.03 | 0.044 | 0.006 | 0.004 |
| bigbasket | theme:availability_stock | 23 | 0.008 | 0.015 | 0.022 | 0.003 | 0.003 |
| blinkit | theme:availability_stock | 23 | 0.013 | 0.015 | 0.02 | 0.002 | 0.001 |
| instamart | theme:availability_stock | 23 | 0.008 | 0.016 | 0.025 | 0.004 | 0.003 |
| zepto | theme:availability_stock | 23 | 0.008 | 0.016 | 0.021 | 0.003 | 0.003 |
| bigbasket | theme:delivery_delay | 23 | 0.033 | 0.057 | 0.088 | 0.012 | 0.006 |
| blinkit | theme:delivery_delay | 23 | 0.035 | 0.042 | 0.053 | 0.004 | 0.002 |
| instamart | theme:delivery_delay | 23 | 0.02 | 0.026 | 0.035 | 0.004 | 0.004 |
| zepto | theme:delivery_delay | 23 | 0.052 | 0.074 | 0.119 | 0.021 | 0.006 |
| bigbasket | theme:missing_wrong_item | 23 | 0.005 | 0.015 | 0.026 | 0.005 | 0.003 |
| blinkit | theme:missing_wrong_item | 23 | 0.011 | 0.015 | 0.018 | 0.002 | 0.001 |
| instamart | theme:missing_wrong_item | 23 | 0.015 | 0.021 | 0.026 | 0.003 | 0.004 |
| zepto | theme:missing_wrong_item | 23 | 0.038 | 0.054 | 0.07 | 0.009 | 0.006 |
| bigbasket | theme:other | 23 | 0.058 | 0.076 | 0.099 | 0.011 | 0.007 |
| blinkit | theme:other | 23 | 0.078 | 0.088 | 0.102 | 0.007 | 0.003 |
| instamart | theme:other | 23 | 0.063 | 0.082 | 0.099 | 0.009 | 0.007 |
| zepto | theme:other | 23 | 0.072 | 0.09 | 0.103 | 0.009 | 0.007 |
| bigbasket | theme:partner_behaviour | 23 | 0.01 | 0.016 | 0.022 | 0.004 | 0.003 |
| blinkit | theme:partner_behaviour | 23 | 0.012 | 0.015 | 0.017 | 0.002 | 0.001 |
| instamart | theme:partner_behaviour | 23 | 0.005 | 0.009 | 0.017 | 0.003 | 0.002 |
| zepto | theme:partner_behaviour | 23 | 0.021 | 0.027 | 0.036 | 0.004 | 0.004 |
| bigbasket | theme:positive | 23 | 0.66 | 0.712 | 0.785 | 0.034 | 0.012 |
| blinkit | theme:positive | 23 | 0.69 | 0.712 | 0.737 | 0.011 | 0.005 |
| instamart | theme:positive | 23 | 0.693 | 0.717 | 0.743 | 0.014 | 0.012 |
| zepto | theme:positive | 23 | 0.429 | 0.511 | 0.546 | 0.029 | 0.012 |
| bigbasket | theme:pricing_fees | 23 | 0.038 | 0.047 | 0.056 | 0.005 | 0.006 |
| blinkit | theme:pricing_fees | 23 | 0.053 | 0.062 | 0.071 | 0.004 | 0.002 |
| instamart | theme:pricing_fees | 23 | 0.065 | 0.083 | 0.106 | 0.01 | 0.007 |
| zepto | theme:pricing_fees | 23 | 0.043 | 0.059 | 0.076 | 0.009 | 0.006 |
| bigbasket | theme:quality_expiry | 23 | 0.024 | 0.041 | 0.057 | 0.008 | 0.005 |
| blinkit | theme:quality_expiry | 23 | 0.025 | 0.028 | 0.033 | 0.002 | 0.002 |
| instamart | theme:quality_expiry | 23 | 0.021 | 0.03 | 0.039 | 0.005 | 0.004 |
| zepto | theme:quality_expiry | 23 | 0.078 | 0.099 | 0.116 | 0.011 | 0.007 |
| bigbasket | theme:refund_support | 23 | 0.035 | 0.074 | 0.099 | 0.016 | 0.007 |
| blinkit | theme:refund_support | 23 | 0.035 | 0.045 | 0.052 | 0.004 | 0.002 |
| instamart | theme:refund_support | 23 | 0.044 | 0.056 | 0.068 | 0.006 | 0.006 |
| zepto | theme:refund_support | 23 | 0.17 | 0.199 | 0.237 | 0.017 | 0.01 |

## Backtest: how many alerts each width would have raised

| k | weeks scored | series | alerts | alerts / week | % of metric-weeks flagged | worse | better | volume |
|---|---|---|---|---|---|---|---|---|
| 2.0 | 15 | 52 | 86 | 5.7 | 11.0 | 46 | 33 | 7 |
| 2.5 | 15 | 52 | 37 | 2.5 | 4.7 | 17 | 14 | 6 |
| 3.0 | 15 | 52 | 11 | 0.7 | 1.4 | 5 | 5 | 1 |

Chosen: **k = 3.0** (2026-10-28; was 2.5). The weekly report has room for 2-3 actions, so the alert list
must stay short. With rating and volume metrics only, k = 2.5 gave under one alert a week. Theme shares add
~10 series per app, and k = 2.5 then gives about 2.5 a week, more than the report can act on. k = 3 brings it
back under one a week. Cost, from the k = 2.5 backtest: it misses BigBasket's 1★ jump (week of Aug 10, z = 2.8)
and the second week of Blinkit's rating improvement (Oct 5); the first week (Sep 28) is still caught by both
rating metrics. k = 2 flags ~11% of metric-weeks: the SD of only 8 weekly values is itself noisy, so the
range is often too narrow.

## Alerts at k = 3.0

| week | app | metric | denom | value | base_mean | expected_low | expected_high | z | verdict |
|---|---|---|---|---|---|---|---|---|---|
| 2026-07-13 | zepto | theme:app_payment_bug | 1693 | 0.044 | 0.029 | 0.016 | 0.042 | 3.603 | worse |
| 2026-07-20 | blinkit | theme:delivery_delay | 8875 | 0.035 | 0.043 | 0.036 | 0.049 | -3.503 | better |
| 2026-07-20 | blinkit | theme:positive | 8875 | 0.737 | 0.715 | 0.7 | 0.73 | 4.413 | better |
| 2026-07-27 | bigbasket | theme:refund_support | 2041 | 0.035 | 0.066 | 0.036 | 0.096 | -3.024 | better |
| 2026-08-03 | instamart | theme:positive | 1496 | 0.693 | 0.731 | 0.697 | 0.766 | -3.341 | worse |
| 2026-08-03 | instamart | theme:pricing_fees | 1496 | 0.106 | 0.084 | 0.062 | 0.105 | 3.127 | worse |
| 2026-08-31 | bigbasket | theme:delivery_delay | 2857 | 0.088 | 0.057 | 0.028 | 0.086 | 3.139 | worse |
| 2026-08-31 | blinkit | theme:other | 9604 | 0.1 | 0.085 | 0.075 | 0.095 | 4.45 | worse |
| 2026-08-31 | instamart | reviews | 1892 | 1892.0 | 1631.125 | 1370.332 | 1891.918 | 3.001 | change |
| 2026-09-28 | blinkit | avg_rating | 9816 | 4.144 | 4.089 | 4.037 | 4.141 | 3.202 | better |
| 2026-09-28 | blinkit | pct_1star | 9816 | 0.148 | 0.161 | 0.15 | 0.172 | -3.582 | better |
