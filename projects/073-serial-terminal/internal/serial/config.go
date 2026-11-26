// Package serial opens and configures serial ports without third-party
// dependencies. Platform back-ends talk to the OS directly: termios ioctls on
// Linux and macOS, and the Win32 comm API (DCB + COMMTIMEOUTS) on Windows.
//
// Besides device paths, Open also accepts "tcp://host:port" so the terminal
// can talk to network serial bridges (ser2net, ESP-Link) or local simulators.
package serial

import (
	"errors"
	"fmt"
	"io"
	"net"
	"strings"
	"time"
)

// Parity selects the parity bit mode.
type Parity int

const (
	ParityNone Parity = iota
	ParityOdd
	ParityEven
)

func (p Parity) String() string {
	switch p {
	case ParityOdd:
		return "O"
	case ParityEven:
		return "E"
	default:
		return "N"
	}
}

// FlowControl selects hardware handshaking.
type FlowControl int

const (
	FlowNone FlowControl = iota
	FlowRTSCTS
)

// Config describes a serial line. The zero value is not valid; start from
// DefaultConfig, which is the ubiquitous "115200 8N1".
type Config struct {
	BaudRate int
	DataBits int // 5..8
	Parity   Parity
	StopBits int // 1 or 2
	Flow     FlowControl
}

// DefaultConfig returns 115200 baud, 8 data bits, no parity, 1 stop bit.
func DefaultConfig() Config {
	return Config{BaudRate: 115200, DataBits: 8, Parity: ParityNone, StopBits: 1, Flow: FlowNone}
}

// String renders the conventional short form, e.g. "115200 8N1".
func (c Config) String() string {
	s := fmt.Sprintf("%d %d%s%d", c.BaudRate, c.DataBits, c.Parity, c.StopBits)
	if c.Flow == FlowRTSCTS {
		s += " rtscts"
	}
	return s
}

// ErrInvalidConfig wraps every validation failure so callers can test for it.
var ErrInvalidConfig = errors.New("invalid serial config")

// Validate checks that every field is in range.
func (c Config) Validate() error {
	switch {
	case c.BaudRate <= 0:
		return fmt.Errorf("%w: baud rate must be positive, got %d", ErrInvalidConfig, c.BaudRate)
	case c.DataBits < 5 || c.DataBits > 8:
		return fmt.Errorf("%w: data bits must be 5-8, got %d", ErrInvalidConfig, c.DataBits)
	case c.StopBits != 1 && c.StopBits != 2:
		return fmt.Errorf("%w: stop bits must be 1 or 2, got %d", ErrInvalidConfig, c.StopBits)
	case c.Parity < ParityNone || c.Parity > ParityEven:
		return fmt.Errorf("%w: unknown parity %d", ErrInvalidConfig, c.Parity)
	case c.Flow < FlowNone || c.Flow > FlowRTSCTS:
		return fmt.Errorf("%w: unknown flow control %d", ErrInvalidConfig, c.Flow)
	}
	return nil
}

// ParseFrame parses a frame spec such as "8N1", "7E1" or "8o2" into c.
func (c *Config) ParseFrame(spec string) error {
	if len(spec) != 3 {
		return fmt.Errorf("%w: frame %q must look like 8N1", ErrInvalidConfig, spec)
	}
	data, par, stop := spec[0], strings.ToUpper(spec[1:2]), spec[2]
	if data < '5' || data > '8' {
		return fmt.Errorf("%w: data bits %q", ErrInvalidConfig, string(data))
	}
	if stop != '1' && stop != '2' {
		return fmt.Errorf("%w: stop bits %q", ErrInvalidConfig, string(stop))
	}
	switch par {
	case "N":
		c.Parity = ParityNone
	case "O":
		c.Parity = ParityOdd
	case "E":
		c.Parity = ParityEven
	default:
		return fmt.Errorf("%w: parity %q (want N, O or E)", ErrInvalidConfig, par)
	}
	c.DataBits = int(data - '0')
	c.StopBits = int(stop - '0')
	return nil
}

// Port is an open serial line. Close must unblock a pending Read.
type Port interface {
	io.ReadWriteCloser
}

// Open opens a device path (e.g. /dev/ttyUSB0, COM3) or a tcp:// URL.
func Open(name string, cfg Config) (Port, error) {
	if err := cfg.Validate(); err != nil {
		return nil, err
	}
	if addr, ok := strings.CutPrefix(name, "tcp://"); ok {
		// Line settings don't apply to a raw socket; the remote bridge owns them.
		return net.DialTimeout("tcp", addr, 5*time.Second)
	}
	return openDevice(name, cfg)
}

// ListPorts returns candidate serial device names for this platform.
func ListPorts() ([]string, error) { return listPorts() }
