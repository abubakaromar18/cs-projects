// Package server exposes the shortener over HTTP: a small HTML page, a JSON
// API, and the redirect endpoint itself.
package server

import (
	"context"
	"embed"
	"encoding/json"
	"errors"
	"html/template"
	"log"
	"net"
	"net/http"
	"net/url"
	"regexp"
	"strconv"
	"strings"
	"time"

	"github.com/abubakaromar18/cs-projects/projects/002-url-shortener/internal/shortcode"
	"github.com/abubakaromar18/cs-projects/projects/002-url-shortener/internal/store"
)

//go:embed templates/index.html
var templateFS embed.FS

var indexTmpl = template.Must(template.ParseFS(templateFS, "templates/index.html"))

// maxURLLength guards against absurd inputs filling the database.
const maxURLLength = 2048

// hostnamePattern allows DNS-style labels (letters, digits, hyphens, dots).
var hostnamePattern = regexp.MustCompile(`^[A-Za-z0-9]([A-Za-z0-9-]*[A-Za-z0-9])?(\.[A-Za-z0-9]([A-Za-z0-9-]*[A-Za-z0-9])?)*\.?$`)

// maxGenerateAttempts bounds retries when a random code collides.
const maxGenerateAttempts = 5

// Server holds dependencies for the HTTP handlers.
type Server struct {
	store   *store.Store
	baseURL string // e.g. "http://localhost:8080", no trailing slash
	logger  *log.Logger
	// generate is swappable so tests can force collisions.
	generate func() (string, error)
}

// New builds a Server. baseURL is used to render full short links.
func New(st *store.Store, baseURL string, logger *log.Logger) *Server {
	return &Server{
		store:    st,
		baseURL:  strings.TrimRight(baseURL, "/"),
		logger:   logger,
		generate: func() (string, error) { return shortcode.Generate(shortcode.DefaultLength) },
	}
}

// Handler returns the routed, logged http.Handler.
func (s *Server) Handler() http.Handler {
	mux := http.NewServeMux()
	// Go 1.22+ patterns: method and {wildcard} matching are built in.
	mux.HandleFunc("GET /{$}", s.handleIndex)
	mux.HandleFunc("POST /shorten", s.handleShortenForm)
	mux.HandleFunc("GET /healthz", s.handleHealth)
	mux.HandleFunc("POST /api/links", s.handleCreate)
	mux.HandleFunc("GET /api/links", s.handleList)
	mux.HandleFunc("GET /api/links/{code}", s.handleGet)
	mux.HandleFunc("DELETE /api/links/{code}", s.handleDelete)
	mux.HandleFunc("GET /api/stats", s.handleStats)
	mux.HandleFunc("GET /{code}", s.handleRedirect)
	return s.logRequests(mux)
}

// ---- core logic -----------------------------------------------------------

// apiError carries an HTTP status alongside a user-facing message.
type apiError struct {
	status int
	msg    string
}

func (e *apiError) Error() string { return e.msg }

// shorten validates input and creates (or reuses) a link. The bool reports
// whether a new link was created.
func (s *Server) shorten(ctx context.Context, rawURL, alias string) (store.Link, bool, error) {
	target, err := normalizeURL(rawURL)
	if err != nil {
		return store.Link{}, false, &apiError{http.StatusBadRequest, err.Error()}
	}

	if alias != "" {
		if err := shortcode.ValidateAlias(alias); err != nil {
			return store.Link{}, false, &apiError{http.StatusBadRequest, err.Error()}
		}
		l, err := s.store.Create(ctx, alias, target, true)
		if errors.Is(err, store.ErrCodeTaken) {
			return store.Link{}, false, &apiError{http.StatusConflict, "alias already in use"}
		}
		return l, err == nil, err
	}

	// Same URL, no alias: hand back the existing code instead of a new one.
	if existing, err := s.store.FindGeneratedByURL(ctx, target); err == nil {
		return existing, false, nil
	} else if !errors.Is(err, store.ErrNotFound) {
		return store.Link{}, false, err
	}

	for attempt := 0; attempt < maxGenerateAttempts; attempt++ {
		code, err := s.generate()
		if err != nil {
			return store.Link{}, false, err
		}
		l, err := s.store.Create(ctx, code, target, false)
		if errors.Is(err, store.ErrCodeTaken) {
			continue // collision: draw another code
		}
		return l, err == nil, err
	}
	return store.Link{}, false, errors.New("could not allocate a unique code")
}

// normalizeURL accepts only absolute http(s) URLs with a host.
func normalizeURL(raw string) (string, error) {
	raw = strings.TrimSpace(raw)
	if raw == "" {
		return "", errors.New("url is required")
	}
	if len(raw) > maxURLLength {
		return "", errors.New("url is too long")
	}
	// Be forgiving: "example.com/page" becomes "https://example.com/page".
	if !strings.Contains(raw, "://") {
		raw = "https://" + raw
	}
	u, err := url.Parse(raw)
	if err != nil {
		return "", errors.New("url is not valid")
	}
	if u.Scheme != "http" && u.Scheme != "https" {
		return "", errors.New("only http and https URLs are allowed")
	}
	host := u.Hostname()
	if host == "" {
		return "", errors.New("url must include a host")
	}
	if net.ParseIP(host) == nil && !hostnamePattern.MatchString(host) {
		return "", errors.New("url host is not a valid hostname")
	}
	u.Scheme = strings.ToLower(u.Scheme)
	u.Host = strings.ToLower(u.Host)
	return u.String(), nil
}

// ---- JSON API ---------------------------------------------------------------

type linkResponse struct {
	store.Link
	ShortURL string `json:"short_url"`
}

func (s *Server) withShortURL(l store.Link) linkResponse {
	return linkResponse{Link: l, ShortURL: s.baseURL + "/" + l.Code}
}

func (s *Server) handleCreate(w http.ResponseWriter, r *http.Request) {
	var req struct {
		URL   string `json:"url"`
		Alias string `json:"alias"`
	}
	r.Body = http.MaxBytesReader(w, r.Body, 8<<10)
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeError(w, http.StatusBadRequest, "body must be JSON like {\"url\": \"...\"}")
		return
	}
	l, created, err := s.shorten(r.Context(), req.URL, req.Alias)
	if err != nil {
		s.writeErr(w, err)
		return
	}
	status := http.StatusOK
	if created {
		status = http.StatusCreated
	}
	writeJSON(w, status, s.withShortURL(l))
}

func (s *Server) handleList(w http.ResponseWriter, r *http.Request) {
	limit := queryInt(r, "limit", 20, 1, 100)
	offset := queryInt(r, "offset", 0, 0, 1<<31-1)
	links, err := s.store.List(r.Context(), limit, offset)
	if err != nil {
		s.writeErr(w, err)
		return
	}
	out := make([]linkResponse, len(links))
	for i, l := range links {
		out[i] = s.withShortURL(l)
	}
	writeJSON(w, http.StatusOK, map[string]any{"links": out, "limit": limit, "offset": offset})
}

func (s *Server) handleGet(w http.ResponseWriter, r *http.Request) {
	l, err := s.store.Get(r.Context(), r.PathValue("code"))
	if err != nil {
		s.writeErr(w, err)
		return
	}
	writeJSON(w, http.StatusOK, s.withShortURL(l))
}

func (s *Server) handleDelete(w http.ResponseWriter, r *http.Request) {
	if err := s.store.Delete(r.Context(), r.PathValue("code")); err != nil {
		s.writeErr(w, err)
		return
	}
	w.WriteHeader(http.StatusNoContent)
}

func (s *Server) handleStats(w http.ResponseWriter, r *http.Request) {
	st, err := s.store.Totals(r.Context())
	if err != nil {
		s.writeErr(w, err)
		return
	}
	writeJSON(w, http.StatusOK, st)
}

func (s *Server) handleHealth(w http.ResponseWriter, _ *http.Request) {
	writeJSON(w, http.StatusOK, map[string]string{"status": "ok"})
}

// ---- redirect ----------------------------------------------------------------

func (s *Server) handleRedirect(w http.ResponseWriter, r *http.Request) {
	target, err := s.store.Resolve(r.Context(), r.PathValue("code"))
	if errors.Is(err, store.ErrNotFound) {
		http.NotFound(w, r)
		return
	}
	if err != nil {
		s.writeErr(w, err)
		return
	}
	// 302 rather than 301: browsers cache 301s forever, which would stop
	// repeat visits from reaching us and make click counts undercount.
	w.Header().Set("Cache-Control", "no-store")
	http.Redirect(w, r, target, http.StatusFound)
}

// ---- HTML page ------------------------------------------------------------------

type pageData struct {
	Result *linkResponse
	Error  string
	URL    string
	Alias  string
	Links  []linkResponse
	Stats  store.Stats
}

func (s *Server) handleIndex(w http.ResponseWriter, r *http.Request) {
	s.renderIndex(w, r, http.StatusOK, pageData{})
}

func (s *Server) handleShortenForm(w http.ResponseWriter, r *http.Request) {
	r.Body = http.MaxBytesReader(w, r.Body, 8<<10)
	if err := r.ParseForm(); err != nil {
		s.renderIndex(w, r, http.StatusBadRequest, pageData{Error: "could not read form"})
		return
	}
	data := pageData{URL: r.PostFormValue("url"), Alias: r.PostFormValue("alias")}
	l, _, err := s.shorten(r.Context(), data.URL, data.Alias)
	status := http.StatusOK
	if err != nil {
		var ae *apiError
		if errors.As(err, &ae) {
			status, data.Error = ae.status, ae.msg
		} else {
			s.logger.Printf("shorten: %v", err)
			status, data.Error = http.StatusInternalServerError, "internal error"
		}
	} else {
		resp := s.withShortURL(l)
		data.Result = &resp
		data.URL, data.Alias = "", ""
	}
	s.renderIndex(w, r, status, data)
}

func (s *Server) renderIndex(w http.ResponseWriter, r *http.Request, status int, data pageData) {
	links, err := s.store.List(r.Context(), 10, 0)
	if err == nil {
		for _, l := range links {
			data.Links = append(data.Links, s.withShortURL(l))
		}
	}
	data.Stats, _ = s.store.Totals(r.Context())
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	w.WriteHeader(status)
	if err := indexTmpl.Execute(w, data); err != nil {
		s.logger.Printf("render: %v", err)
	}
}

// ---- helpers ----------------------------------------------------------------------

func (s *Server) writeErr(w http.ResponseWriter, err error) {
	var ae *apiError
	switch {
	case errors.As(err, &ae):
		writeError(w, ae.status, ae.msg)
	case errors.Is(err, store.ErrNotFound):
		writeError(w, http.StatusNotFound, "link not found")
	default:
		s.logger.Printf("internal error: %v", err)
		writeError(w, http.StatusInternalServerError, "internal error")
	}
}

func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(v)
}

func writeError(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, map[string]string{"error": msg})
}

// queryInt parses an integer query parameter, clamped to [min, max].
func queryInt(r *http.Request, key string, def, min, max int) int {
	v, err := strconv.Atoi(r.URL.Query().Get(key))
	if err != nil {
		return def
	}
	if v < min {
		return min
	}
	if v > max {
		return max
	}
	return v
}

// statusRecorder captures the status code for logging.
type statusRecorder struct {
	http.ResponseWriter
	status int
}

func (rec *statusRecorder) WriteHeader(code int) {
	rec.status = code
	rec.ResponseWriter.WriteHeader(code)
}

func (s *Server) logRequests(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()
		rec := &statusRecorder{ResponseWriter: w, status: http.StatusOK}
		next.ServeHTTP(rec, r)
		s.logger.Printf("%s %s %d %s", r.Method, r.URL.Path, rec.status, time.Since(start).Round(time.Microsecond))
	})
}
