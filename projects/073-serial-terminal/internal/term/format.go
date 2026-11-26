// Package term holds the platform-independent half of the serial terminal:
// line-ending translation for outgoing text, display filters for incoming
// bytes (hex dump, timestamps, control-character escaping) and the Session
// that pumps data between a port and the console.
package term

import (
	"bytes"
	"encoding/hex"
	"fmt"
	"io"
	"strings"
	"time"
)

// LineEnding is what the Enter key sends to the device.
type LineEnding int

const (
	EOLCR   LineEnding = iota // "\r"  (most AT-command modems, many bootloaders)
	EOLLF                     // "\n"  (Arduino Serial.readStringUntil('\n'))
	EOLCRLF                   // "\r\n"
	EOLNone                   // send nothing extra
)

// ParseLineEnding accepts cr, lf, crlf or none.
func ParseLineEnding(s string) (LineEnding, error) {
	switch strings.ToLower(s) {
	case "cr":
		return EOLCR, nil
	case "lf":
		return EOLLF, nil
	case "crlf":
		return EOLCRLF, nil
	case "none":
		return EOLNone, nil
	}
	return 0, fmt.Errorf("unknown line ending %q (want cr, lf, crlf or none)", s)
}

// Bytes returns the wire bytes for e.
func (e LineEnding) Bytes() []byte {
	switch e {
	case EOLCR:
		return []byte{'\r'}
	case EOLLF:
		return []byte{'\n'}
	case EOLCRLF:
		return []byte{'\r', '\n'}
	}
	return nil
}

// Encode strips whatever line terminator the console gave us and appends the
// configured one, so the device sees the same bytes on every OS.
func (e LineEnding) Encode(line string) []byte {
	line = strings.TrimRight(line, "\r\n")
	return append([]byte(line), e.Bytes()...)
}

// ParseHexBytes turns "01 03 ff", "0x01,0x03" or "0103ff" into bytes. Used by
// the ~b escape for sending binary frames (Modbus, bootloader commands, ...).
func ParseHexBytes(s string) ([]byte, error) {
	r := strings.NewReplacer("0x", "", "0X", "", " ", "", ",", "", ":", "", "\t", "")
	clean := r.Replace(s)
	if clean == "" {
		return nil, fmt.Errorf("no hex bytes given")
	}
	b, err := hex.DecodeString(clean)
	if err != nil {
		return nil, fmt.Errorf("bad hex %q: %w", s, err)
	}
	return b, nil
}

// HexWriter renders a byte stream as a classic 16-bytes-per-row hex dump
//
//	00000010  48 65 6c 6c 6f 0d 0a                              |Hello..|
//
// Serial data arrives in arbitrary chunks, so a partial row is held back
// until it fills up or Flush is called (e.g. after a quiet period). Offsets
// keep counting across rows and flushes.
type HexWriter struct {
	w      io.Writer
	offset int
	row    []byte
}

// NewHexWriter wraps w.
func NewHexWriter(w io.Writer) *HexWriter { return &HexWriter{w: w, row: make([]byte, 0, 16)} }

func (h *HexWriter) Write(p []byte) (int, error) {
	n := len(p)
	for len(p) > 0 {
		take := min(16-len(h.row), len(p))
		h.row = append(h.row, p[:take]...)
		p = p[take:]
		if len(h.row) == 16 {
			if err := h.emit(); err != nil {
				return n - len(p), err
			}
		}
	}
	return n, nil
}

// Flush writes out a partial row, if any.
func (h *HexWriter) Flush() error {
	if len(h.row) == 0 {
		return nil
	}
	return h.emit()
}

func (h *HexWriter) emit() error {
	var b strings.Builder
	fmt.Fprintf(&b, "%08x  ", h.offset)
	for i := 0; i < 16; i++ {
		if i < len(h.row) {
			fmt.Fprintf(&b, "%02x ", h.row[i])
		} else {
			b.WriteString("   ")
		}
		if i == 7 {
			b.WriteByte(' ')
		}
	}
	b.WriteString(" |")
	for _, c := range h.row {
		if c >= 0x20 && c < 0x7f {
			b.WriteByte(c)
		} else {
			b.WriteByte('.')
		}
	}
	b.WriteString("|\n")
	h.offset += len(h.row)
	h.row = h.row[:0]
	_, err := io.WriteString(h.w, b.String())
	return err
}

// TimestampWriter prefixes every line with the local time it started, e.g.
// "[12:04:05.123] ". The prefix is written lazily when the first byte of a new
// line arrives, so the time reflects when data actually showed up.
type TimestampWriter struct {
	w       io.Writer
	now     func() time.Time
	atStart bool
}

// NewTimestampWriter wraps w. A nil clock means time.Now.
func NewTimestampWriter(w io.Writer, clock func() time.Time) *TimestampWriter {
	if clock == nil {
		clock = time.Now
	}
	return &TimestampWriter{w: w, now: clock, atStart: true}
}

func (t *TimestampWriter) Write(p []byte) (int, error) {
	var out bytes.Buffer
	for _, c := range p {
		if t.atStart {
			out.WriteString(t.now().Format("[15:04:05.000] "))
			t.atStart = false
		}
		out.WriteByte(c)
		if c == '\n' {
			t.atStart = true
		}
	}
	if _, err := t.w.Write(out.Bytes()); err != nil {
		return 0, err
	}
	return len(p), nil
}

// EscapeWriter makes invisible bytes visible: control characters other than
// \n, \r and \t become <XX>, and so do bytes >= 0x7f. Handy for spotting a
// stray NUL or wrong line endings. Multi-byte UTF-8 is shown as hex too,
// since a serial stream may split it anyway.
type EscapeWriter struct{ w io.Writer }

// NewEscapeWriter wraps w.
func NewEscapeWriter(w io.Writer) *EscapeWriter { return &EscapeWriter{w: w} }

func (e *EscapeWriter) Write(p []byte) (int, error) {
	var out bytes.Buffer
	for _, c := range p {
		switch {
		case c == '\n' || c == '\t':
			out.WriteByte(c)
		case c == '\r':
			out.WriteString(`\r`)
		case c < 0x20 || c >= 0x7f:
			fmt.Fprintf(&out, "<%02X>", c)
		default:
			out.WriteByte(c)
		}
	}
	if _, err := e.w.Write(out.Bytes()); err != nil {
		return 0, err
	}
	return len(p), nil
}
