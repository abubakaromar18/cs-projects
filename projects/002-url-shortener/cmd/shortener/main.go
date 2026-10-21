// Command shortener runs the URL shortener HTTP service.
//
//	go run ./cmd/shortener -addr :8080 -db shortener.db
package main

import (
	"context"
	"errors"
	"flag"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/abubakaromar18/cs-projects/projects/002-url-shortener/internal/server"
	"github.com/abubakaromar18/cs-projects/projects/002-url-shortener/internal/store"
)

func main() {
	addr := flag.String("addr", "127.0.0.1:8080", "listen address")
	dbPath := flag.String("db", "shortener.db", "SQLite database file")
	baseURL := flag.String("base-url", "", "public base URL for short links (default http://<addr>)")
	flag.Parse()

	if *baseURL == "" {
		*baseURL = "http://" + *addr
	}

	logger := log.New(os.Stdout, "shortener ", log.LstdFlags)

	st, err := store.Open(*dbPath)
	if err != nil {
		logger.Fatalf("opening store: %v", err)
	}
	defer st.Close()

	httpSrv := &http.Server{
		Addr:              *addr,
		Handler:           server.New(st, *baseURL, logger).Handler(),
		ReadHeaderTimeout: 5 * time.Second,
		ReadTimeout:       10 * time.Second,
		WriteTimeout:      10 * time.Second,
		IdleTimeout:       60 * time.Second,
	}

	// Shut down cleanly on Ctrl-C / SIGTERM so in-flight requests finish
	// and the SQLite file is closed properly.
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	go func() {
		logger.Printf("listening on %s (db %s, base %s)", *addr, *dbPath, *baseURL)
		if err := httpSrv.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
			logger.Fatalf("server: %v", err)
		}
	}()

	<-ctx.Done()
	logger.Println("shutting down")
	shutdownCtx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	if err := httpSrv.Shutdown(shutdownCtx); err != nil {
		logger.Printf("shutdown: %v", err)
	}
}
