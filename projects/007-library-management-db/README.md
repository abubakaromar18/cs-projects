# 007 · Library Management DB

A small but complete **library management system** built on SQLite. The heart of it is a normalized relational schema (`schema.sql`); a Python service layer adds the circulation rules, and a CLI (`library-db`) lets you catalog books, register members, check copies in and out, and run reports.

## Features

- Catalog of books with multiple authors, genres and a publisher, stored in **third normal form**
- Books (the work, keyed by ISBN) kept separate from **copies** (physical items with barcodes)
- Checkout, return and renew, with rules: max 5 loans per member, no borrowing while something is overdue, one renewal per loan, 25¢/day late fine capped at $20
- ISBN-10/ISBN-13 check-digit validation; ISBN-10s are converted to ISBN-13 so the same book can't be entered twice
- Reports: catalog with live availability, search, overdue loans with fines, most-borrowed ranking, per-author totals, member history
- Read-only ad-hoc `sql` command for exploring the data safely
- Standard library only (`sqlite3`); `pytest` is needed just for the tests

## CS concepts demonstrated

| Concept | Where |
|---|---|
| **Normalization (1NF→3NF)**: no repeating groups, no derived or duplicated facts | `schema.sql` header and table design |
| **Many-to-many relationships** via junction tables with composite primary keys | `book_authors`, `book_genres` |
| **Declarative integrity**: FOREIGN KEY, UNIQUE, CHECK, ON DELETE CASCADE/RESTRICT/SET NULL | `schema.sql` |
| **Partial unique index** making a double checkout impossible at the DB level | `ux_loans_one_open_per_copy` |
| **Derived data computed on read** (availability is never stored, so it can't drift) | `v_book_catalog`, `v_open_loans` |
| **ACID transactions**: `BEGIN IMMEDIATE` … COMMIT/ROLLBACK, so check-then-insert is atomic | `db.transaction`, `Library.checkout` |
| **Parameterized queries** (no SQL injection), plus escaping `LIKE` wildcards | everywhere in `library.py`, `Library.search` |
| **Joins, correlated subqueries, `EXISTS`, `GROUP BY`, CTEs, window functions (`RANK()`)** | `search`, `popular`, `author_report` |
| **Indexing the access paths** (FK columns, partial index on open loans' due dates) | bottom of `schema.sql` |
| **Check-digit algorithms** (weighted mod 11 and mod 10) | `isbn.py` |
| **Least privilege**: ad-hoc queries go through a `mode=ro` connection | `cli.run_readonly` |

## Schema

```
publishers 1──* books *──* authors        (via book_authors, ordered by position)
                  │  *──* genres         (via book_genres)
                  1
                  │
                  * copies 1──* loans *──1 members
```

| Table | Key columns |
|---|---|
| `books` | `isbn` UNIQUE (ISBN-13), `title`, `publisher_id` → publishers, `published_year` |
| `copies` | `barcode` UNIQUE, `book_id` → books (RESTRICT) |
| `members` | `email` UNIQUE (case-insensitive) |
| `loans` | `copy_id`, `member_id`, `loaned_on`, `due_on`, `returned_on` (NULL = open), `renewals` |

## Layout

```
src/library_db/
  schema.sql   tables, constraints, indexes, views
  db.py        connection settings + transaction context manager
  isbn.py      ISBN-10/13 validation and conversion
  library.py   service layer: catalog, members, circulation, reports
  seed.py      sample data (CS classics, four famous members)
  cli.py       argparse front end (`library-db`)
tests/         59 pytest tests (schema constraints, rules, reports, CLI)
```

## Build, run, test

Requires Python 3.10+.

```bash
make dev                 # pip install -e '.[dev]'
make test                # python -m pytest
make demo                # fresh library.db with sample data + a few reports

# without installing
PYTHONPATH=src python3 -m library_db --db library.db seed
```

Every command accepts `--db FILE` (default `library.db`) and `--today YYYY-MM-DD` to simulate a date.

## Example session

```console
$ library-db seed
seeded: books=7, copies=10, members=4, open_loans=4, total_loans=11

$ library-db search programming
isbn           title                                              authors                                available_copies
-------------  -------------------------------------------------  -------------------------------------  ----------------
9780596517748  JavaScript: The Good Parts                         Douglas Crockford                      1
9780262510875  Structure and Interpretation of Computer Programs  Harold Abelson, Gerald Jay Sussman     0
9780131103627  The C Programming Language                         Brian W. Kernighan, Dennis M. Ritchie  1

$ library-db overdue
member        email             title                                              barcode  due_on      days_overdue  fine
------------  ----------------  -------------------------------------------------  -------  ----------  ------------  -----
Ada Lovelace  ada@example.org   Introduction to Algorithms                         C001-1   2026-10-08  16            $4.00
Alan Turing   alan@example.org  Structure and Interpretation of Computer Programs  C004-1   2026-10-18  6             $1.50

$ library-db checkout C001-2 ada@example.org
error: ada@example.org has 1 overdue loan(s); return them first

$ library-db return C001-1
returned C001-1, 16 day(s) late, fine $4.00

$ library-db popular -n 4
rank  title                                  loans
----  -------------------------------------  -----
1     Introduction to Algorithms             4
2     Designing Data-Intensive Applications  3
3     Design Patterns                        2
4     Clean Code                             1

$ library-db sql "SELECT name FROM members WHERE email LIKE 'a%'"
name
------------
Ada Lovelace
Alan Turing

$ library-db sql "DELETE FROM members"
error: attempt to write a readonly database
```

Search matches title, author or genre substrings (here the title or the "Programming Languages" genre), or an exact ISBN in either format.

## Possible extensions

- **Holds/reservations queue**: a `holds` table ordered by request time; block renewals when someone is waiting
- **Fines ledger**: persist fines and payments in a `transactions` table instead of computing them on return
- **Full-text search** with SQLite's FTS5 virtual tables and ranking by `bm25()`
- **Migrations**: version the schema with `PRAGMA user_version` and upgrade scripts
- **Port to PostgreSQL** and compare: `SERIAL`/identity columns, `EXCLUDE` constraints, real date types
- **Concurrency test**: two processes racing to check out the same copy, proving the partial index wins
- A small web front end (Flask/FastAPI) on top of the same `Library` class
