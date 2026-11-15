-- 06 · Did average body mass change year over year?
-- Technique: LAG() to compare each year with the previous one inside a species.
WITH yearly AS (
    SELECT species, year, ROUND(AVG(body_mass_g), 0) AS avg_mass_g, COUNT(*) AS n
    FROM penguins
    WHERE body_mass_g IS NOT NULL
    GROUP BY species, year
)
SELECT
    species,
    year,
    n,
    avg_mass_g,
    avg_mass_g - LAG(avg_mass_g) OVER (PARTITION BY species ORDER BY year)
        AS change_from_prev_year_g
FROM yearly
ORDER BY species, year;
