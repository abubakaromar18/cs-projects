package main

import (
	"bufio"
	"bytes"
	"io"
	"net"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/abubakaromar18/cs-projects/projects/073-serial-terminal/internal/serial"
)

func TestBuildConfig(t *testing.T) {
	f, err := parseFlags([]string{"-port", "x", "-baud", "9600", "-frame", "7e2", "-flow", "rtscts"}, io.Discard)
	if err != nil {
		t.Fatal(err)
	}
	cfg, err := buildConfig(f)
	if err != nil {
		t.Fatal(err)
	}
	want := serial.Config{BaudRate: 9600, DataBits: 7, Parity: serial.ParityEven, StopBits: 2, Flow: serial.FlowRTSCTS}
	if cfg != want {
		t.Fatalf("got %+v", cfg)
	}
}

func TestFlagErrors(t *testing.T) {
	if _, err := parseFlags(nil, io.Discard); err == nil {
		t.Error("missing -port should fail")
	}
	f, _ := parseFlags([]string{"-port", "x", "-flow", "xon"}, io.Discard)
	if _, err := buildConfig(f); err == nil {
		t.Error("bad flow should fail")
	}
	if err := run([]string{"-port", "x", "-eol", "bogus"}, nil, io.Discard, io.Discard); err == nil {
		t.Error("bad eol should fail")
	}
}

func TestListRuns(t *testing.T) {
	var out bytes.Buffer
	if err := run([]string{"-list"}, nil, &out, io.Discard); err != nil {
		t.Fatal(err)
	}
	if out.Len() == 0 {
		t.Fatal("no output")
	}
}

// End-to-end: run the CLI against a TCP "device" on localhost that upper-cases
// each line it receives.
func TestRunAgainstTCPDevice(t *testing.T) {
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
		defer c.Close()
		r := bufio.NewReader(c)
		for {
			line, err := r.ReadString('\n')
			if err != nil {
				return
			}
			c.Write([]byte(strings.ToUpper(line)))
		}
	}()

	logPath := filepath.Join(t.TempDir(), "rx.log")
	var stdout, stderr bytes.Buffer
	args := []string{"-port", "tcp://" + ln.Addr().String(), "-eol", "lf", "-log", logPath, "-escape"}
	if err := run(args, strings.NewReader("hello\n"), &stdout, &stderr); err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(stderr.String(), "--- connected to tcp://") || !strings.Contains(stderr.String(), "tx 6 bytes") {
		t.Errorf("stderr: %s", stderr.String())
	}
	// On console EOF the session lingers briefly so the reply is captured.
	if stdout.String() != "HELLO\n" {
		t.Errorf("stdout = %q", stdout.String())
	}
	logged, err := os.ReadFile(logPath)
	if err != nil || string(logged) != "HELLO\n" {
		t.Errorf("log = %q, %v", logged, err)
	}
}
