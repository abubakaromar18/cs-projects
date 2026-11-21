# Spreadsheet to SQL Importer

`sheet2sql` reads CSV, TSV and XLSX files, works out a SQL type for every column, cleans up the headers, and loads the rows into a SQLite table. Each table is loaded in a single transaction. It's a small, dependency-free cousin of tools like `csvkit`'s `csvsql` and `pandas.to_sql`.

```
$ sheet2sql examples/employees.csv --db company.db
employees: 5 row(s)
  employee_id          INTEGER   PK NOT NULL unique  (from 'Employee ID')
  full_name            TEXT      NOT NULL unique  (from 'Full Name')
  department           TEXT      NOT NULL  (from 'Department')
  start_date           DATE      NOT NULL unique  (from 'Start Date')
  salary               REAL      NOT NULL unique  (from 'Salary')
  remote               BOOLEAN   NOT NULL  (from 'Remote?')
  last_login           DATETIME  unique  (from 'Last Login')
  zip_code             TEXT      unique  (from 'Zip Code')
```

```
$ sheet2sql examples/employees.csv --dry-run
CREATE TABLE "employees" (
  "employee_id" INTEGER PRIMARY KEY,
  "full_name" TEXT NOT NULL,
  "department" TEXT NOT NULL,
  "start_date" TEXT NOT NULL,
  "salary" REAL NOT NULL,
  "remote" INTEGER NOT NULL CHECK ("remote" IN (0, 1)),
  "last_login" TEXT,
  "zip_code" TEXT
);
```

Some things to notice in that output: `"125,000"` became the number `125000.0`; `yes`/`NO`/`Y` became `1`/`0`; `N/A` and blank cells became real `NULL`s; and the ZIP code `02134` stayed as text, so its leading zero wasn't lost.

## CS concepts demonstrated

- **Type inference over a lattice.** Each cell is classified as the narrowest type that fits it (`NULL < BOOLEAN < INTEGER < REAL < TEXT`, with a parallel `DATE < DATETIME < TEXT` branch). A column's type is the *least upper bound* (join) of all its cells' types. The join is commutative, associative and idempotent, so the order of the rows doesn't matter. The tests check these properties exhaustively. (`infer.py`)
- **Two-pass streaming.** The first pass profiles the columns and the second converts and inserts. Readers can be iterated more than once, so the whole file is never held in memory. `--sample N` cuts the first pass short, which trades accuracy for speed.
- **Batched, atomic writes.** Rows go in with `executemany` in batches of 1000, inside one explicit transaction. Python's `sqlite3` would otherwise autocommit DDL, so `BEGIN` is issued by hand. A failure part-way through rolls back everything, including the `CREATE TABLE`. (`loader.py`)
- **Identifier sanitisation and SQL-injection safety.** Headers are normalised to unique snake_case names (Unicode is folded to ASCII, camelCase is split, a name starting with a digit gets a `c_` prefix, reserved words get a `_` suffix, and duplicates get numbered). Every identifier is quoted, and every value goes through a `?` parameter. (`schema.py`)
- **Constraint inference.** `NOT NULL` is added when a column has no nulls, a `CHECK` limits BOOLEAN columns to 0/1, and a unique, non-null integer `id` / `*_id` column becomes the `PRIMARY KEY`.
- **Format detection.** The CSV delimiter (`, ; \t |`) is detected with `csv.Sniffer`, Excel's UTF-8 BOM is stripped, and XLSX files are streamed with `openpyxl` in read-only mode. Native XLSX types (dates, booleans, numbers) are kept as they are.

## Type rules

| Inferred  | Example cells                                      | Stored as (SQLite)             |
|-----------|----------------------------------------------------|--------------------------------|
| BOOLEAN   | `true`, `No`, `y`, `F`                             | `INTEGER` 0/1 + CHECK          |
| INTEGER   | `42`, `-7`, `1,234,567`                            | `INTEGER`                      |
| REAL      | `3.14`, `.5`, `1e10`, `12,000.75`                  | `REAL`                         |
| DATE      | `2024-02-29`, `2024/02/29`, `03/15/2024`           | `TEXT` ISO-8601 `YYYY-MM-DD`   |
| DATETIME  | `2024-02-29 13:45:00`, `2024-02-29T13:45`          | `TEXT` `YYYY-MM-DD HH:MM:SS`   |
| TEXT      | anything else, or numbers with leading zeros       | `TEXT`                         |
| NULL      | empty, `null`, `none`, `na`, `n/a`, `nan`, `-`     | `NULL`                         |

Dates are stored as ISO-8601 text because that sorts correctly and works directly with SQLite's `date()`/`datetime()` functions.

## Project layout

```
src/sheet2sql/
  infer.py     type lattice, cell classifier, value conversion, column profiling
  readers.py   CSV/TSV/XLSX readers that can be iterated more than once
  schema.py    header -> identifier, CREATE/INSERT generation, PK detection
  loader.py    two-pass transactional import into SQLite
  cli.py       argparse front end
tests/         69 pytest cases (unit, end-to-end, XLSX, CLI)
examples/      employees.csv sample data
```

## Build, run, test

Requires Python 3.10+. Reading XLSX needs `openpyxl`; CSV support uses only the standard library.

```bash
pip install -e ".[dev]"          # or: pip install pytest openpyxl
make test                        # python3 -m pytest
make dry-run                     # print inferred schema for the example
make run                         # load the example into example.db
```

Without installing anything you can run `PYTHONPATH=src python3 -m sheet2sql ...`.

### CLI options

```
sheet2sql FILE [FILE ...] [--db PATH] [-t TABLE] [--sheet NAME] [-d DELIM]
          [--if-exists {fail,replace,append}] [--sample N] [--strict]
          [--no-pk] [--dry-run]
```

- Each XLSX worksheet becomes its own table, and empty sheets are skipped.
- `--if-exists` controls what happens when the table already exists: `fail` (the default) stops with an error, `replace` drops the table and recreates it, and `append` adds rows to it.
- `--sample N` infers types from the first N rows only. A later value that doesn't fit is stored as text and reported, or with `--strict` the import stops and is rolled back.

### Library use

```python
import sqlite3
from sheet2sql import read_any, load_table

conn = sqlite3.connect("shop.db")
for table in read_any("orders.xlsx"):
    result = load_table(conn, table, if_exists="replace")
    print(result.table, result.rows, result.schema.create_sql())
```

## Possible extensions

- Support PostgreSQL/MySQL with dialect-specific DDL (`BOOLEAN`, `DATE`, `NUMERIC(p,s)`, `VARCHAR(n)` sized from `max_len`).
- Make inference tolerant of a small share of bad cells, for example "95% INTEGER", and write the outliers to a rejects file.
- Infer foreign keys across sheets (a `customer_id` column whose values are all found in `customers.id`).
- Parse locale-aware numbers (`1.234,56`) and currencies (`$1,200`, `€3`).
- Do incremental upserts (`INSERT ... ON CONFLICT DO UPDATE`) keyed on the detected primary key.
- Add progress reporting and parallel parsing for multi-GB files.
