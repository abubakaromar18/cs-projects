package server

import (
	"encoding/json"
	"io"
	"log"
	"net/http"
	"net/http/httptest"
	"net/url"
	"path/filepath"
	"strings"
	"testing"

	"github.com/abubakaromar18/cs-projects/projects/002-url-shortener/internal/store"
)

// testEnv starts a real HTTP server backed by a temporary SQLite file.
type testEnv struct {
	srv    *Server
	ts     *httptest.Server
	client *http.Client
}

func newEnv(t *testing.T) *testEnv {
	t.Helper()
	st, err := store.Open(filepath.Join(t.TempDir(), "srv.db"))
	if err != nil {
		t.Fatal(err)
	}
	srv := New(st, "http://sho.rt/", log.New(io.Discard, "", 0))
	ts := httptest.NewServer(srv.Handler())
	t.Cleanup(func() { ts.Close(); st.Close() })
	// Don't follow redirects so we can inspect them.
	client := &http.Client{CheckRedirect: func(*http.Request, []*http.Request) error {
		return http.ErrUseLastResponse
	}}
	return &testEnv{srv: srv, ts: ts, client: client}
}

func (e *testEnv) do(t *testing.T, method, path, body string) (*http.Response, map[string]any) {
	t.Helper()
	req, _ := http.NewRequest(method, e.ts.URL+path, strings.NewReader(body))
	if body != "" {
		req.Header.Set("Content-Type", "application/json")
	}
	resp, err := e.client.Do(req)
	if err != nil {
		t.Fatal(err)
	}
	defer resp.Body.Close()
	var m map[string]any
	if strings.HasPrefix(resp.Header.Get("Content-Type"), "application/json") {
		json.NewDecoder(resp.Body).Decode(&m)
	}
	return resp, m
}

func TestCreateRedirectAndCount(t *testing.T) {
	e := newEnv(t)
	resp, body := e.do(t, "POST", "/api/links", `{"url":"https://go.dev/doc"}`)
	if resp.StatusCode != http.StatusCreated {
		t.Fatalf("create status = %d, body %v", resp.StatusCode, body)
	}
	code := body["code"].(string)
	if len(code) != 7 {
		t.Errorf("code %q has length %d", code, len(code))
	}
	if body["short_url"] != "http://sho.rt/"+code {
		t.Errorf("short_url = %v", body["short_url"])
	}

	for i := 0; i < 2; i++ {
		r, _ := e.do(t, "GET", "/"+code, "")
		if r.StatusCode != http.StatusFound || r.Header.Get("Location") != "https://go.dev/doc" {
			t.Fatalf("redirect = %d %q", r.StatusCode, r.Header.Get("Location"))
		}
	}

	_, got := e.do(t, "GET", "/api/links/"+code, "")
	if got["clicks"].(float64) != 2 {
		t.Errorf("clicks = %v, want 2", got["clicks"])
	}
	if got["last_clicked_at"] == nil {
		t.Error("last_clicked_at should be set after a click")
	}
}

func TestSameURLReusesCode(t *testing.T) {
	e := newEnv(t)
	_, a := e.do(t, "POST", "/api/links", `{"url":"https://Example.com/x"}`)
	resp, b := e.do(t, "POST", "/api/links", `{"url":"https://example.com/x"}`)
	if resp.StatusCode != http.StatusOK {
		t.Errorf("second create status = %d, want 200", resp.StatusCode)
	}
	if a["code"] != b["code"] {
		t.Errorf("codes differ: %v vs %v", a["code"], b["code"])
	}
}

func TestCustomAlias(t *testing.T) {
	e := newEnv(t)
	resp, body := e.do(t, "POST", "/api/links", `{"url":"example.org","alias":"my-link"}`)
	if resp.StatusCode != http.StatusCreated || body["code"] != "my-link" || body["url"] != "https://example.org" {
		t.Fatalf("alias create = %d %v", resp.StatusCode, body)
	}
	resp, _ = e.do(t, "POST", "/api/links", `{"url":"https://other.org","alias":"my-link"}`)
	if resp.StatusCode != http.StatusConflict {
		t.Errorf("taken alias status = %d, want 409", resp.StatusCode)
	}
	resp, _ = e.do(t, "POST", "/api/links", `{"url":"https://other.org","alias":"api"}`)
	if resp.StatusCode != http.StatusBadRequest {
		t.Errorf("reserved alias status = %d, want 400", resp.StatusCode)
	}
}

func TestRejectsBadInput(t *testing.T) {
	e := newEnv(t)
	for _, body := range []string{
		`not json`,
		`{"url":""}`,
		`{"url":"javascript:alert(1)"}`,
		`{"url":"ftp://files.example.com"}`,
		`{"url":"https://"}`,
		`{"url":"https://bad_host!.com"}`,
		`{"url":"https://ok.example","alias":"bad alias"}`,
		`{"url":"https://example.com/` + strings.Repeat("a", 3000) + `"}`,
	} {
		resp, m := e.do(t, "POST", "/api/links", body)
		if resp.StatusCode != http.StatusBadRequest {
			t.Errorf("%.40s: status %d, want 400", body, resp.StatusCode)
		}
		if m["error"] == nil {
			t.Errorf("%.40s: missing error message", body)
		}
	}
}

func TestCollisionRetry(t *testing.T) {
	e := newEnv(t)
	codes := []string{"dupcode", "dupcode", "fresh01"}
	e.srv.generate = func() (string, error) {
		c := codes[0]
		codes = codes[1:]
		return c, nil
	}
	_, a := e.do(t, "POST", "/api/links", `{"url":"https://a.example"}`)
	_, b := e.do(t, "POST", "/api/links", `{"url":"https://b.example"}`)
	if a["code"] != "dupcode" || b["code"] != "fresh01" {
		t.Errorf("codes = %v, %v; want dupcode, fresh01", a["code"], b["code"])
	}
}

func TestUnknownCodeAndDelete(t *testing.T) {
	e := newEnv(t)
	if r, _ := e.do(t, "GET", "/nothing", ""); r.StatusCode != http.StatusNotFound {
		t.Errorf("unknown code status = %d", r.StatusCode)
	}
	e.do(t, "POST", "/api/links", `{"url":"https://a.example","alias":"gone"}`)
	if r, _ := e.do(t, "DELETE", "/api/links/gone", ""); r.StatusCode != http.StatusNoContent {
		t.Errorf("delete status = %d", r.StatusCode)
	}
	if r, _ := e.do(t, "DELETE", "/api/links/gone", ""); r.StatusCode != http.StatusNotFound {
		t.Errorf("second delete status = %d", r.StatusCode)
	}
	if r, _ := e.do(t, "GET", "/gone", ""); r.StatusCode != http.StatusNotFound {
		t.Errorf("deleted link still redirects: %d", r.StatusCode)
	}
}

func TestListAndStats(t *testing.T) {
	e := newEnv(t)
	for _, u := range []string{"https://a.example", "https://b.example", "https://c.example"} {
		e.do(t, "POST", "/api/links", `{"url":"`+u+`"}`)
	}
	_, m := e.do(t, "GET", "/api/links?limit=2", "")
	if n := len(m["links"].([]any)); n != 2 {
		t.Errorf("list returned %d links, want 2", n)
	}
	_, st := e.do(t, "GET", "/api/stats", "")
	if st["links"].(float64) != 3 {
		t.Errorf("stats = %v", st)
	}
	if r, h := e.do(t, "GET", "/healthz", ""); r.StatusCode != 200 || h["status"] != "ok" {
		t.Errorf("healthz = %d %v", r.StatusCode, h)
	}
}

func TestHTMLFormFlow(t *testing.T) {
	e := newEnv(t)
	resp, err := e.client.PostForm(e.ts.URL+"/shorten", url.Values{"url": {"https://go.dev"}, "alias": {"godev"}})
	if err != nil {
		t.Fatal(err)
	}
	page, _ := io.ReadAll(resp.Body)
	resp.Body.Close()
	if resp.StatusCode != 200 || !strings.Contains(string(page), "http://sho.rt/godev") {
		t.Errorf("form result missing short link (status %d)", resp.StatusCode)
	}

	// Errors are shown on the page, and user input is HTML-escaped.
	resp, _ = e.client.PostForm(e.ts.URL+"/shorten", url.Values{"url": {"<script>x</script>"}})
	page, _ = io.ReadAll(resp.Body)
	resp.Body.Close()
	if resp.StatusCode != http.StatusBadRequest || strings.Contains(string(page), "<script>x") {
		t.Errorf("bad form input not handled safely (status %d)", resp.StatusCode)
	}

	resp, _ = e.client.Get(e.ts.URL + "/")
	page, _ = io.ReadAll(resp.Body)
	resp.Body.Close()
	if !strings.Contains(string(page), "godev") {
		t.Error("index should list recent links")
	}
}

func TestNormalizeURL(t *testing.T) {
	cases := map[string]string{
		"example.com":                   "https://example.com",
		"  HTTP://Example.COM/Path?q=1": "http://example.com/Path?q=1",
		"https://example.com:8443/a":    "https://example.com:8443/a",
		"http://127.0.0.1:3000/x":       "http://127.0.0.1:3000/x",
		"http://[::1]:8080/":            "http://[::1]:8080/",
	}
	for in, want := range cases {
		got, err := normalizeURL(in)
		if err != nil || got != want {
			t.Errorf("normalizeURL(%q) = %q, %v; want %q", in, got, err, want)
		}
	}
}
