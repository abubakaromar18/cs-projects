package term

import (
	"bytes"
	"context"
	"errors"
	"io"
	"net"
	"strings"
	"sync"
	"testing"
	"time"
)

// syncBuf is a goroutine-safe bytes.Buffer for capturing display output.
type syncBuf struct {
	mu sync.Mutex
	b  bytes.Buffer
}

func (s *syncBuf) Write(p []byte) (int, error) { s.mu.Lock(); defer s.mu.Unlock(); return s.b.Write(p) }
func (s *syncBuf) String() string              { s.mu.Lock(); defer s.mu.Unlock(); return s.b.String() }

// fakeDevice is the far end of an in-memory pipe. It answers "AT\r" with
// "OK\r\n" and records everything it receives.
func fakeDevice(t *testing.T) (port net.Conn, received func() string) {
	t.Helper()
	ours, theirs := net.Pipe()
	var mu sync.Mutex
	var got bytes.Buffer
	go func() {
		buf := make([]byte, 256)
		for {
			n, err := theirs.Read(buf)
			if n > 0 {
				mu.Lock()
				got.Write(buf[:n])
				mu.Unlock()
				if bytes.Contains(buf[:n], []byte("AT\r")) {
					theirs.Write([]byte("OK\r\n"))
				}
			}
			if err != nil {
				return
			}
		}
	}()
	t.Cleanup(func() { ours.Close(); theirs.Close() })
	return ours, func() string { mu.Lock(); defer mu.Unlock(); return got.String() }
}

func waitFor(t *testing.T, cond func() bool) {
	t.Helper()
	deadline := time.Now().Add(2 * time.Second)
	for !cond() {
		if time.Now().After(deadline) {
			t.Fatal("timed out")
		}
		time.Sleep(5 * time.Millisecond)
	}
}

func TestSessionSendsLinesAndShowsReplies(t *testing.T) {
	port, received := fakeDevice(t)
	var display, status syncBuf
	s := NewSession(port, Options{EOL: EOLCR, Display: &display, Status: &status, IdleFlush: 10 * time.Millisecond})

	err := s.Run(context.Background(), strings.NewReader("AT\n"))
	if err != nil {
		t.Fatal(err)
	}
	waitFor(t, func() bool { return display.String() == "OK\r\n" })
	if received() != "AT\r" {
		t.Fatalf("device got %q", received())
	}
	if st := s.Stats(); st.TX != 3 || st.RX != 4 {
		t.Fatalf("stats %+v", st)
	}
}

func TestSessionEscapes(t *testing.T) {
	port, received := fakeDevice(t)
	var display, status syncBuf
	s := NewSession(port, Options{EOL: EOLLF, Display: &display, Status: &status, IdleFlush: 10 * time.Millisecond})

	in := "~?\n~b 01 03 ff\n~b nothex\n~~tilde\n~s\n~.\nnever sent\n"
	err := s.Run(context.Background(), strings.NewReader(in))
	if !errors.Is(err, ErrQuit) {
		t.Fatalf("want ErrQuit, got %v", err)
	}
	waitFor(t, func() bool { return strings.HasSuffix(received(), "~tilde\n") })
	if got := received(); got != "\x01\x03\xff~tilde\n" {
		t.Fatalf("device got %q", got)
	}
	st := status.String()
	for _, want := range []string{"~.        quit", "bad hex", "tx 10 bytes"} {
		if !strings.Contains(st, want) {
			t.Errorf("status missing %q:\n%s", want, st)
		}
	}
}

func TestSessionLocalEchoAndLog(t *testing.T) {
	port, _ := fakeDevice(t)
	var display, status, log syncBuf
	s := NewSession(port, Options{EOL: EOLCR, LocalEcho: true, Display: &display, Status: &status, Log: &log, IdleFlush: 10 * time.Millisecond})
	if err := s.Run(context.Background(), strings.NewReader("AT\n")); err != nil {
		t.Fatal(err)
	}
	waitFor(t, func() bool { return strings.Contains(display.String(), "OK") })
	if display.String() != "AT\rOK\r\n" {
		t.Fatalf("display %q", display.String())
	}
	if log.String() != "OK\r\n" { // log is receive-only and raw
		t.Fatalf("log %q", log.String())
	}
}

func TestSessionHexIdleFlush(t *testing.T) {
	port, _ := fakeDevice(t)
	var out syncBuf
	s := NewSession(port, Options{EOL: EOLCR, Display: NewHexWriter(&out), IdleFlush: 10 * time.Millisecond})
	// Console stays open (pipe never written), so only the idle timer can flush.
	pr, pw := io.Pipe()
	defer pw.Close()
	ctx, cancel := context.WithCancel(context.Background())
	done := make(chan error, 1)
	go func() { done <- s.Run(ctx, pr) }()
	pw.Write([]byte("AT\n"))
	waitFor(t, func() bool { return strings.Contains(out.String(), "|OK..|") })
	cancel()
	if err := <-done; !errors.Is(err, context.Canceled) {
		t.Fatalf("got %v", err)
	}
}

func TestSessionDeviceHangup(t *testing.T) {
	ours, theirs := net.Pipe()
	s := NewSession(ours, Options{})
	pr, pw := io.Pipe()
	defer pw.Close()
	done := make(chan error, 1)
	go func() { done <- s.Run(context.Background(), pr) }()
	theirs.Close()
	select {
	case err := <-done:
		if err != nil {
			t.Fatalf("hangup should be a clean exit, got %v", err)
		}
	case <-time.After(2 * time.Second):
		t.Fatal("Run did not notice the hangup")
	}
}
