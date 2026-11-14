package main

import (
	"bytes"
	"strings"
	"testing"
)

// drive runs the CLI with the given args and stdin, returning exit code,
// stdout and stderr.
func drive(args []string, stdin string) (int, string, string) {
	var out, errb bytes.Buffer
	code := run(args, strings.NewReader(stdin), &out, &errb)
	return code, out.String(), errb.String()
}

func TestRootCommand(t *testing.T) {
	code, out, _ := drive([]string{"root"}, "a\nb\nc\nd\n")
	if code != 0 {
		t.Fatalf("exit = %d, want 0", code)
	}
	root := strings.TrimSpace(out)
	if len(root) != 64 { // SHA-256 hex
		t.Fatalf("root %q is not 64 hex chars", root)
	}
}

// Full end-to-end flow: get a root, then verify a real line against it, and
// confirm a tampered line fails.
func TestVerifyRoundTrip(t *testing.T) {
	const data = "alpha\nbravo\ncharlie\ndelta\necho\n"
	_, out, _ := drive([]string{"root"}, data)
	root := strings.TrimSpace(out)

	code, out, _ := drive([]string{"verify", "-i", "2", "-root", root}, data)
	if code != 0 {
		t.Fatalf("verify of real line exit = %d, want 0; out=%q", code, out)
	}
	if !strings.Contains(out, "OK") {
		t.Fatalf("verify output = %q, want OK", out)
	}

	tampered := "alpha\nbravo\nCHARLIE\ndelta\necho\n"
	code, out, _ = drive([]string{"verify", "-i", "2", "-root", root}, tampered)
	if code == 0 {
		t.Fatalf("verify of tampered line exit = %d, want non-zero", code)
	}
	if !strings.Contains(out, "FAIL") {
		t.Fatalf("tampered verify output = %q, want FAIL", out)
	}
}

func TestProveEmitsJSON(t *testing.T) {
	code, out, errb := drive([]string{"prove", "-i", "1"}, "a\nb\nc\n")
	if code != 0 {
		t.Fatalf("exit = %d, want 0", code)
	}
	if !strings.Contains(out, `"index": 1`) || !strings.Contains(out, `"steps"`) {
		t.Fatalf("proof JSON missing fields: %q", out)
	}
	if !strings.Contains(errb, "root:") {
		t.Fatalf("stderr should echo the root, got %q", errb)
	}
}

func TestUnknownCommand(t *testing.T) {
	code, _, errb := drive([]string{"frobnicate"}, "")
	if code != 2 {
		t.Fatalf("exit = %d, want 2", code)
	}
	if !strings.Contains(errb, "unknown command") {
		t.Fatalf("stderr = %q", errb)
	}
}

func TestProveRequiresIndex(t *testing.T) {
	code, _, errb := drive([]string{"prove"}, "a\nb\n")
	if code != 2 {
		t.Fatalf("exit = %d, want 2", code)
	}
	if !strings.Contains(errb, "-i") {
		t.Fatalf("stderr = %q", errb)
	}
}
