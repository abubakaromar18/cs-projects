package server

import (
	"bufio"
	"context"
	"net"
	"strings"
	"sync"
	"testing"
	"time"
)

// startServer runs a server on a random localhost port and returns its
// address plus a function that shuts it down and waits for it to exit.
func startServer(t *testing.T) (string, func()) {
	t.Helper()
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	ctx, cancel := context.WithCancel(context.Background())
	done := make(chan error, 1)
	go func() { done <- New().Serve(ctx, ln) }()

	var once sync.Once
	stop := func() {
		once.Do(func() {
			cancel()
			select {
			case err := <-done:
				if err != nil {
					t.Errorf("Serve returned %v", err)
				}
			case <-time.After(3 * time.Second):
				t.Error("server did not shut down in time")
			}
		})
	}
	t.Cleanup(stop)
	return ln.Addr().String(), stop
}

// testClient is a thin line-oriented wrapper around a TCP connection.
type testClient struct {
	t    *testing.T
	conn net.Conn
	r    *bufio.Reader
}

func dial(t *testing.T, addr string) *testClient {
	t.Helper()
	conn, err := net.Dial("tcp", addr)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { conn.Close() })
	c := &testClient{t: t, conn: conn, r: bufio.NewReader(conn)}
	c.expect("*** welcome")
	return c
}

func (c *testClient) say(line string) {
	c.t.Helper()
	if _, err := c.conn.Write([]byte(line + "\n")); err != nil {
		c.t.Fatal(err)
	}
}

func (c *testClient) readLine() (string, error) {
	c.conn.SetReadDeadline(time.Now().Add(2 * time.Second))
	line, err := c.r.ReadString('\n')
	return strings.TrimRight(line, "\n"), err
}

// expect reads lines until one contains want, failing on timeout.
func (c *testClient) expect(want string) string {
	c.t.Helper()
	for {
		line, err := c.readLine()
		if err != nil {
			c.t.Fatalf("waiting for %q: %v", want, err)
		}
		if strings.Contains(line, want) {
			return line
		}
	}
}

// nick renames the client and waits for the confirmation broadcast.
func (c *testClient) nick(name string) {
	c.t.Helper()
	c.say("/nick " + name)
	c.expect("is now known as " + name)
}

func TestWelcomeAndGuestNames(t *testing.T) {
	addr, _ := startServer(t)
	a := dial(t, addr)
	a.say("/who")
	if line := a.expect("online"); !strings.Contains(line, "guest1") {
		t.Fatalf("unexpected /who: %q", line)
	}
}

func TestBroadcast(t *testing.T) {
	addr, _ := startServer(t)
	alice := dial(t, addr)
	alice.nick("alice")
	bob := dial(t, addr)
	alice.expect("joined")
	bob.nick("bob")
	alice.expect("is now known as bob")

	alice.say("hello everyone")
	if got := bob.expect("hello"); got != "<alice> hello everyone" {
		t.Fatalf("bob got %q", got)
	}

	bob.say("/me waves")
	alice.expect("* bob waves")
}

func TestSenderDoesNotReceiveOwnMessage(t *testing.T) {
	addr, _ := startServer(t)
	a := dial(t, addr)
	b := dial(t, addr)
	a.expect("joined")

	a.say("ping")
	b.expect("ping")
	// The next thing a sees must be the /who reply, not its own "ping".
	a.say("/who")
	if line, _ := a.readLine(); !strings.HasPrefix(line, "*** online") {
		t.Fatalf("a received %q, expected /who reply", line)
	}
}

func TestPrivateMessage(t *testing.T) {
	addr, _ := startServer(t)
	alice := dial(t, addr)
	alice.nick("alice")
	bob := dial(t, addr)
	bob.nick("bob")
	carol := dial(t, addr)
	carol.nick("carol")

	alice.say("/msg bob secret plan")
	if got := bob.expect("pm from"); got != "[pm from alice] secret plan" {
		t.Fatalf("bob got %q", got)
	}
	alice.expect("[pm to bob] secret plan")

	// Carol must not see the private message: her next line is /who.
	carol.say("/who")
	if line := carol.expect("***"); strings.Contains(line, "secret") {
		t.Fatalf("carol saw pm: %q", line)
	}

	alice.say("/msg nobody hi")
	alice.expect(`no such user "nobody"`)
}

func TestNickConflict(t *testing.T) {
	addr, _ := startServer(t)
	a := dial(t, addr)
	a.nick("alice")
	b := dial(t, addr)
	b.say("/nick ALICE") // nicknames are case-insensitive
	b.expect(`nickname "ALICE" is taken`)
	b.say("/nick bad!name")
	b.expect("!!! nickname must be")
}

func TestUnknownCommand(t *testing.T) {
	addr, _ := startServer(t)
	a := dial(t, addr)
	a.say("/dance")
	a.expect("!!! unknown command")
	a.say("/help")
	a.expect("/msg <name> <text>")
}

func TestQuitAndDisconnectNotifyOthers(t *testing.T) {
	addr, _ := startServer(t)
	a := dial(t, addr)
	a.nick("alice")
	b := dial(t, addr)
	b.nick("bob")
	c := dial(t, addr)
	c.nick("carol")

	b.say("/quit")
	b.expect("*** bye")
	if _, err := b.readLine(); err == nil {
		t.Fatal("expected connection to be closed after /quit")
	}
	a.expect("*** bob left")

	c.conn.Close() // abrupt disconnect
	a.expect("*** carol left")

	a.say("/who")
	if line := a.expect("online"); line != "*** online (1): alice" {
		t.Fatalf("got %q", line)
	}
}

func TestManyClientsConcurrently(t *testing.T) {
	addr, _ := startServer(t)
	listener := dial(t, addr)
	listener.nick("listener")

	const n = 20
	var wg sync.WaitGroup
	for i := 0; i < n; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			conn, err := net.Dial("tcp", addr)
			if err != nil {
				t.Error(err)
				return
			}
			defer conn.Close()
			conn.Write([]byte("hi from a goroutine\n/quit\n"))
			// Wait for the server to close us so the message is processed.
			bufio.NewReader(conn).ReadString(0)
		}()
	}
	wg.Wait()

	got := 0
	for got < n {
		line, err := listener.readLine()
		if err != nil {
			t.Fatalf("received %d/%d messages: %v", got, n, err)
		}
		if strings.HasSuffix(line, "> hi from a goroutine") {
			got++
		}
	}
}

func TestShutdownClosesClients(t *testing.T) {
	addr, stop := startServer(t)
	a := dial(t, addr)
	stop()
	a.expect("server shutting down")
	if _, err := a.readLine(); err == nil {
		t.Fatal("expected EOF after shutdown")
	}
}
