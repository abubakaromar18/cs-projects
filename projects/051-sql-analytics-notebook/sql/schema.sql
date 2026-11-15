-- Schema for the Palmer Penguins analytics database.
-- A small star-ish layout: one fact table of measurements and one
-- dimension table describing each species.

DROP TABLE IF EXISTS penguins;
DROP TABLE IF EXISTS species;

CREATE TABLE species (
    species         TEXT PRIMARY KEY,
    scientific_name TEXT NOT NULL,
    genus           TEXT NOT NULL
);

CREATE TABLE penguins (
    id                INTEGER PRIMARY KEY,           -- surrogate key (row order in CSV)
    species           TEXT NOT NULL REFERENCES species(species),
    island            TEXT NOT NULL,
    bill_length_mm    REAL,                          -- NULL when not measured
    bill_depth_mm     REAL,
    flipper_length_mm INTEGER,
    body_mass_g       INTEGER,
    sex               TEXT CHECK (sex IN ('male', 'female') OR sex IS NULL),
    year              INTEGER NOT NULL CHECK (year BETWEEN 2007 AND 2009)
);

-- Most analyses group by species/island, so index them.
CREATE INDEX idx_penguins_species_island ON penguins(species, island);
