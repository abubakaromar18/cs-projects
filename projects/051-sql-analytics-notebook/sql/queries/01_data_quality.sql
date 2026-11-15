-- 01 · Data quality: how many rows, and how many NULLs per column?
-- Technique: conditional aggregation (SUM over a boolean expression).
SELECT
    COUNT(*)                                   AS total_rows,
    SUM(bill_length_mm    IS NULL)             AS missing_bill_length,
    SUM(bill_depth_mm     IS NULL)             AS missing_bill_depth,
    SUM(flipper_length_mm IS NULL)             AS missing_flipper_length,
    SUM(body_mass_g       IS NULL)             AS missing_body_mass,
    SUM(sex               IS NULL)             AS missing_sex
FROM penguins;
