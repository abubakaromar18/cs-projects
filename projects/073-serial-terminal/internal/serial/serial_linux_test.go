//go:build linux

package serial

import (
	"fmt"
	"io"
	"os"
	"syscall"
	"testing"
	"time"
	"unsafe"
)

// openPTY creates a pseudo-terminal pair. The slave end behaves like a real
// tty, termios and all, so it stands in for a USB-serial adapter in tests.
func openPTY(t *testing.T) (master *os.File, slavePath string) {
	t.Helper()
	m, err := os.OpenFile("/dev/ptmx", os.O_RDWR|syscall.O_NOCTTY, 0)
	if err != nil {
		t.Skipf("no /dev/ptmx: %v", err)
	}
	var unlock int32
	if err := ioctl(int(m.Fd()), syscall.TIOCSPTLCK, unsafe.Pointer(&unlock)); err != nil {
		t.Fatalf("unlockpt: %v", err)
	}
	var n uint32
	if err := ioctl(int(m.Fd()), syscall.TIOCGPTN, unsafe.Pointer(&n)); err != nil {
		t.Fatalf("ptsname: %v", err)
	}
	t.Cleanup(func() { m.Close() })
	return m, fmt.Sprintf("/dev/pts/%d", n)
}

func termiosOf(t *testing.T, f *os.File) syscall.Termios {
	t.Helper()
	var tio syscall.Termios
	rc, _ := f.SyscallConn()
	var ierr error
	rc.Control(func(fd uintptr) { ierr = ioctl(int(fd), syscall.TCGETS, unsafe.Pointer(&tio)) })
	if ierr != nil {
		t.Fatal(ierr)
	}
	return tio
}

func TestOpenPTYAppliesConfig(t *testing.T) {
	_, slave := openPTY(t)
	cfg := Config{BaudRate: 9600, DataBits: 7, Parity: ParityEven, StopBits: 2, Flow: FlowRTSCTS}
	p, err := Open(slave, cfg)
	if err != nil {
		t.Fatal(err)
	}
	defer p.Close()
	tio := termiosOf(t, p.(*os.File))

	if tio.Cflag&cbaud != syscall.B9600 {
		t.Errorf("baud bits = %#x", tio.Cflag&cbaud)
	}
	// Note: the Linux pty driver forces CS8 and clears PARENB on the slave,
	// so data bits and parity are checked against applyRaw directly below.
	if tio.Cflag&syscall.CSTOPB == 0 {
		t.Error("CSTOPB not set")
	}
	if tio.Cflag&crtscts == 0 {
		t.Error("CRTSCTS not set")
	}
	if tio.Lflag&(syscall.ICANON|syscall.ECHO) != 0 {
		t.Error("not in raw mode")
	}
}

func TestPTYDataFlowsBothWaysUntranslated(t *testing.T) {
	master, slave := openPTY(t)
	p, err := Open(slave, DefaultConfig())
	if err != nil {
		t.Fatal(err)
	}
	defer p.Close()

	// Device -> us: a CR must not be turned into LF (ICRNL off).
	master.Write([]byte("OK\r\n\x00\xff"))
	got := make([]byte, 6)
	if _, err := io.ReadFull(p, got); err != nil {
		t.Fatal(err)
	}
	if string(got) != "OK\r\n\x00\xff" {
		t.Fatalf("read %q", got)
	}

	// Us -> device: LF must not become CRLF (OPOST off).
	p.Write([]byte("AT\n"))
	back := make([]byte, 3)
	if _, err := io.ReadFull(master, back); err != nil {
		t.Fatal(err)
	}
	if string(back) != "AT\n" {
		t.Fatalf("master read %q", back)
	}
}

func TestCloseUnblocksRead(t *testing.T) {
	_, slave := openPTY(t)
	p, err := Open(slave, DefaultConfig())
	if err != nil {
		t.Fatal(err)
	}
	done := make(chan error, 1)
	go func() {
		_, err := p.Read(make([]byte, 1))
		done <- err
	}()
	time.Sleep(50 * time.Millisecond)
	p.Close()
	select {
	case err := <-done:
		if err == nil {
			t.Fatal("expected error after close")
		}
	case <-time.After(2 * time.Second):
		t.Fatal("Read still blocked after Close")
	}
}

func TestNonStandardBaudRejectedOnLinux(t *testing.T) {
	_, slave := openPTY(t)
	cfg := DefaultConfig()
	cfg.BaudRate = 12345
	if _, err := Open(slave, cfg); err == nil {
		t.Fatal("expected error for 12345 baud")
	}
}

func TestApplyRawNoParityClearsINPCK(t *testing.T) {
	tio := syscall.Termios{Iflag: syscall.INPCK | syscall.ICRNL, Cflag: syscall.PARENB | syscall.PARODD}
	applyRaw(&tio, DefaultConfig(), syscall.B115200)
	if tio.Iflag&(syscall.INPCK|syscall.ICRNL) != 0 || tio.Cflag&syscall.PARENB != 0 {
		t.Fatalf("flags not cleared: iflag=%#x cflag=%#x", tio.Iflag, tio.Cflag)
	}
	if tio.Cc[syscall.VMIN] != 1 || tio.Cc[syscall.VTIME] != 0 {
		t.Fatal("VMIN/VTIME")
	}
}

func TestApplyRawFrameBits(t *testing.T) {
	var tio syscall.Termios
	applyRaw(&tio, Config{BaudRate: 9600, DataBits: 7, Parity: ParityEven, StopBits: 1}, syscall.B9600)
	if tio.Cflag&syscall.CSIZE != syscall.CS7 {
		t.Errorf("CSIZE = %#x", tio.Cflag&syscall.CSIZE)
	}
	if tio.Cflag&syscall.PARENB == 0 || tio.Cflag&syscall.PARODD != 0 || tio.Iflag&syscall.INPCK == 0 {
		t.Errorf("even parity flags wrong: cflag=%#x", tio.Cflag)
	}
	applyRaw(&tio, Config{BaudRate: 9600, DataBits: 5, Parity: ParityOdd, StopBits: 1}, syscall.B9600)
	if tio.Cflag&syscall.CSIZE != syscall.CS5 || tio.Cflag&syscall.PARODD == 0 {
		t.Errorf("odd/5-bit flags wrong: cflag=%#x", tio.Cflag)
	}
	if tio.Cflag&syscall.CSTOPB != 0 || tio.Cflag&crtscts != 0 {
		t.Error("stale CSTOPB/CRTSCTS")
	}
}
