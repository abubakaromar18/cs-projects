# 051 · SQL Analytics Notebook

Exploratory data analysis of the public **Palmer Penguins** dataset (344 penguins, 3 species,
3 Antarctic islands, 2007–2009) written almost entirely in **SQL**. The CSVs are loaded into
SQLite, ten standalone `.sql` files answer one question each, and a Jupyter notebook ties them
together with tables and charts.

## Key concepts

| Query | Question | SQL technique |
|---|---|---|
| 01 | How clean is the data? | Conditional aggregation `SUM(col IS NULL)` |
| 02 | Which species live where? | `GROUP BY` + window over an aggregate for percent-of-total |
| 03 | Average size by species & sex | Aggregates and NULL handling |
| 04 | Heaviest 3 per species | `ROW_NUMBER() OVER (PARTITION BY …)` top-N per group |
| 05 | Outliers | Chained CTEs, variance via `AVG(x²) − AVG(x)²`, z-scores |
| 06 | Year-over-year change | `LAG()` window function |
| 07 | Scientific names | `LEFT JOIN` to a dimension table, referential-integrity check |
| 08 | Median flipper length | Emulating `MEDIAN` with `ROW_NUMBER` + `COUNT` windows |
| 09 | Mass histogram | Integer bucketing and a `CASE` pivot |
| 10 | Rule-based classifier | `CASE` predictions + confusion matrix |

Also: schema design with `PRIMARY KEY`, `REFERENCES`, `CHECK` constraints and an index;
an ETL step that maps `NA` → `NULL` with correct column types; and generating the notebook
from the SQL files so the two never drift apart.

## Layout

```
data/            penguins.csv (CC0) + species.csv dimension
sql/schema.sql   tables, constraints, index
sql/queries/     01_…sql – 10_…sql, one analysis each
analytics/       loader + query runner (stdlib sqlite3; pandas optional) and CLI
build_notebook.py   regenerates notebook.ipynb from sql/
notebook.ipynb   executed notebook with tables and charts
tests/           pytest: loading, every query, notebook execution
```

## Build, run, test

```bash
make install        # pip install -e ".[dev,notebook]"
make run            # print every analysis as a text table
make lab            # open the notebook in JupyterLab
make notebook       # regenerate + execute notebook.ipynb after editing SQL
make db             # write penguins.sqlite, then: sqlite3 penguins.sqlite < sql/queries/04_heaviest_per_species.sql
make test           # 30 tests
```

Run one query by number: `python3 -m analytics 04 08`. List them: `python3 -m analytics --list`.

## Example output

```
=== 04 · Top 3 heaviest penguins in each species. ===
species   | rank_in_species | id  | island    | sex  | body_mass_g
----------+-----------------+-----+-----------+------+------------
Adelie    | 1               | 110 | Biscoe    | male | 4775
Adelie    | 2               | 102 | Biscoe    | male | 4725
Adelie    | 3               | 82  | Torgersen | male | 4700
Chinstrap | 1               | 314 | Dream     | male | 4800
...
Gentoo    | 1               | 170 | Biscoe    | male | 6300

=== 10 · Can a simple SQL rule tell species apart? ===
actual    | predicted | n   | pct_of_actual
----------+-----------+-----+--------------
Adelie    | Adelie    | 137 | 90.7
Chinstrap | Chinstrap | 63  | 92.6
Gentoo    | Gentoo    | 115 | 93.5
...
```

## Testing approach

The tests check that loading is faithful (row counts, `NA` → `NULL`, column types, foreign-key
and `CHECK` constraints), and they check the tricky queries against an independent Python
computation: z-score outliers against `statistics.pstdev`, the emulated median against
`statistics.median`. A final test runs the whole notebook with `nbclient`.

## Possible extensions

* Port the queries to DuckDB and compare its `MEDIAN`, `PIVOT` and `QUALIFY` syntax.
* Add a second public dataset and practice multi-table joins (e.g. weather by island and year).
* Use `jupysql` `%%sql` magics instead of `pandas.read_sql_query`.
* Fit a decision tree in scikit-learn and compare it to the hand-written `CASE` classifier.
* Write the outputs to a small static dashboard.
