-- 07 · Attach scientific names from the dimension table.
-- Technique: LEFT JOIN fact → dimension; a NULL scientific_name would reveal
-- a species missing from the dimension (referential-integrity check).
SELECT
    s.scientific_name,
    p.species,
    COUNT(p.id)                          AS n_penguins,
    COUNT(DISTINCT p.island)             AS n_islands,
    GROUP_CONCAT(DISTINCT p.island)      AS islands
FROM penguins p
LEFT JOIN species s ON s.species = p.species
GROUP BY p.species, s.scientific_name
ORDER BY n_penguins DESC;
