-- 10 · Can a simple SQL rule tell species apart?
-- Technique: CASE-expression "classifier" on bill shape, then a confusion matrix
-- via GROUP BY actual vs predicted. Thresholds chosen by eyeballing query 03.
WITH predicted AS (
    SELECT
        species AS actual,
        CASE
            WHEN bill_depth_mm < 16.5                       THEN 'Gentoo'
            WHEN bill_length_mm >= 43                        THEN 'Chinstrap'
            ELSE 'Adelie'
        END AS predicted
    FROM penguins
    WHERE bill_length_mm IS NOT NULL AND bill_depth_mm IS NOT NULL
)
SELECT
    actual,
    predicted,
    COUNT(*) AS n,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY actual), 1) AS pct_of_actual
FROM predicted
GROUP BY actual, predicted
ORDER BY actual, n DESC;
