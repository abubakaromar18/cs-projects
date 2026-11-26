package term

import (
	"bytes"
	"strings"
	"testing"
	"time"
)

func TestLineEndingEncode(t *testing.T) {
	tests := []struct {
		eol  LineEnding
		in   string
		want string
	}{
		{EOLCR, "AT\n", "AT\r"},
		{EOLLF, "AT\r\n", "AT\n"},
		{EOLCRLF, "AT\n", "AT\r\n"},
		{EOLNone, "AT\r\n", "AT"},
		{EOLCRLF, "", "\r\n"},
	}
	for _, tt := range tests {
		if got := string(tt.eol.Encode(tt.in)); got != tt.want {
			t.Errorf("%v.Encode(%q) = %q, want %q", tt.eol, tt.in, got, tt.want)
		}
	}
}

func TestParseLineEnding(t *testing.T) {
	for s, want := range map[string]LineEnding{"cr": EOLCR, "LF": EOLLF, "CrLf": EOLCRLF, "none": EOLNone} {
		got, err := ParseLineEnding(s)
		if err != nil || got != want {
			t.Errorf("%q -> %v, %v", s, got, err)
		}
	}
	if _, err := ParseLineEnding("rn"); err == nil {
		t.Error("expected error")
	}
}

func TestParseHexBytes(t *testing.T) {
	for _, in := range []string{"01 03 ff", "0x01,0x03,0xFF", "0103ff", " 01:03:ff "} {
		got, err := ParseHexBytes(in)
		if err != nil || !bytes.Equal(got, []byte{1, 3, 0xff}) {
			t.Errorf("%q -> %x, %v", in, got, err)
		}
	}
	for _, bad := range []string{"", "0", "zz", "01 0"} {
		if _, err := ParseHexBytes(bad); err == nil {
			t.Errorf("%q: expected error", bad)
		}
	}
}

func TestHexWriterFullAndPartialRows(t *testing.T) {
	var out bytes.Buffer
	h := NewHexWriter(&out)
	// Feed in awkward chunks, as a UART would.
	data := []byte("Hello, serial world!\r\n\x00")
	h.Write(data[:3])
	h.Write(data[3:17])
	if strings.Count(out.String(), "\n") != 1 {
		t.Fatalf("expected exactly one full row so far, got %q", out.String())
	}
	h.Write(data[17:])
	h.Flush()

	want := "" +
		"00000000  48 65 6c 6c 6f 2c 20 73  65 72 69 61 6c 20 77 6f  |Hello, serial wo|\n" +
		"00000010  72 6c 64 21 0d 0a 00                              |rld!...|\n"
	if out.String() != want {
		t.Fatalf("got:\n%s\nwant:\n%s", out.String(), want)
	}
	// Flushing an empty row is a no-op.
	h.Flush()
	if out.String() != want {
		t.Fatal("empty flush wrote output")
	}
}

func TestHexWriterOffsetContinuesAfterFlush(t *testing.T) {
	var out bytes.Buffer
	h := NewHexWriter(&out)
	h.Write([]byte{1, 2, 3})
	h.Flush()
	h.Write([]byte{4})
	h.Flush()
	if !strings.Contains(out.String(), "\n00000003  04 ") {
		t.Fatalf("offset not continued: %q", out.String())
	}
}

func TestTimestampWriter(t *testing.T) {
	var out bytes.Buffer
	tick := time.Date(2026, 1, 2, 3, 4, 5, 6_000_000, time.UTC)
	clock := func() time.Time { tick = tick.Add(time.Second); return tick }
	w := NewTimestampWriter(&out, clock)
	w.Write([]byte("boot"))
	w.Write([]byte("ing\nready\n"))
	w.Write([]byte("x"))
	want := "[03:04:06.006] booting\n[03:04:07.006] ready\n[03:04:08.006] x"
	if out.String() != want {
		t.Fatalf("got %q\nwant %q", out.String(), want)
	}
}

func TestEscapeWriter(t *testing.T) {
	var out bytes.Buffer
	n, _ := NewEscapeWriter(&out).Write([]byte("OK\r\n\x00\x1b[0m\tz\xff"))
	if n != 12 {
		t.Errorf("n = %d", n)
	}
	want := "OK\\r\n<00><1B>[0m\tz<FF>"
	if out.String() != want {
		t.Fatalf("got %q want %q", out.String(), want)
	}
}

func TestEscapeThenTimestampChain(t *testing.T) {
	var out bytes.Buffer
	clock := func() time.Time { return time.Date(2026, 1, 1, 9, 0, 0, 0, time.UTC) }
	w := NewEscapeWriter(NewTimestampWriter(&out, clock))
	w.Write([]byte("a\r\nb\x07\n"))
	want := "[09:00:00.000] a\\r\n[09:00:00.000] b<07>\n"
	if out.String() != want {
		t.Fatalf("got %q", out.String())
	}
}
