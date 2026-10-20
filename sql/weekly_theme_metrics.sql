-- Weekly theme shares per app, same long form as weekly_metrics (metric = 'theme:<key>').
-- Needs metric_reviews and a table review_themes(review_id, theme) with one row per review per theme.
-- Denominator: reviews with text (emoji/symbol-only reviews can't carry a theme; docs/DATA_QUALITY.md).
CREATE OR REPLACE VIEW weekly_theme_metrics AS
WITH base AS (
    SELECT app, review_week AS week, review_id
    FROM metric_reviews
    WHERE NOT is_empty_or_symbols
),
den AS (
    SELECT app, week, count(*) AS n FROM base GROUP BY ALL
),
num AS (
    SELECT b.app, b.week, t.theme, count(DISTINCT b.review_id) AS k
    FROM base b JOIN review_themes t USING (review_id)
    GROUP BY ALL
),
grid AS (
    SELECT d.app, d.week, d.n, th.theme
    FROM den d CROSS JOIN (SELECT DISTINCT theme FROM review_themes) th
)
SELECT g.app, g.week, 'theme:' || g.theme AS metric, 'share' AS kind, g.n AS denom,
       coalesce(num.k, 0) / g.n AS value, NULL::DOUBLE AS se
FROM grid g LEFT JOIN num USING (app, week, theme);
