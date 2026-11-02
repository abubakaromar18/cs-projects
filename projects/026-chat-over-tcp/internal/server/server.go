// Package server implements a multi-client TCP chat server.
//
// Concurrency design (the "hub" pattern, CSP style):
//
//   - One goroutine — the hub — owns all shared state (the set of clients
//     and their nicknames). Nobody else touches that state, so no mutex is
//     needed; other goroutines talk to the hub by sending events on a channel.
//   - Each connection gets two goroutines: a reader that turns incoming lines
//     into events for the hub, and a writer that drains the client's buffered
//     outbox onto the socket.
//   - The hub never blocks on a slow client: if a client's outbox is full the
//     hub drops that client instead of stalling the whole room.
package server

import (
	"bufio"
	"context"
	"errors"
	"fmt"
	"io"
	"log"
	"net"
	"sort"
	"strings"
	"sync"
	"time"

	"github.com/abubakaromar18/cs-projects/projects/026-chat-over-tcp/internal/protocol"
)

// outboxSize is how many pending lines a client may have queued before it is
// considered too slow and disconnected.
const outboxSize = 64

// client is one connected user. Only the hub reads or writes nick.
type client struct {
	id     int
	conn   net.Conn
	nick   string
	outbox chan string   // lines waiting to be written to conn
	quit   chan struct{} // closed to tell the writer to flush and hang up
	once   sync.Once     // guards closing quit
}

// send queues a line for the client without blocking. It reports false if
// the outbox is full (the client is not keeping up).
func (c *client) send(line string) bool {
	select {
	case c.outbox <- line:
		return true
	default:
		return false
	}
}

// close asks the writer to flush what is queued and close the connection.
// It is safe to call from any goroutine, any number of times. The outbox
// itself is never closed, so a late send can never panic.
func (c *client) close() { c.once.Do(func() { close(c.quit) }) }

// Event kinds delivered to the hub.
type eventKind int

const (
	evJoin eventKind = iota
	evLine
	evLeave
)

type event struct {
	kind   eventKind
	client *client
	line   string
}

// Server is a chat server. Create one with New and start it with Serve.
type Server struct {
	Logger *log.Logger // optional; defaults to a discard logger

	events  chan event
	clients map[*client]bool // owned by the hub goroutine
	nextID  int              // owned by the hub goroutine
	hubDone chan struct{}    // closed when the hub goroutine exits

	wg sync.WaitGroup // tracks per-connection goroutines
}

// New returns a ready-to-use Server.
func New() *Server {
	return &Server{
		Logger:  log.New(io.Discard, "", 0),
		events:  make(chan event, 128),
		clients: make(map[*client]bool),
		hubDone: make(chan struct{}),
	}
}

// ListenAndServe listens on addr and serves until ctx is cancelled.
func (s *Server) ListenAndServe(ctx context.Context, addr string) error {
	ln, err := net.Listen("tcp", addr)
	if err != nil {
		return err
	}
	return s.Serve(ctx, ln)
}

// Serve accepts connections on ln until ctx is cancelled, then closes every
// client connection and waits for their goroutines to exit.
func (s *Server) Serve(ctx context.Context, ln net.Listener) error {
	s.Logger.Printf("listening on %s", ln.Addr())

	// A private cancel lets a fatal Accept error shut everything down too.
	ctx, cancel := context.WithCancel(ctx)
	defer cancel()

	go func() {
		s.runHub(ctx)
		close(s.hubDone)
	}()

	// Closing the listener is how we unblock Accept on shutdown.
	go func() {
		<-ctx.Done()
		ln.Close()
	}()

	for {
		conn, err := ln.Accept()
		if err != nil {
			if ctx.Err() != nil {
				break // normal shutdown
			}
			var ne net.Error
			if errors.As(err, &ne) && ne.Timeout() {
				time.Sleep(50 * time.Millisecond)
				continue
			}
			cancel()
			<-s.hubDone
			s.wg.Wait()
			return err
		}
		s.wg.Add(1)
		go s.handleConn(ctx, conn)
	}

	<-s.hubDone // hub closes all client connections on exit...
	s.wg.Wait() // ...which lets every reader/writer goroutine finish.
	s.Logger.Printf("server stopped")
	return nil
}

// handleConn runs the reader loop for one connection and starts its writer.
func (s *Server) handleConn(ctx context.Context, conn net.Conn) {
	defer s.wg.Done()
	c := &client{conn: conn, outbox: make(chan string, outboxSize), quit: make(chan struct{})}

	// Writer goroutine: owns all writes to conn.
	writerDone := make(chan struct{})
	go func() {
		defer close(writerDone)
		defer conn.Close()
		w := bufio.NewWriter(conn)
		write := func(line string) bool {
			_, err := w.WriteString(line + "\n")
			return err == nil
		}
		for {
			select {
			case line := <-c.outbox:
				if !write(line) {
					return
				}
				// Flush only when nothing else is queued, batching bursts.
				if len(c.outbox) == 0 && w.Flush() != nil {
					return
				}
			case <-c.quit:
				// Drain whatever is already queued (e.g. "*** bye"), then hang up.
				for {
					select {
					case line := <-c.outbox:
						if !write(line) {
							return
						}
					default:
						w.Flush()
						return
					}
				}
			}
		}
	}()

	if !s.emit(ctx, event{kind: evJoin, client: c}) {
		s.closeAfterHub(c)
		<-writerDone
		return
	}

	// On shutdown, expire the read deadline so the blocked Scan below returns.
	// (We don't Close here so the writer can still flush a goodbye line.)
	stop := context.AfterFunc(ctx, func() { conn.SetReadDeadline(time.Now()) })
	defer stop()

	sc := bufio.NewScanner(conn)
	sc.Buffer(make([]byte, 0, 256), protocol.MaxLineLen)
	for sc.Scan() {
		if !s.emit(ctx, event{kind: evLine, client: c, line: sc.Text()}) {
			break
		}
	}
	// EOF, read error, line too long, or server shutting down.
	if !s.emit(ctx, event{kind: evLeave, client: c}) {
		s.closeAfterHub(c) // shutting down; the hub can't hear us
	}
	<-writerDone
}

// closeAfterHub waits for the hub to finish its shutdown broadcast (so the
// client still receives "server shutting down") and then stops the writer.
func (s *Server) closeAfterHub(c *client) {
	<-s.hubDone
	c.close()
}

// emit delivers an event to the hub unless the server is shutting down.
func (s *Server) emit(ctx context.Context, ev event) bool {
	select {
	case s.events <- ev:
		return true
	case <-ctx.Done():
		return false
	}
}

// runHub is the single goroutine that owns s.clients.
func (s *Server) runHub(ctx context.Context) {
	for {
		select {
		case <-ctx.Done():
			for c := range s.clients {
				c.send("*** server shutting down")
				s.disconnect(c)
			}
			return
		case ev := <-s.events:
			switch ev.kind {
			case evJoin:
				s.join(ev.client)
			case evLine:
				if s.clients[ev.client] {
					s.handleLine(ev.client, ev.line)
				}
			case evLeave:
				if s.clients[ev.client] {
					s.disconnect(ev.client)
					s.broadcast(nil, fmt.Sprintf("*** %s left", ev.client.nick))
				} else {
					ev.client.close()
				}
			}
		}
	}
}

func (s *Server) join(c *client) {
	s.nextID++
	c.id = s.nextID
	c.nick = s.uniqueNick(fmt.Sprintf("guest%d", c.id))
	s.clients[c] = true
	s.Logger.Printf("%s connected from %s", c.nick, c.conn.RemoteAddr())
	s.deliver(c, fmt.Sprintf("*** welcome, you are %s (%d online). Type /help for commands.", c.nick, len(s.clients)))
	s.broadcast(c, fmt.Sprintf("*** %s joined", c.nick))
}

// disconnect removes c from the room and shuts down its writer, which in
// turn closes the socket and unblocks the reader.
func (s *Server) disconnect(c *client) {
	delete(s.clients, c)
	c.close()
	s.Logger.Printf("%s disconnected", c.nick)
}

func (s *Server) handleLine(c *client, line string) {
	cmd, err := protocol.Parse(line)
	if errors.Is(err, protocol.ErrEmpty) {
		return
	}
	if err != nil {
		s.deliver(c, "!!! "+err.Error())
		return
	}

	switch cmd.Kind {
	case protocol.KindSay:
		s.broadcast(c, fmt.Sprintf("<%s> %s", c.nick, cmd.Text))
	case protocol.KindMe:
		s.broadcast(nil, fmt.Sprintf("* %s %s", c.nick, cmd.Text))
	case protocol.KindNick:
		if cmd.Target == c.nick {
			return
		}
		if s.findNick(cmd.Target) != nil {
			s.deliver(c, fmt.Sprintf("!!! nickname %q is taken", cmd.Target))
			return
		}
		old := c.nick
		c.nick = cmd.Target
		s.broadcast(nil, fmt.Sprintf("*** %s is now known as %s", old, c.nick))
	case protocol.KindMsg:
		to := s.findNick(cmd.Target)
		if to == nil {
			s.deliver(c, fmt.Sprintf("!!! no such user %q", cmd.Target))
			return
		}
		s.deliver(to, fmt.Sprintf("[pm from %s] %s", c.nick, cmd.Text))
		s.deliver(c, fmt.Sprintf("[pm to %s] %s", to.nick, cmd.Text))
	case protocol.KindWho:
		s.deliver(c, fmt.Sprintf("*** online (%d): %s", len(s.clients), strings.Join(s.nicks(), ", ")))
	case protocol.KindHelp:
		for _, l := range strings.Split(protocol.HelpText, "\n") {
			s.deliver(c, l)
		}
	case protocol.KindQuit:
		s.deliver(c, "*** bye")
		s.disconnect(c)
		s.broadcast(nil, fmt.Sprintf("*** %s left", c.nick))
	}
}

// deliver sends a line to one client, dropping it if it is too slow.
func (s *Server) deliver(c *client, line string) {
	if !c.send(line) {
		s.Logger.Printf("%s is too slow; disconnecting", c.nick)
		s.disconnect(c)
	}
}

// broadcast sends line to every client except skip (which may be nil).
func (s *Server) broadcast(skip *client, line string) {
	for c := range s.clients {
		if c != skip {
			s.deliver(c, line)
		}
	}
}

func (s *Server) findNick(nick string) *client {
	for c := range s.clients {
		if strings.EqualFold(c.nick, nick) {
			return c
		}
	}
	return nil
}

func (s *Server) uniqueNick(base string) string {
	nick := base
	for i := 2; s.findNick(nick) != nil; i++ {
		nick = fmt.Sprintf("%s_%d", base, i)
	}
	return nick
}

func (s *Server) nicks() []string {
	out := make([]string, 0, len(s.clients))
	for c := range s.clients {
		out = append(out, c.nick)
	}
	sort.Strings(out)
	return out
}
