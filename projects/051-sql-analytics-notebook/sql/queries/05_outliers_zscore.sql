-- 05 · Unusually heavy or light penguins relative to their own species.
-- Technique: chained CTEs computing mean and (population) standard deviation,
-- since SQLite has no built-in STDDEV. A |z| > 2.5 is flagged.
WITH stats AS (
    SELECT
        species,
        AVG(body_mass_g)                                     AS mean_mass,
        AVG(body_mass_g * body_mass_g) - AVG(body_mass_g) * AVG(body_mass_g)
                                                             AS var_mass
    FROM penguins
    WHERE body_mass_g IS NOT NULL
    GROUP BY species
),
scored AS (
    SELECT
        p.id, p.species, p.sex, p.body_mass_g,
        (p.body_mass_g - s.mean_mass) / SQRT(s.var_mass)     AS z
    FROM penguins p
    JOIN stats s USING (species)
    WHERE p.body_mass_g IS NOT NULL
)
SELECT id, species, sex, body_mass_g, ROUND(z, 2) AS z_score
FROM scored
WHERE ABS(z) > 2.5
ORDER BY ABS(z) DESC;
