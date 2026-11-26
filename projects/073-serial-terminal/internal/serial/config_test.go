package serial

import (
	"errors"
	"io"
	"net"
	"testing"
)

func TestDefaultConfigIsValid(t *testing.T) {
	c := DefaultConfig()
	if err := c.Validate(); err != nil {
		t.Fatal(err)
	}
	if got := c.String(); got != "115200 8N1" {
		t.Fatalf("String() = %q", got)
	}
}

func TestValidateRejects(t *testing.T) {
	cases := map[string]func(*Config){
		"baud":   func(c *Config) { c.BaudRate = 0 },
		"data":   func(c *Config) { c.DataBits = 9 },
		"stop":   func(c *Config) { c.StopBits = 3 },
		"parity": func(c *Config) { c.Parity = 7 },
		"flow":   func(c *Config) { c.Flow = 9 },
	}
	for name, mutate := range cases {
		c := DefaultConfig()
		mutate(&c)
		if err := c.Validate(); !errors.Is(err, ErrInvalidConfig) {
			t.Errorf("%s: want ErrInvalidConfig, got %v", name, err)
		}
	}
}

func TestParseFrame(t *testing.T) {
	tests := []struct {
		in     string
		data   int
		parity Parity
		stop   int
	}{
		{"8N1", 8, ParityNone, 1},
		{"7E1", 7, ParityEven, 1},
		{"8o2", 8, ParityOdd, 2},
		{"5N2", 5, ParityNone, 2},
	}
	for _, tt := range tests {
		c := DefaultConfig()
		if err := c.ParseFrame(tt.in); err != nil {
			t.Fatalf("%s: %v", tt.in, err)
		}
		if c.DataBits != tt.data || c.Parity != tt.parity || c.StopBits != tt.stop {
			t.Errorf("%s: got %+v", tt.in, c)
		}
		if c.String() != "115200 "+string([]byte{tt.in[0], "NOE"[tt.parity], tt.in[2]}) {
			t.Errorf("%s: round trip String() = %q", tt.in, c.String())
		}
	}
	for _, bad := range []string{"", "8N", "9N1", "8X1", "8N3", "8N11"} {
		c := DefaultConfig()
		if err := c.ParseFrame(bad); !errors.Is(err, ErrInvalidConfig) {
			t.Errorf("%q: want error, got %v", bad, err)
		}
	}
}

func TestOpenRejectsInvalidConfigBeforeTouchingDevice(t *testing.T) {
	c := DefaultConfig()
	c.DataBits = 4
	if _, err := Open("/dev/does-not-matter", c); !errors.Is(err, ErrInvalidConfig) {
		t.Fatalf("got %v", err)
	}
}

func TestOpenMissingDevice(t *testing.T) {
	if _, err := Open("/dev/definitely-not-a-port-xyz", DefaultConfig()); err == nil {
		t.Fatal("expected error")
	}
}

func TestOpenTCP(t *testing.T) {
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	defer ln.Close()
	go func() {
		c, err := ln.Accept()
		if err != nil {
			return
		}
		io.Copy(c, c) // echo device
		c.Close()
	}()
	p, err := Open("tcp://"+ln.Addr().String(), DefaultConfig())
	if err != nil {
		t.Fatal(err)
	}
	defer p.Close()
	p.Write([]byte("ping"))
	buf := make([]byte, 4)
	if _, err := io.ReadFull(p, buf); err != nil || string(buf) != "ping" {
		t.Fatalf("echo = %q, %v", buf, err)
	}
}

func TestListPortsDoesNotError(t *testing.T) {
	if _, err := ListPorts(); err != nil {
		t.Fatal(err)
	}
}
