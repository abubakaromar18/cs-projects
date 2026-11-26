package term

import (
	"bufio"
	"context"
	"errors"
	"fmt"
	"io"
	"strings"
	"sync"
	"sync/atomic"
	"time"
)

// ErrQuit is returned by Run when the user typed the ~. escape.
var ErrQuit = errors.New("user quit")

// Flusher is implemented by display filters that buffer (HexWriter).
type Flusher interface{ Flush() error }

// Options configures a Session.
type Options struct {
	EOL       LineEnding
	LocalEcho bool          // print what we send, for devices that don't echo
	Display   io.Writer     // where received bytes are shown (after filters)
	Log       io.Writer     // optional raw capture of received bytes
	Status    io.Writer     // local messages: help, errors, stats
	IdleFlush time.Duration // flush buffered display after this much silence
}

// Stats counts bytes in each direction.
type Stats struct{ TX, RX int64 }

// Session pumps bytes between a serial port and the console. Two concurrent
// loops run: the receive loop copies port -> display/log, and the transmit
// loop reads console lines, handles ~ escapes and writes to the port.
type Session struct {
	opts Options
	port io.ReadWriter

	mu     sync.Mutex // serialises writes to Display from rx, echo and the idle timer
	idle   *time.Timer
	tx, rx atomic.Int64
}

// NewSession validates options and fills defaults.
func NewSession(port io.ReadWriter, opts Options) *Session {
	if opts.Display == nil {
		opts.Display = io.Discard
	}
	if opts.Status == nil {
		opts.Status = io.Discard
	}
	if opts.IdleFlush == 0 {
		opts.IdleFlush = 150 * time.Millisecond
	}
	return &Session{opts: opts, port: port}
}

// Stats returns the current byte counters.
func (s *Session) Stats() Stats { return Stats{TX: s.tx.Load(), RX: s.rx.Load()} }

// Run blocks until the console hits EOF, the user types ~., the port fails,
// or ctx is cancelled. The caller owns the port and should Close it after
// Run returns; that also ends the receive goroutine.
func (s *Session) Run(ctx context.Context, console io.Reader) error {
	rxErr := make(chan error, 1)
	go func() { rxErr <- s.receive() }()

	lines := make(chan string)
	consoleErr := make(chan error, 1)
	go func() {
		r := bufio.NewReader(console)
		for {
			line, err := r.ReadString('\n')
			if line != "" {
				select {
				case lines <- line:
				case <-ctx.Done():
					return
				}
			}
			if err != nil {
				consoleErr <- err
				return
			}
		}
	}()

	for {
		select {
		case <-ctx.Done():
			return ctx.Err()
		case err := <-rxErr:
			if errors.Is(err, io.EOF) {
				fmt.Fprintln(s.opts.Status, "--- device closed the connection")
				return nil
			}
			return fmt.Errorf("read: %w", err)
		case err := <-consoleErr:
			if errors.Is(err, io.EOF) {
				// Give in-flight replies a moment to arrive before returning,
				// which makes piped scripts (echo AT | serialterm) useful.
				select {
				case <-time.After(s.opts.IdleFlush * 2):
				case <-ctx.Done():
				}
				s.flush()
				return nil
			}
			return err
		case line := <-lines:
			if err := s.handleLine(line); err != nil {
				return err
			}
		}
	}
}

// handleLine interprets ~ escapes (like ssh and cu) or sends the line.
func (s *Session) handleLine(line string) error {
	trimmed := strings.TrimRight(line, "\r\n")
	switch {
	case trimmed == "~.":
		return ErrQuit
	case trimmed == "~?":
		fmt.Fprint(s.opts.Status, helpText)
		return nil
	case trimmed == "~s":
		st := s.Stats()
		fmt.Fprintf(s.opts.Status, "--- tx %d bytes, rx %d bytes\n", st.TX, st.RX)
		return nil
	case strings.HasPrefix(trimmed, "~b"):
		data, err := ParseHexBytes(strings.TrimPrefix(trimmed, "~b"))
		if err != nil {
			fmt.Fprintf(s.opts.Status, "--- %v\n", err)
			return nil
		}
		return s.send(data)
	case strings.HasPrefix(trimmed, "~~"):
		trimmed = trimmed[1:] // literal leading tilde
	}
	return s.send(s.opts.EOL.Encode(trimmed))
}

const helpText = `--- escapes (type at the start of a line):
---   ~.        quit
---   ~?        this help
---   ~s        byte counters
---   ~b HEX    send raw bytes, e.g. ~b 01 03 00 00 00 0a
---   ~~text    send a line starting with ~
`

func (s *Session) send(data []byte) error {
	n, err := s.port.Write(data)
	s.tx.Add(int64(n))
	if err != nil {
		return fmt.Errorf("write: %w", err)
	}
	if s.opts.LocalEcho {
		s.mu.Lock()
		s.opts.Display.Write(data)
		s.mu.Unlock()
	}
	return nil
}

func (s *Session) receive() error {
	buf := make([]byte, 4096)
	for {
		n, err := s.port.Read(buf)
		if n > 0 {
			s.rx.Add(int64(n))
			if s.opts.Log != nil {
				s.opts.Log.Write(buf[:n])
			}
			s.mu.Lock()
			s.opts.Display.Write(buf[:n])
			s.armIdle()
			s.mu.Unlock()
		}
		if err != nil {
			return err
		}
	}
}

// armIdle (re)starts the idle timer; caller holds mu.
func (s *Session) armIdle() {
	if _, ok := s.opts.Display.(Flusher); !ok {
		return
	}
	if s.idle == nil {
		s.idle = time.AfterFunc(s.opts.IdleFlush, s.flush)
	} else {
		s.idle.Reset(s.opts.IdleFlush)
	}
}

func (s *Session) flush() {
	s.mu.Lock()
	defer s.mu.Unlock()
	if f, ok := s.opts.Display.(Flusher); ok {
		f.Flush()
	}
}
