-- Monthly memo metrics (PLAN.md section 9.1). Needs reviews_clean, review_themes(review_id, theme) and the
-- variable metrics_start. Reviews with text only (the base for theme shares), without copy-paste or link
-- reviews, in full calendar months (IST dates) on or after metrics_start, and only months that have ended.
CREATE OR REPLACE VIEW monthly_reviews AS
SELECT app, date_trunc('month', review_date)::DATE AS month, review_id, rating
FROM reviews_clean
WHERE NOT is_repeated_text
  AND NOT has_link
  AND NOT is_empty_or_symbols
  AND date_trunc('month', review_date) >= getvariable('metrics_start')::DATE
  AND date_trunc('month', review_date) + INTERVAL 1 MONTH <= (SELECT max(review_date) FROM reviews_clean);

CREATE OR REPLACE VIEW monthly_app AS
SELECT app, month, count(*) AS n, avg(rating) AS avg_rating, stddev_samp(rating) AS sd_rating, sum(rating) AS sum_rating
FROM monthly_reviews
GROUP BY ALL;

-- Impact sizing: the app's average rating if half of the reviews carrying the theme were gone
-- (re-weight them by 0.5). An estimate from review ratings, not the Play Store rating formula.
CREATE OR REPLACE VIEW monthly_themes AS
WITH t AS (
    SELECT m.app, m.month, rt.theme, count(*) AS k, sum(m.rating) AS sum_r, avg(m.rating) AS theme_avg_rating
    FROM monthly_reviews m JOIN review_themes rt USING (review_id)
    GROUP BY ALL
)
SELECT a.app, a.month, th.theme, a.n, coalesce(t.k, 0) AS k, coalesce(t.k, 0) / a.n AS share,
       t.theme_avg_rating, a.avg_rating,
       (a.sum_rating - 0.5 * coalesce(t.sum_r, 0)) / (a.n - 0.5 * coalesce(t.k, 0)) AS halved_avg_rating,
       (a.sum_rating - 0.5 * coalesce(t.sum_r, 0)) / (a.n - 0.5 * coalesce(t.k, 0)) - a.avg_rating AS gain
FROM monthly_app a
CROSS JOIN (SELECT DISTINCT theme FROM review_themes) th
LEFT JOIN t USING (app, month, theme);
