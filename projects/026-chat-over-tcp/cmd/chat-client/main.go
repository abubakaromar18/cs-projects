// Command chat-client is a minimal terminal client for chat-server.
//
// It runs two concurrent loops: one copies lines from the server to stdout,
// the other copies lines typed on stdin to the server. Either side closing
// ends the program. (You can also just use `nc 127.0.0.1 9000`.)
package main

import (
	"bufio"
	"flag"
	"fmt"
	"io"
	"log"
	"net"
	"os"
	"strings"
)

func main() {
	addr := flag.String("addr", "127.0.0.1:9000", "server address")
	nick := flag.String("nick", "", "nickname to request on connect")
	flag.Parse()

	conn, err := net.Dial("tcp", *addr)
	if err != nil {
		log.Fatalf("connect: %v", err)
	}
	defer conn.Close()

	if *nick != "" {
		fmt.Fprintf(conn, "/nick %s\n", *nick)
	}

	serverClosed := make(chan struct{})
	go func() {
		// Server -> terminal.
		io.Copy(os.Stdout, conn)
		close(serverClosed)
	}()

	go func() {
		// Terminal -> server.
		sc := bufio.NewScanner(os.Stdin)
		for sc.Scan() {
			line := sc.Text()
			if _, err := fmt.Fprintln(conn, line); err != nil {
				return
			}
			if strings.EqualFold(strings.TrimSpace(line), "/quit") {
				return
			}
		}
		// stdin closed (Ctrl-D): tell the server we're leaving.
		fmt.Fprintln(conn, "/quit")
	}()

	<-serverClosed
	fmt.Fprintln(os.Stderr, "disconnected")
}
