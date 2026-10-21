// Package store persists short links in SQLite.
//
// The schema is a single table keyed by the short code. Click counting is
// done with one UPDATE ... RETURNING statement, so a redirect is a single
// atomic round trip and concurrent clicks never lose increments.
package store

import (
	"context"
	"database/sql"
	"errors"
	"fmt"
	"strings"
	"time"

	_ "github.com/mattn/go-sqlite3" // registers the "sqlite3" driver
)

var (
	// ErrNotFound means no link exists for the given code.
	ErrNotFound = errors.New("link not found")
	// ErrCodeTaken means the requested code is already in use.
	ErrCodeTaken = errors.New("code already in use")
)

// Link is one shortened URL and its statistics.
type Link struct {
	Code          string     `json:"code"`
	URL           string     `json:"url"`
	Custom        bool       `json:"custom"`
	Clicks        int64      `json:"clicks"`
	CreatedAt     time.Time  `json:"created_at"`
	LastClickedAt *time.Time `json:"last_clicked_at,omitempty"`
}

// Store wraps a SQLite database handle.
type Store struct {
	db  *sql.DB
	now func() time.Time // injectable clock for tests
}

const schema = `
CREATE TABLE IF NOT EXISTS links (
	code            TEXT PRIMARY KEY,
	url             TEXT NOT NULL,
	custom          INTEGER NOT NULL DEFAULT 0,
	clicks          INTEGER NOT NULL DEFAULT 0,
	created_at      INTEGER NOT NULL,  -- unix milliseconds
	last_clicked_at INTEGER            -- unix milliseconds, NULL until first click
);
CREATE INDEX IF NOT EXISTS idx_links_url ON links(url);
CREATE INDEX IF NOT EXISTS idx_links_created ON links(created_at);
`

// Open opens (creating if needed) the database at path and applies the schema.
func Open(path string) (*Store, error) {
	// WAL lets readers proceed while a writer is active; busy_timeout makes
	// a blocked writer wait instead of failing immediately with SQLITE_BUSY.
	dsn := fmt.Sprintf("file:%s?_journal_mode=WAL&_busy_timeout=5000&_foreign_keys=on", path)
	db, err := sql.Open("sqlite3", dsn)
	if err != nil {
		return nil, fmt.Errorf("open db: %w", err)
	}
	// SQLite allows only one writer at a time; a single connection avoids
	// lock contention entirely and is plenty for a small service.
	db.SetMaxOpenConns(1)
	if _, err := db.Exec(schema); err != nil {
		db.Close()
		return nil, fmt.Errorf("apply schema: %w", err)
	}
	return &Store{db: db, now: time.Now}, nil
}

// Close releases the database.
func (s *Store) Close() error { return s.db.Close() }

// Create inserts a new link. It returns ErrCodeTaken if code already exists.
func (s *Store) Create(ctx context.Context, code, url string, custom bool) (Link, error) {
	created := s.now().UTC().Truncate(time.Millisecond)
	_, err := s.db.ExecContext(ctx,
		`INSERT INTO links (code, url, custom, created_at) VALUES (?, ?, ?, ?)`,
		code, url, custom, created.UnixMilli())
	if err != nil {
		if isUniqueViolation(err) {
			return Link{}, ErrCodeTaken
		}
		return Link{}, fmt.Errorf("insert link: %w", err)
	}
	return Link{Code: code, URL: url, Custom: custom, CreatedAt: created}, nil
}

// Get returns the link for code without counting a click.
func (s *Store) Get(ctx context.Context, code string) (Link, error) {
	row := s.db.QueryRowContext(ctx,
		`SELECT code, url, custom, clicks, created_at, last_clicked_at FROM links WHERE code = ?`, code)
	return scanLink(row)
}

// FindGeneratedByURL returns an existing auto-generated link for url, so
// shortening the same URL twice gives the same code. Custom aliases are
// excluded: they belong to whoever chose them.
func (s *Store) FindGeneratedByURL(ctx context.Context, url string) (Link, error) {
	row := s.db.QueryRowContext(ctx,
		`SELECT code, url, custom, clicks, created_at, last_clicked_at FROM links
		 WHERE url = ? AND custom = 0 ORDER BY created_at LIMIT 1`, url)
	return scanLink(row)
}

// Resolve looks up the destination for code and records a click atomically.
func (s *Store) Resolve(ctx context.Context, code string) (string, error) {
	var url string
	err := s.db.QueryRowContext(ctx,
		`UPDATE links SET clicks = clicks + 1, last_clicked_at = ?
		 WHERE code = ? RETURNING url`,
		s.now().UTC().UnixMilli(), code).Scan(&url)
	if errors.Is(err, sql.ErrNoRows) {
		return "", ErrNotFound
	}
	if err != nil {
		return "", fmt.Errorf("resolve: %w", err)
	}
	return url, nil
}

// List returns links newest first, paginated by limit and offset.
func (s *Store) List(ctx context.Context, limit, offset int) ([]Link, error) {
	rows, err := s.db.QueryContext(ctx,
		`SELECT code, url, custom, clicks, created_at, last_clicked_at FROM links
		 ORDER BY created_at DESC, code LIMIT ? OFFSET ?`, limit, offset)
	if err != nil {
		return nil, fmt.Errorf("list: %w", err)
	}
	defer rows.Close()
	links := []Link{}
	for rows.Next() {
		l, err := scanLink(rows)
		if err != nil {
			return nil, err
		}
		links = append(links, l)
	}
	return links, rows.Err()
}

// Delete removes a link. It returns ErrNotFound if nothing was deleted.
func (s *Store) Delete(ctx context.Context, code string) error {
	res, err := s.db.ExecContext(ctx, `DELETE FROM links WHERE code = ?`, code)
	if err != nil {
		return fmt.Errorf("delete: %w", err)
	}
	if n, _ := res.RowsAffected(); n == 0 {
		return ErrNotFound
	}
	return nil
}

// Stats summarises the whole table.
type Stats struct {
	Links  int64 `json:"links"`
	Clicks int64 `json:"clicks"`
}

// Totals returns the number of links and the sum of all clicks.
func (s *Store) Totals(ctx context.Context) (Stats, error) {
	var st Stats
	err := s.db.QueryRowContext(ctx,
		`SELECT COUNT(*), COALESCE(SUM(clicks), 0) FROM links`).Scan(&st.Links, &st.Clicks)
	return st, err
}

// scanner is satisfied by both *sql.Row and *sql.Rows.
type scanner interface{ Scan(dest ...any) error }

func scanLink(sc scanner) (Link, error) {
	var (
		l       Link
		created int64
		last    sql.NullInt64
	)
	err := sc.Scan(&l.Code, &l.URL, &l.Custom, &l.Clicks, &created, &last)
	if errors.Is(err, sql.ErrNoRows) {
		return Link{}, ErrNotFound
	}
	if err != nil {
		return Link{}, fmt.Errorf("scan link: %w", err)
	}
	l.CreatedAt = time.UnixMilli(created).UTC()
	if last.Valid {
		t := time.UnixMilli(last.Int64).UTC()
		l.LastClickedAt = &t
	}
	return l, nil
}

func isUniqueViolation(err error) bool {
	// go-sqlite3 reports "UNIQUE constraint failed: links.code".
	return strings.Contains(err.Error(), "UNIQUE constraint failed")
}
