-- Version watch (PLAN.md section 8.4): app versions whose reviews this week carry far more bug or complaint
-- themes than the same app's reviews over the baseline weeks.
-- Needs metric_reviews, review_themes(review_id, theme) and the variables report_week, baseline_weeks,
-- alert_k, version_min_n. Same denominator as weekly_theme_metrics: reviews with text.
-- Flagged when the version has at least version_min_n reviews this week, its share is at least twice the
-- baseline, and it is more than alert_k sampling errors above the baseline (sampling error at the baseline share).
CREATE OR REPLACE VIEW version_watch AS
WITH r AS (
    SELECT m.app, m.app_version, m.review_week AS week, m.review_id,
           bool_or(t.theme = 'app_payment_bug')                    AS is_bug,
           bool_or(t.theme NOT IN ('positive', 'other'))           AS is_complaint
    FROM metric_reviews m
    LEFT JOIN review_themes t USING (review_id)
    WHERE NOT m.is_empty_or_symbols
    GROUP BY ALL
),
long AS (
    SELECT app, app_version, week, 'app_payment_bug' AS metric, is_bug::INT AS hit FROM r
    UNION ALL
    SELECT app, app_version, week, 'any_complaint', is_complaint::INT FROM r
),
base AS (
    SELECT app, metric, avg(hit) AS base_share, count(*) AS base_n
    FROM long
    WHERE week <  getvariable('report_week')::DATE
      AND week >= getvariable('report_week')::DATE - to_days(7 * getvariable('baseline_weeks')::INT)
    GROUP BY ALL
),
cur AS (
    SELECT app, app_version, metric, count(*) AS n, avg(hit) AS share
    FROM long
    WHERE week = getvariable('report_week')::DATE AND app_version IS NOT NULL
    GROUP BY ALL
)
SELECT c.app, c.app_version, c.metric, c.n, c.share, b.base_share, b.base_n,
       c.share / nullif(b.base_share, 0) AS ratio,
       (c.share - b.base_share) / nullif(sqrt(b.base_share * (1 - b.base_share) / c.n), 0) AS z,
       c.n >= getvariable('version_min_n')::INT
           AND c.share >= 2 * b.base_share
           AND (c.share - b.base_share) / nullif(sqrt(b.base_share * (1 - b.base_share) / c.n), 0)
               > getvariable('alert_k')::DOUBLE AS is_flag
FROM cur c JOIN base b USING (app, metric);
