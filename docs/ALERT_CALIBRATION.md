# Alert calibration

_Generated 2026-10-20 by `uv run python -m qpulse.metrics --calibrate`._
Weeks 2026-05-11 to 2026-10-12 (full Monday-Sunday weeks from `METRICS_START`).
Theme metrics: not included (no theme labels for all reviews yet).

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

## Backtest: how many alerts each width would have raised

| k | weeks scored | series | alerts | alerts / week | % of metric-weeks flagged | worse | better | volume |
|---|---|---|---|---|---|---|---|---|
| 2.0 | 15 | 12 | 27 | 1.8 | 15.0 | 8 | 12 | 7 |
| 2.5 | 15 | 12 | 12 | 0.8 | 6.7 | 1 | 5 | 6 |
| 3.0 | 15 | 12 | 3 | 0.2 | 1.7 | 0 | 2 | 1 |

Chosen: **k = 2.5**. The weekly report has room for 2-3 actions, so the alert list must stay short.
k = 2 flags ~15% of metric-weeks, far above the ~5% normal noise would give: the SD of only 8
weekly values is itself noisy, so the range is often too narrow. k = 3 misses events that read as real
when checked (Blinkit's rating improving two weeks running, caught by both rating metrics; a BigBasket 1★
jump). k = 2.5 keeps those at under one alert a week. Re-check once theme metrics are added: they add
~10 series per app, roughly 4× the alert count.

## Alerts at k = 2.5

| week | app | metric | denom | value | base_mean | expected_low | expected_high | z | verdict |
|---|---|---|---|---|---|---|---|---|---|
| 2026-07-13 | instamart | reviews | 1750 | 1750.0 | 1508.75 | 1281.3 | 1736.2 | 2.652 | change |
| 2026-07-20 | blinkit | reviews | 9061 | 9061.0 | 10381.875 | 9077.965 | 11685.785 | -2.533 | change |
| 2026-08-10 | bigbasket | pct_1star | 1538 | 0.196 | 0.144 | 0.097 | 0.191 | 2.764 | worse |
| 2026-08-31 | bigbasket | reviews | 2906 | 2906.0 | 1633.875 | 567.227 | 2700.523 | 2.982 | change |
| 2026-08-31 | instamart | reviews | 1892 | 1892.0 | 1631.125 | 1413.798 | 1848.452 | 3.001 | change |
| 2026-09-14 | zepto | reviews | 1453 | 1453.0 | 1669.75 | 1478.865 | 1860.635 | -2.839 | change |
| 2026-09-28 | blinkit | avg_rating | 9816 | 4.144 | 4.089 | 4.046 | 4.132 | 3.202 | better |
| 2026-09-28 | blinkit | pct_1star | 9816 | 0.148 | 0.161 | 0.152 | 0.17 | -3.582 | better |
| 2026-09-28 | zepto | pct_1star | 1473 | 0.354 | 0.39 | 0.357 | 0.423 | -2.741 | better |
| 2026-10-05 | blinkit | avg_rating | 9660 | 4.164 | 4.093 | 4.03 | 4.156 | 2.827 | better |
| 2026-10-05 | blinkit | pct_1star | 9660 | 0.144 | 0.16 | 0.146 | 0.174 | -2.957 | better |
| 2026-10-05 | zepto | reviews | 1296 | 1296.0 | 1569.375 | 1311.693 | 1827.057 | -2.652 | change |
