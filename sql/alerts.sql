-- Expected-range alerts (PLAN.md section 8). Needs a view all_metrics(app, week, metric, kind, denom, value, se)
-- and the variables baseline_weeks, alert_k, alert_min_n.
-- Expected range = mean of the previous `baseline_weeks` weeks ± k × their standard deviation,
-- widened to k × the sampling error when the baseline happens to be unusually flat. For shares the
-- sampling error uses the baseline share (what we'd expect if nothing changed), so a week at 0% can't
-- shrink its own range to nothing.
CREATE OR REPLACE VIEW alerts AS
WITH b AS (
    SELECT *,
           avg(value)         OVER w AS base_mean,
           stddev_samp(value) OVER w AS base_sd,
           count(value)       OVER w AS base_weeks
    FROM all_metrics
    WINDOW w AS (PARTITION BY app, metric ORDER BY week
                 RANGE BETWEEN to_days(7 * getvariable('baseline_weeks')::INT) PRECEDING
                           AND INTERVAL 7 DAYS PRECEDING)
),
f AS (
    SELECT *,
           CASE WHEN kind = 'share' THEN sqrt(base_mean * (1 - base_mean) / denom) ELSE se END AS floor_se
    FROM b
),
r AS (
    SELECT *,
           greatest(base_sd, coalesce(floor_se, 0)) AS spread,
           getvariable('alert_k')::DOUBLE * greatest(base_sd, coalesce(floor_se, 0)) AS half_width
    FROM f
)
SELECT app, week, metric, kind, denom, value, base_mean, base_sd, floor_se, base_weeks,
       base_mean - half_width AS expected_low,
       base_mean + half_width AS expected_high,
       (value - base_mean) / nullif(spread, 0) AS z,
       CASE WHEN value > base_mean + half_width THEN 'up'
            WHEN value < base_mean - half_width THEN 'down' END AS direction,
       base_weeks = getvariable('baseline_weeks')::INT
           AND denom >= getvariable('alert_min_n')::INT
           AND (value > base_mean + half_width OR value < base_mean - half_width) AS is_alert
FROM r;
