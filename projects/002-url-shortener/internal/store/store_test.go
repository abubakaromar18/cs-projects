package store

import (
	"context"
	"errors"
	"path/filepath"
	"sync"
	"testing"
	"time"
)

func newTestStore(t *testing.T) *Store {
	t.Helper()
	s, err := Open(filepath.Join(t.TempDir(), "test.db"))
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { s.Close() })
	return s
}

func TestCreateGetAndDuplicate(t *testing.T) {
	s := newTestStore(t)
	ctx := context.Background()

	l, err := s.Create(ctx, "abc1234", "https://go.dev", false)
	if err != nil {
		t.Fatal(err)
	}
	got, err := s.Get(ctx, "abc1234")
	if err != nil {
		t.Fatal(err)
	}
	if got.URL != "https://go.dev" || got.Clicks != 0 || got.LastClickedAt != nil {
		t.Errorf("unexpected link %+v", got)
	}
	if !got.CreatedAt.Equal(l.CreatedAt) {
		t.Errorf("created_at mismatch: %v vs %v", got.CreatedAt, l.CreatedAt)
	}
	if _, err := s.Create(ctx, "abc1234", "https://other", false); !errors.Is(err, ErrCodeTaken) {
		t.Errorf("duplicate create err = %v, want ErrCodeTaken", err)
	}
	if _, err := s.Get(ctx, "missing"); !errors.Is(err, ErrNotFound) {
		t.Errorf("Get missing err = %v", err)
	}
}

func TestResolveCountsClicks(t *testing.T) {
	s := newTestStore(t)
	ctx := context.Background()
	fixed := time.Date(2026, 1, 2, 3, 4, 5, 0, time.UTC)
	s.now = func() time.Time { return fixed }

	s.Create(ctx, "x", "https://example.com", false)
	for i := 0; i < 3; i++ {
		url, err := s.Resolve(ctx, "x")
		if err != nil || url != "https://example.com" {
			t.Fatalf("Resolve = %q, %v", url, err)
		}
	}
	l, _ := s.Get(ctx, "x")
	if l.Clicks != 3 {
		t.Errorf("clicks = %d, want 3", l.Clicks)
	}
	if l.LastClickedAt == nil || !l.LastClickedAt.Equal(fixed) {
		t.Errorf("last_clicked_at = %v, want %v", l.LastClickedAt, fixed)
	}
	if _, err := s.Resolve(ctx, "nope"); !errors.Is(err, ErrNotFound) {
		t.Errorf("Resolve missing err = %v", err)
	}
}

func TestConcurrentClicksAreNotLost(t *testing.T) {
	s := newTestStore(t)
	ctx := context.Background()
	s.Create(ctx, "hot", "https://example.com", false)

	const workers, per = 8, 25
	var wg sync.WaitGroup
	for w := 0; w < workers; w++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for i := 0; i < per; i++ {
				if _, err := s.Resolve(ctx, "hot"); err != nil {
					t.Error(err)
				}
			}
		}()
	}
	wg.Wait()
	l, _ := s.Get(ctx, "hot")
	if l.Clicks != workers*per {
		t.Errorf("clicks = %d, want %d", l.Clicks, workers*per)
	}
}

func TestFindGeneratedByURLIgnoresCustom(t *testing.T) {
	s := newTestStore(t)
	ctx := context.Background()
	s.Create(ctx, "mine", "https://a.example", true)
	if _, err := s.FindGeneratedByURL(ctx, "https://a.example"); !errors.Is(err, ErrNotFound) {
		t.Errorf("custom alias should not be reused, err = %v", err)
	}
	s.Create(ctx, "gen1234", "https://a.example", false)
	l, err := s.FindGeneratedByURL(ctx, "https://a.example")
	if err != nil || l.Code != "gen1234" {
		t.Errorf("FindGeneratedByURL = %+v, %v", l, err)
	}
}

func TestListOrderPaginationDeleteTotals(t *testing.T) {
	s := newTestStore(t)
	ctx := context.Background()
	base := time.Date(2026, 1, 1, 0, 0, 0, 0, time.UTC)
	for i, code := range []string{"one", "two", "three"} {
		at := base.Add(time.Duration(i) * time.Minute)
		s.now = func() time.Time { return at }
		s.Create(ctx, code, "https://example.com/"+code, false)
	}
	s.Resolve(ctx, "two")
	s.Resolve(ctx, "two")

	links, err := s.List(ctx, 2, 0)
	if err != nil {
		t.Fatal(err)
	}
	if len(links) != 2 || links[0].Code != "three" || links[1].Code != "two" {
		t.Errorf("page 1 = %+v", links)
	}
	links, _ = s.List(ctx, 2, 2)
	if len(links) != 1 || links[0].Code != "one" {
		t.Errorf("page 2 = %+v", links)
	}

	st, _ := s.Totals(ctx)
	if st.Links != 3 || st.Clicks != 2 {
		t.Errorf("totals = %+v", st)
	}

	if err := s.Delete(ctx, "two"); err != nil {
		t.Fatal(err)
	}
	if err := s.Delete(ctx, "two"); !errors.Is(err, ErrNotFound) {
		t.Errorf("second delete err = %v", err)
	}
	st, _ = s.Totals(ctx)
	if st.Links != 2 || st.Clicks != 0 {
		t.Errorf("totals after delete = %+v", st)
	}
}

func TestDataSurvivesReopen(t *testing.T) {
	path := filepath.Join(t.TempDir(), "persist.db")
	s, err := Open(path)
	if err != nil {
		t.Fatal(err)
	}
	s.Create(context.Background(), "keep", "https://example.com", false)
	s.Close()

	s2, err := Open(path)
	if err != nil {
		t.Fatal(err)
	}
	defer s2.Close()
	if _, err := s2.Get(context.Background(), "keep"); err != nil {
		t.Errorf("link lost after reopen: %v", err)
	}
}
