//go:build linux

package serial

import (
	"fmt"
	"syscall"
	"unsafe"
)

// USB-serial adapters, CDC-ACM boards (Arduino, Pico), built-in UARTs and
// Raspberry Pi aliases.
var devicePatterns = []string{"/dev/ttyUSB*", "/dev/ttyACM*", "/dev/ttyAMA*", "/dev/serial0", "/dev/ttyS*"}

// Linux encodes speed as a symbolic constant inside c_cflag (the CBAUD bits),
// not as a number, so only the classic rates can be set via TCSETS.
var linuxBauds = map[int]uint32{
	50: syscall.B50, 75: syscall.B75, 110: syscall.B110, 134: syscall.B134,
	150: syscall.B150, 200: syscall.B200, 300: syscall.B300, 600: syscall.B600,
	1200: syscall.B1200, 1800: syscall.B1800, 2400: syscall.B2400, 4800: syscall.B4800,
	9600: syscall.B9600, 19200: syscall.B19200, 38400: syscall.B38400,
	57600: syscall.B57600, 115200: syscall.B115200, 230400: syscall.B230400,
	460800: syscall.B460800, 500000: syscall.B500000, 576000: syscall.B576000,
	921600: syscall.B921600, 1000000: syscall.B1000000, 1152000: syscall.B1152000,
	1500000: syscall.B1500000, 2000000: syscall.B2000000, 2500000: syscall.B2500000,
	3000000: syscall.B3000000, 3500000: syscall.B3500000, 4000000: syscall.B4000000,
}

const (
	cbaud   = 0x100f     // CBAUD | CBAUDEX mask in c_cflag
	crtscts = 0x80000000 // hardware flow control bit in c_cflag
)

var dataBitFlags = map[int]uint32{5: syscall.CS5, 6: syscall.CS6, 7: syscall.CS7, 8: syscall.CS8}

func configure(fd int, cfg Config) error {
	speed, ok := linuxBauds[cfg.BaudRate]
	if !ok {
		return fmt.Errorf("%w: baud %d is not a standard Linux rate", ErrInvalidConfig, cfg.BaudRate)
	}
	var t syscall.Termios
	if err := ioctl(fd, syscall.TCGETS, unsafe.Pointer(&t)); err != nil {
		return fmt.Errorf("TCGETS: %w", err)
	}
	applyRaw(&t, cfg, speed)
	if err := ioctl(fd, syscall.TCSETS, unsafe.Pointer(&t)); err != nil {
		return fmt.Errorf("TCSETS: %w", err)
	}
	return nil
}

// applyRaw is the equivalent of cfmakeraw(3) plus the frame settings. It is
// split out so tests can check the bit twiddling without a device.
func applyRaw(t *syscall.Termios, cfg Config, speed uint32) {
	// Raw mode: no input translation, no output post-processing, no echo,
	// no line editing, no signals. Bytes in == bytes out.
	t.Iflag &^= syscall.IGNBRK | syscall.BRKINT | syscall.PARMRK | syscall.ISTRIP |
		syscall.INLCR | syscall.IGNCR | syscall.ICRNL | syscall.IXON | syscall.IXOFF
	t.Oflag &^= syscall.OPOST
	t.Lflag &^= syscall.ECHO | syscall.ECHONL | syscall.ICANON | syscall.ISIG | syscall.IEXTEN

	t.Cflag &^= syscall.CSIZE | syscall.PARENB | syscall.PARODD | syscall.CSTOPB | crtscts | cbaud
	t.Cflag |= dataBitFlags[cfg.DataBits] | syscall.CREAD | syscall.CLOCAL | speed
	switch cfg.Parity {
	case ParityOdd:
		t.Cflag |= syscall.PARENB | syscall.PARODD
		t.Iflag |= syscall.INPCK
	case ParityEven:
		t.Cflag |= syscall.PARENB
		t.Iflag |= syscall.INPCK
	default:
		t.Iflag &^= syscall.INPCK
	}
	if cfg.StopBits == 2 {
		t.Cflag |= syscall.CSTOPB
	}
	if cfg.Flow == FlowRTSCTS {
		t.Cflag |= crtscts
	}
	t.Ispeed, t.Ospeed = speed, speed

	// VMIN=1, VTIME=0: a read returns as soon as one byte is available. With
	// O_NONBLOCK the poller turns "nothing yet" (EAGAIN) into a park.
	t.Cc[syscall.VMIN] = 1
	t.Cc[syscall.VTIME] = 0
}
