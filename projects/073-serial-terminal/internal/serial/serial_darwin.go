//go:build darwin

package serial

import (
	"fmt"
	"syscall"
	"unsafe"
)

// On macOS use the "call-out" /dev/cu.* nodes; /dev/tty.* block on open until
// carrier detect is asserted.
var devicePatterns = []string{"/dev/cu.usbserial*", "/dev/cu.usbmodem*", "/dev/cu.SLAB*", "/dev/cu.wchusbserial*"}

const crtscts = 0x00030000 // CCTS_OFLOW | CRTS_IFLOW

var dataBitFlags = map[int]uint64{5: syscall.CS5, 6: syscall.CS6, 7: syscall.CS7, 8: syscall.CS8}

func configure(fd int, cfg Config) error {
	var t syscall.Termios
	if err := ioctl(fd, syscall.TIOCGETA, unsafe.Pointer(&t)); err != nil {
		return fmt.Errorf("TIOCGETA: %w", err)
	}

	t.Iflag &^= syscall.IGNBRK | syscall.BRKINT | syscall.PARMRK | syscall.ISTRIP |
		syscall.INLCR | syscall.IGNCR | syscall.ICRNL | syscall.IXON | syscall.IXOFF
	t.Oflag &^= syscall.OPOST
	t.Lflag &^= syscall.ECHO | syscall.ECHONL | syscall.ICANON | syscall.ISIG | syscall.IEXTEN

	t.Cflag &^= syscall.CSIZE | syscall.PARENB | syscall.PARODD | syscall.CSTOPB | crtscts
	t.Cflag |= dataBitFlags[cfg.DataBits] | syscall.CREAD | syscall.CLOCAL
	switch cfg.Parity {
	case ParityOdd:
		t.Cflag |= syscall.PARENB | syscall.PARODD
		t.Iflag |= syscall.INPCK
	case ParityEven:
		t.Cflag |= syscall.PARENB
		t.Iflag |= syscall.INPCK
	}
	if cfg.StopBits == 2 {
		t.Cflag |= syscall.CSTOPB
	}
	if cfg.Flow == FlowRTSCTS {
		t.Cflag |= crtscts
	}
	// BSD termios stores speed as a plain number, so any rate the driver
	// accepts can be requested directly.
	t.Ispeed, t.Ospeed = uint64(cfg.BaudRate), uint64(cfg.BaudRate)
	t.Cc[syscall.VMIN] = 1
	t.Cc[syscall.VTIME] = 0

	if err := ioctl(fd, syscall.TIOCSETA, unsafe.Pointer(&t)); err != nil {
		return fmt.Errorf("TIOCSETA: %w", err)
	}
	return nil
}
