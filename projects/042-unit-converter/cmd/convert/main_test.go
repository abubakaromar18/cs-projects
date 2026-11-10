package main

import (
	"bytes"
	"strings"
	"testing"
)

func runCLI(t *testing.T, stdin string, args ...string) (int, string, string) {
	t.Helper()
	var out, errb bytes.Buffer
	code := run(args, strings.NewReader(stdin), &out, &errb)
	return code, out.String(), errb.String()
}

func TestOneShot(t *testing.T) {
	code, out, _ := runCLI(t, "", "10", "km", "to", "mi")
	if code != 0 || out != "10 km = 6.21371 mi\n" {
		t.Fatalf("code=%d out=%q", code, out)
	}
}

func TestNegativeNumberNotAFlag(t *testing.T) {
	code, out, stderr := runCLI(t, "", "-40", "C", "to", "F")
	if code != 0 || out != "-40 C = -40 F\n" {
		t.Fatalf("code=%d out=%q err=%q", code, out, stderr)
	}
}

func TestPrecisionAndGrouping(t *testing.T) {
	_, out, _ := runCLI(t, "", "-p", "3", "1", "mi", "ft")
	if out != "1 mi = 5280 ft\n" {
		t.Fatalf("out=%q", out)
	}
	_, out, _ = runCLI(t, "", "-g", "1", "GB", "B")
	if out != "1 GB = 1,000,000,000 B\n" {
		t.Fatalf("out=%q", out)
	}
}

func TestAllUnits(t *testing.T) {
	code, out, _ := runCLI(t, "", "-all", "0", "C")
	if code != 0 {
		t.Fatalf("code=%d", code)
	}
	for _, want := range []string{"273.15", "K", "32", "F", "491.67", "R"} {
		if !strings.Contains(out, want) {
			t.Errorf("missing %q in:\n%s", want, out)
		}
	}
}

func TestNoTargetShowsAll(t *testing.T) {
	_, out, _ := runCLI(t, "", "1", "KiB")
	if !strings.Contains(out, "1024") || !strings.Contains(out, "8192") {
		t.Fatalf("out=%s", out)
	}
}

func TestList(t *testing.T) {
	code, out, _ := runCLI(t, "", "-list", "mass")
	if code != 0 || !strings.Contains(out, "[mass]") || strings.Contains(out, "[length]") {
		t.Fatalf("code=%d out=%s", code, out)
	}
	code, _, errOut := runCLI(t, "", "-list", "volume")
	if code != 1 || !strings.Contains(errOut, "unknown category") {
		t.Fatalf("code=%d err=%s", code, errOut)
	}
}

func TestErrors(t *testing.T) {
	code, _, errOut := runCLI(t, "", "1", "kg", "to", "m")
	if code != 1 || !strings.Contains(errOut, "incompatible") {
		t.Fatalf("code=%d err=%q", code, errOut)
	}
	if code, _, _ := runCLI(t, "", "-p", "0", "1", "m"); code != 2 {
		t.Fatalf("bad -p should exit 2, got %d", code)
	}
	if code, _, _ := runCLI(t, "", "-nope"); code != 2 {
		t.Fatalf("bad flag should exit 2, got %d", code)
	}
	if code, _, _ := runCLI(t, "", "-h"); code != 0 {
		t.Fatalf("-h should exit 0, got %d", code)
	}
}

func TestREPL(t *testing.T) {
	input := "# comment\n\n1 kg lb\nbogus\n32 F to C\nquit\n1 m cm\n"
	code, out, errOut := runCLI(t, input)
	if code != 1 {
		t.Errorf("expected exit 1 because one line failed, got %d", code)
	}
	if !strings.Contains(out, "1 kg = 2.20462 lb") || !strings.Contains(out, "32 F = 0 C") {
		t.Errorf("out=%q", out)
	}
	if strings.Contains(out, "100 cm") {
		t.Errorf("lines after quit should be ignored: %q", out)
	}
	if !strings.Contains(errOut, "error:") {
		t.Errorf("err=%q", errOut)
	}
}
