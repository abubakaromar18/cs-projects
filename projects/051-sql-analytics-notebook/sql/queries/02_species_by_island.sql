-- 02 · Where does each species live?
-- Technique: GROUP BY two columns + share-of-total via a window over the aggregate.
SELECT
    species,
    island,
    COUNT(*)                                                     AS n,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY species), 1)
                                                                 AS pct_of_species
FROM penguins
GROUP BY species, island
ORDER BY species, n DESC;
