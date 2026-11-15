-- 08 · Median flipper length per species.
-- Technique: SQLite has no MEDIAN(); emulate it with ROW_NUMBER + COUNT windows and
-- average the one (odd n) or two (even n) middle values.
WITH ordered AS (
    SELECT
        species,
        flipper_length_mm,
        ROW_NUMBER() OVER (PARTITION BY species ORDER BY flipper_length_mm) AS rn,
        COUNT(*)     OVER (PARTITION BY species)                            AS cnt
    FROM penguins
    WHERE flipper_length_mm IS NOT NULL
)
SELECT species, AVG(flipper_length_mm) AS median_flipper_length_mm, MAX(cnt) AS n
FROM ordered
WHERE rn IN ((cnt + 1) / 2, (cnt + 2) / 2)
GROUP BY species
ORDER BY species;
