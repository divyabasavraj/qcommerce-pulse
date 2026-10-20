-- One row per review with data-quality flags. Downstream metrics read this view, not `reviews`.
-- Decisions for each flag are in docs/DATA_QUALITY.md.
CREATE OR REPLACE VIEW reviews_clean AS
WITH base AS (
    SELECT
        *,
        CAST(review_at AS DATE)                                   AS review_date,
        date_trunc('week', review_at)::DATE                       AS review_week,   -- weeks start Monday
        trim(text)                                                AS text_trim,
        lower(trim(text))                                         AS text_norm,
        length(regexp_replace(trim(text), '\s+', ' ', 'g'))
            - length(replace(regexp_replace(trim(text), '\s+', ' ', 'g'), ' ', '')) + 1 AS n_words
    FROM reviews
),
dup AS (
    -- Same long text posted several times for one app = copy-paste / campaign spam.
    SELECT app, text_norm, count(*) AS n_same_text
    FROM base
    WHERE length(text_norm) >= 40
    GROUP BY ALL
)
SELECT
    b.* EXCLUDE (text_trim, text_norm),
    regexp_matches(b.text, '[ऀ-ॿ]')                         AS has_devanagari,
    (b.text_trim = '' OR NOT regexp_matches(b.text, '[A-Za-zऀ-ॿ0-9]')) AS is_empty_or_symbols,
    (b.n_words <= 2)                                                  AS is_very_short,
    coalesce(d.n_same_text, 1) >= 3                                   AS is_repeated_text,
    regexp_matches(b.text_norm, '(https?://|www\.|[a-z0-9-]+\.(com|in|net|org|xyz)/|t\.me/|wa\.me/)') AS has_link,
    -- Clearly happy words with 1-2 stars, or clearly unhappy words with 4-5 stars.
    (b.rating <= 2 AND regexp_matches(b.text_norm, '^(very |so |super |too )?(good|nice|great|excellent|awesome|best|superb|amazing|love it|accha|badhiya|mast)( app| service| experience)?[ !.]*$'))
    OR (b.rating >= 4 AND regexp_matches(b.text_norm, '\b(worst|pathetic|fraud|scam|useless|horrible|bakwas|bekar|ghatiya|cheat(ing|ers)?)\b'))
                                                                      AS star_text_mismatch,
    b.app_version IS NULL                                             AS missing_version
FROM base b
LEFT JOIN dup d USING (app, text_norm);
