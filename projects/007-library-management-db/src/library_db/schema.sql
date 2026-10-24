-- Library Management DB: normalized schema (3NF) for SQLite.
--
-- Design notes
--   * Every fact lives in exactly one place. A book's title is stored once in
--     `books`; its authors and genres are many-to-many and live in junction
--     tables, so there are no repeating groups ("author1, author2, ...").
--   * A *book* (the work / ISBN) is separated from a *copy* (a physical item
--     with a barcode). A library owns many copies of one book.
--   * Availability is NOT stored. A copy is on loan iff it has a loan row with
--     returned_on IS NULL. Storing a separate "status" column would be derived
--     data that can drift out of sync (an update anomaly).
--   * Integrity rules are pushed into the database where possible: foreign
--     keys, CHECK constraints, UNIQUE constraints and a partial unique index.
--
-- Dates are stored as ISO-8601 TEXT ('YYYY-MM-DD'), which sorts correctly and
-- works with SQLite's date functions.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS authors (
    author_id   INTEGER PRIMARY KEY,
    name        TEXT    NOT NULL UNIQUE CHECK (length(trim(name)) > 0)
);

CREATE TABLE IF NOT EXISTS publishers (
    publisher_id INTEGER PRIMARY KEY,
    name         TEXT    NOT NULL UNIQUE CHECK (length(trim(name)) > 0)
);

CREATE TABLE IF NOT EXISTS genres (
    genre_id    INTEGER PRIMARY KEY,
    name        TEXT    NOT NULL UNIQUE COLLATE NOCASE
);

CREATE TABLE IF NOT EXISTS books (
    book_id         INTEGER PRIMARY KEY,
    isbn            TEXT    NOT NULL UNIQUE CHECK (length(isbn) IN (10, 13)),
    title           TEXT    NOT NULL CHECK (length(trim(title)) > 0),
    publisher_id    INTEGER REFERENCES publishers(publisher_id) ON DELETE SET NULL,
    published_year  INTEGER CHECK (published_year BETWEEN 1400 AND 2100)
);

-- Junction table: a book has 1..n authors, an author writes 0..n books.
CREATE TABLE IF NOT EXISTS book_authors (
    book_id     INTEGER NOT NULL REFERENCES books(book_id)   ON DELETE CASCADE,
    author_id   INTEGER NOT NULL REFERENCES authors(author_id) ON DELETE RESTRICT,
    position    INTEGER NOT NULL DEFAULT 1,      -- author order on the cover
    PRIMARY KEY (book_id, author_id)
);

-- Junction table: books <-> genres.
CREATE TABLE IF NOT EXISTS book_genres (
    book_id     INTEGER NOT NULL REFERENCES books(book_id)   ON DELETE CASCADE,
    genre_id    INTEGER NOT NULL REFERENCES genres(genre_id) ON DELETE CASCADE,
    PRIMARY KEY (book_id, genre_id)
);

-- Physical items. Deleting a book that still has copies is refused.
CREATE TABLE IF NOT EXISTS copies (
    copy_id     INTEGER PRIMARY KEY,
    book_id     INTEGER NOT NULL REFERENCES books(book_id) ON DELETE RESTRICT,
    barcode     TEXT    NOT NULL UNIQUE,
    acquired_on TEXT    NOT NULL DEFAULT (date('now'))
);

CREATE TABLE IF NOT EXISTS members (
    member_id   INTEGER PRIMARY KEY,
    name        TEXT    NOT NULL CHECK (length(trim(name)) > 0),
    email       TEXT    NOT NULL UNIQUE COLLATE NOCASE CHECK (email LIKE '%_@_%'),
    joined_on   TEXT    NOT NULL DEFAULT (date('now'))
);

CREATE TABLE IF NOT EXISTS loans (
    loan_id     INTEGER PRIMARY KEY,
    copy_id     INTEGER NOT NULL REFERENCES copies(copy_id)   ON DELETE RESTRICT,
    member_id   INTEGER NOT NULL REFERENCES members(member_id) ON DELETE RESTRICT,
    loaned_on   TEXT    NOT NULL,
    due_on      TEXT    NOT NULL,
    returned_on TEXT,
    renewals    INTEGER NOT NULL DEFAULT 0 CHECK (renewals >= 0),
    CHECK (due_on >= loaned_on),
    CHECK (returned_on IS NULL OR returned_on >= loaned_on)
);

-- A copy can have at most ONE open loan. This partial unique index makes a
-- double checkout impossible even if two clients race each other.
CREATE UNIQUE INDEX IF NOT EXISTS ux_loans_one_open_per_copy
    ON loans(copy_id) WHERE returned_on IS NULL;

-- Secondary indexes for the common access paths (FK columns are not indexed
-- automatically in SQLite).
CREATE INDEX IF NOT EXISTS ix_loans_member      ON loans(member_id);
CREATE INDEX IF NOT EXISTS ix_loans_open_due    ON loans(due_on) WHERE returned_on IS NULL;
CREATE INDEX IF NOT EXISTS ix_copies_book       ON copies(book_id);
CREATE INDEX IF NOT EXISTS ix_book_authors_auth ON book_authors(author_id);
CREATE INDEX IF NOT EXISTS ix_books_title       ON books(title COLLATE NOCASE);

-- ---------------------------------------------------------------------------
-- Views: derived data computed on read instead of being stored.
-- ---------------------------------------------------------------------------

-- One row per book with its authors and how many copies are free right now.
CREATE VIEW IF NOT EXISTS v_book_catalog AS
SELECT
    b.book_id,
    b.isbn,
    b.title,
    b.published_year,
    p.name AS publisher,
    (SELECT group_concat(name, ', ') FROM (
        SELECT a.name FROM book_authors ba
        JOIN authors a ON a.author_id = ba.author_id
        WHERE ba.book_id = b.book_id
        ORDER BY ba.position, a.name)) AS authors,
    (SELECT count(*) FROM copies c WHERE c.book_id = b.book_id) AS total_copies,
    (SELECT count(*) FROM copies c
      WHERE c.book_id = b.book_id
        AND NOT EXISTS (SELECT 1 FROM loans l
                        WHERE l.copy_id = c.copy_id AND l.returned_on IS NULL)
    ) AS available_copies
FROM books b
LEFT JOIN publishers p ON p.publisher_id = b.publisher_id;

-- Every loan that is still open, with names resolved.
CREATE VIEW IF NOT EXISTS v_open_loans AS
SELECT
    l.loan_id, l.loaned_on, l.due_on,
    m.member_id, m.name AS member, m.email,
    c.copy_id, c.barcode,
    b.book_id, b.title
FROM loans l
JOIN members m ON m.member_id = l.member_id
JOIN copies  c ON c.copy_id   = l.copy_id
JOIN books   b ON b.book_id   = c.book_id
WHERE l.returned_on IS NULL;
