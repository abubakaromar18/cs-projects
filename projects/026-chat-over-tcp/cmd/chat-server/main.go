// Command chat-server runs the multi-client TCP chat server.
//
//	go run ./cmd/chat-server -addr 127.0.0.1:9000
package main

import (
	"context"
	"flag"
	"log"
	"os"
	"os/signal"
	"syscall"

	"github.com/abubakaromar18/cs-projects/projects/026-chat-over-tcp/internal/server"
)

func main() {
	// Bind to localhost by default; pass -addr :9000 to accept LAN clients.
	addr := flag.String("addr", "127.0.0.1:9000", "address to listen on")
	flag.Parse()

	// Ctrl-C / SIGTERM cancel the context, triggering a graceful shutdown.
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()

	srv := server.New()
	srv.Logger = log.New(os.Stderr, "chat: ", log.LstdFlags)
	if err := srv.ListenAndServe(ctx, *addr); err != nil {
		log.Fatal(err)
	}
}
