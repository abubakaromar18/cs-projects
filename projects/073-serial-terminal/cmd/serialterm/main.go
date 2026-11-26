// Command serialterm is a small cross-platform serial monitor, in the spirit
// of screen/minicom/picocom but line-oriented and dependency-free.
//
//	serialterm -list
//	serialterm -port /dev/ttyUSB0 -baud 9600 -eol crlf
//	serialterm -port COM3 -hex
//	serialterm -port tcp://127.0.0.1:2000 -timestamps -log capture.bin
package main

import (
	"context"
	"errors"
	"flag"
	"fmt"
	"io"
	"os"
	"os/signal"
	"strings"
	"time"

	"github.com/abubakaromar18/cs-projects/projects/073-serial-terminal/internal/serial"
	"github.com/abubakaromar18/cs-projects/projects/073-serial-terminal/internal/term"
)

func main() {
	if err := run(os.Args[1:], os.Stdin, os.Stdout, os.Stderr); err != nil {
		fmt.Fprintln(os.Stderr, "serialterm:", err)
		os.Exit(1)
	}
}

type flags struct {
	port, frame, eol, flow, logPath string
	baud                            int
	list, hex, timestamps, escape   bool
	echo                            bool
}

func parseFlags(args []string, stderr io.Writer) (*flags, error) {
	f := &flags{}
	fs := flag.NewFlagSet("serialterm", flag.ContinueOnError)
	fs.SetOutput(stderr)
	fs.StringVar(&f.port, "port", "", "device (/dev/ttyUSB0, /dev/cu.usbserial-1, COM3) or tcp://host:port")
	fs.IntVar(&f.baud, "baud", 115200, "baud rate")
	fs.StringVar(&f.frame, "frame", "8N1", "data bits, parity (N/O/E), stop bits")
	fs.StringVar(&f.flow, "flow", "none", "flow control: none or rtscts")
	fs.StringVar(&f.eol, "eol", "crlf", "line ending sent on Enter: cr, lf, crlf, none")
	fs.BoolVar(&f.list, "list", false, "list candidate serial ports and exit")
	fs.BoolVar(&f.hex, "hex", false, "show received data as a hex dump")
	fs.BoolVar(&f.timestamps, "timestamps", false, "prefix each received line with the time")
	fs.BoolVar(&f.escape, "escape", false, "show control characters as <XX>")
	fs.BoolVar(&f.echo, "echo", false, "local echo of sent data")
	fs.StringVar(&f.logPath, "log", "", "append raw received bytes to this file")
	if err := fs.Parse(args); err != nil {
		return nil, err
	}
	if !f.list && f.port == "" {
		return nil, errors.New("-port is required (try -list)")
	}
	return f, nil
}

func buildConfig(f *flags) (serial.Config, error) {
	cfg := serial.DefaultConfig()
	cfg.BaudRate = f.baud
	if err := cfg.ParseFrame(f.frame); err != nil {
		return cfg, err
	}
	switch strings.ToLower(f.flow) {
	case "none", "":
		cfg.Flow = serial.FlowNone
	case "rtscts", "hw":
		cfg.Flow = serial.FlowRTSCTS
	default:
		return cfg, fmt.Errorf("unknown flow control %q", f.flow)
	}
	return cfg, cfg.Validate()
}

// buildDisplay chains the output filters. Hex mode is exclusive; otherwise
// escaping runs before timestamping so the timestamper still sees '\n'.
func buildDisplay(f *flags, out io.Writer) io.Writer {
	if f.hex {
		return term.NewHexWriter(out)
	}
	w := out
	if f.timestamps {
		w = term.NewTimestampWriter(w, nil)
	}
	if f.escape {
		w = term.NewEscapeWriter(w)
	}
	return w
}

func run(args []string, stdin io.Reader, stdout, stderr io.Writer) error {
	f, err := parseFlags(args, stderr)
	if err != nil {
		return err
	}
	if f.list {
		ports, err := serial.ListPorts()
		if err != nil {
			return err
		}
		if len(ports) == 0 {
			fmt.Fprintln(stdout, "no serial ports found")
		}
		for _, p := range ports {
			fmt.Fprintln(stdout, p)
		}
		return nil
	}

	cfg, err := buildConfig(f)
	if err != nil {
		return err
	}
	eol, err := term.ParseLineEnding(f.eol)
	if err != nil {
		return err
	}

	port, err := serial.Open(f.port, cfg)
	if err != nil {
		return err
	}
	defer port.Close()

	opts := term.Options{EOL: eol, LocalEcho: f.echo, Display: buildDisplay(f, stdout), Status: stderr}
	if f.logPath != "" {
		lf, err := os.OpenFile(f.logPath, os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0o644)
		if err != nil {
			return err
		}
		defer lf.Close()
		opts.Log = lf
	}

	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt)
	defer stop()

	fmt.Fprintf(stderr, "--- connected to %s (%s), eol=%s. Type ~? for help, ~. to quit\n", f.port, cfg, f.eol)
	sess := term.NewSession(port, opts)
	start := time.Now()
	err = sess.Run(ctx, stdin)
	st := sess.Stats()
	fmt.Fprintf(stderr, "\n--- disconnected after %s: tx %d bytes, rx %d bytes\n",
		time.Since(start).Round(time.Millisecond), st.TX, st.RX)
	if errors.Is(err, term.ErrQuit) || errors.Is(err, context.Canceled) {
		return nil
	}
	return err
}
