-- 03 · Average body measurements per species and sex.
-- Technique: aggregates ignore NULLs automatically; rows with unknown sex are excluded.
SELECT
    species,
    sex,
    COUNT(*)                          AS n,
    ROUND(AVG(bill_length_mm), 1)     AS avg_bill_length_mm,
    ROUND(AVG(bill_depth_mm), 1)      AS avg_bill_depth_mm,
    ROUND(AVG(flipper_length_mm), 1)  AS avg_flipper_length_mm,
    ROUND(AVG(body_mass_g), 0)        AS avg_body_mass_g,
    MIN(body_mass_g)                  AS min_body_mass_g,
    MAX(body_mass_g)                  AS max_body_mass_g
FROM penguins
WHERE sex IS NOT NULL
GROUP BY species, sex
ORDER BY species, sex;
