-- Weekly metrics per app, long form: one row per (app, week, metric).
-- Needs reviews_clean and the variable `metrics_start`. Only full Monday-Sunday weeks are kept,
-- and copy-paste / link reviews are excluded (docs/DATA_QUALITY.md).
CREATE OR REPLACE VIEW metric_reviews AS
SELECT *
FROM reviews_clean
WHERE NOT is_repeated_text
  AND NOT has_link
  AND review_week >= getvariable('metrics_start')::DATE
  AND review_week + 6 < (SELECT max(review_date) FROM reviews_clean);   -- the week's Sunday is complete

-- kind: count / mean / share. `se` is the sampling error of this week's value (shares: computed in alerts.sql).
-- Developer-reply rate is left out: has_reply is the state at collection time, so recent weeks always look low.
CREATE OR REPLACE VIEW weekly_metrics AS
WITH w AS (
    SELECT app, review_week AS week, count(*) AS n,
           avg(rating) AS avg_rating, stddev_samp(rating) AS sd_rating,
           count(*) FILTER (WHERE rating = 1) / count(*) AS p_1star
    FROM metric_reviews
    GROUP BY ALL
)
SELECT app, week, 'reviews' AS metric, 'count' AS kind, n AS denom, n::DOUBLE AS value, NULL::DOUBLE AS se FROM w
UNION ALL
SELECT app, week, 'avg_rating', 'mean', n, avg_rating, sd_rating / sqrt(n) FROM w
UNION ALL
SELECT app, week, 'pct_1star', 'share', n, p_1star, NULL FROM w;
