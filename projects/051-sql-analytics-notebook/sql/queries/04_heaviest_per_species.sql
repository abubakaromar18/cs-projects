-- 04 · Top 3 heaviest penguins in each species.
-- Technique: ROW_NUMBER() window function inside a CTE, then filter on the rank.
WITH ranked AS (
    SELECT
        id, species, island, sex, body_mass_g,
        ROW_NUMBER() OVER (
            PARTITION BY species
            ORDER BY body_mass_g DESC, id
        ) AS rank_in_species
    FROM penguins
    WHERE body_mass_g IS NOT NULL
)
SELECT species, rank_in_species, id, island, sex, body_mass_g
FROM ranked
WHERE rank_in_species <= 3
ORDER BY species, rank_in_species;
