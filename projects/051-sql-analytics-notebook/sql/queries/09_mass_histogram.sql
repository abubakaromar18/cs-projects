-- 09 · Body-mass histogram with 500 g buckets, pivoted by species.
-- Technique: integer bucketing + CASE-based pivot (SQLite has no PIVOT keyword).
SELECT
    (body_mass_g / 500) * 500                          AS bucket_start_g,
    (body_mass_g / 500) * 500 + 499                    AS bucket_end_g,
    SUM(CASE WHEN species = 'Adelie'    THEN 1 ELSE 0 END) AS adelie,
    SUM(CASE WHEN species = 'Chinstrap' THEN 1 ELSE 0 END) AS chinstrap,
    SUM(CASE WHEN species = 'Gentoo'    THEN 1 ELSE 0 END) AS gentoo,
    COUNT(*)                                           AS total
FROM penguins
WHERE body_mass_g IS NOT NULL
GROUP BY bucket_start_g
ORDER BY bucket_start_g;
