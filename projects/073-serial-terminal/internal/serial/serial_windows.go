//go:build windows

package serial

import (
	"errors"
	"fmt"
	"strings"
	"sync/atomic"
	"syscall"
	"unsafe"
)

var (
	kernel32            = syscall.NewLazyDLL("kernel32.dll")
	procGetCommState    = kernel32.NewProc("GetCommState")
	procSetCommState    = kernel32.NewProc("SetCommState")
	procSetCommTimeouts = kernel32.NewProc("SetCommTimeouts")
)

// dcb mirrors the Win32 DCB struct (28 bytes). The many 1-bit fields are
// packed into Flags.
type dcb struct {
	DCBlength  uint32
	BaudRate   uint32
	Flags      uint32
	wReserved  uint16
	XonLim     uint16
	XoffLim    uint16
	ByteSize   byte
	Parity     byte
	StopBits   byte
	XonChar    byte
	XoffChar   byte
	ErrorChar  byte
	EofChar    byte
	EvtChar    byte
	wReserved1 uint16
}

const (
	fBinary          = 1 << 0
	fParity          = 1 << 1
	fOutxCtsFlow     = 1 << 2
	fDtrControlShift = 4
	fRtsControlShift = 12
	dtrEnable        = 1
	rtsEnable        = 1
	rtsHandshake     = 2

	oneStopBit  = 0
	twoStopBits = 2
	maxDWORD    = 0xFFFFFFFF
)

type commTimeouts struct {
	ReadIntervalTimeout         uint32
	ReadTotalTimeoutMultiplier  uint32
	ReadTotalTimeoutConstant    uint32
	WriteTotalTimeoutMultiplier uint32
	WriteTotalTimeoutConstant   uint32
}

// winPort is a synchronous COM handle. Reads use a short timeout and loop so
// Close (which flips closed) is noticed within ~100ms.
type winPort struct {
	h      syscall.Handle
	closed atomic.Bool
}

func openDevice(name string, cfg Config) (Port, error) {
	path := name
	if !strings.HasPrefix(path, `\\.\`) {
		path = `\\.\` + path // required for COM10 and above
	}
	p16, err := syscall.UTF16PtrFromString(path)
	if err != nil {
		return nil, err
	}
	h, err := syscall.CreateFile(p16, syscall.GENERIC_READ|syscall.GENERIC_WRITE, 0, nil, syscall.OPEN_EXISTING, 0, 0)
	if err != nil {
		return nil, fmt.Errorf("open %s: %w", name, err)
	}
	if err := configure(h, cfg); err != nil {
		syscall.CloseHandle(h)
		return nil, fmt.Errorf("configure %s: %w", name, err)
	}
	return &winPort{h: h}, nil
}

func configure(h syscall.Handle, cfg Config) error {
	var d dcb
	d.DCBlength = uint32(unsafe.Sizeof(d))
	if r, _, err := procGetCommState.Call(uintptr(h), uintptr(unsafe.Pointer(&d))); r == 0 {
		return fmt.Errorf("GetCommState: %w", err)
	}
	d.BaudRate = uint32(cfg.BaudRate)
	d.ByteSize = byte(cfg.DataBits)
	d.Parity = byte(cfg.Parity) // Win32 uses 0=none, 1=odd, 2=even, same as ours
	d.StopBits = oneStopBit
	if cfg.StopBits == 2 {
		d.StopBits = twoStopBits
	}
	d.Flags = fBinary | dtrEnable<<fDtrControlShift
	if cfg.Parity != ParityNone {
		d.Flags |= fParity
	}
	if cfg.Flow == FlowRTSCTS {
		d.Flags |= fOutxCtsFlow | rtsHandshake<<fRtsControlShift
	} else {
		d.Flags |= rtsEnable << fRtsControlShift
	}
	if r, _, err := procSetCommState.Call(uintptr(h), uintptr(unsafe.Pointer(&d))); r == 0 {
		return fmt.Errorf("SetCommState: %w", err)
	}
	// MAXDWORD/MAXDWORD/N means: return immediately when any byte arrives,
	// otherwise wait up to N ms and return zero bytes.
	t := commTimeouts{ReadIntervalTimeout: maxDWORD, ReadTotalTimeoutMultiplier: maxDWORD, ReadTotalTimeoutConstant: 100}
	if r, _, err := procSetCommTimeouts.Call(uintptr(h), uintptr(unsafe.Pointer(&t))); r == 0 {
		return fmt.Errorf("SetCommTimeouts: %w", err)
	}
	return nil
}

var errClosed = errors.New("serial port closed")

func (p *winPort) Read(b []byte) (int, error) {
	for {
		if p.closed.Load() {
			return 0, errClosed
		}
		var n uint32
		if err := syscall.ReadFile(p.h, b, &n, nil); err != nil {
			return 0, err
		}
		if n > 0 {
			return int(n), nil
		}
	}
}

func (p *winPort) Write(b []byte) (int, error) {
	var n uint32
	err := syscall.WriteFile(p.h, b, &n, nil)
	return int(n), err
}

func (p *winPort) Close() error {
	if p.closed.Swap(true) {
		return nil
	}
	return syscall.CloseHandle(p.h)
}

// listPorts probes COM1..COM64. Ports that exist but are busy report
// ACCESS_DENIED, which still means "present".
func listPorts() ([]string, error) {
	var out []string
	for i := 1; i <= 64; i++ {
		name := fmt.Sprintf("COM%d", i)
		p16, _ := syscall.UTF16PtrFromString(`\\.\` + name)
		h, err := syscall.CreateFile(p16, syscall.GENERIC_READ, 0, nil, syscall.OPEN_EXISTING, 0, 0)
		if err == nil {
			syscall.CloseHandle(h)
			out = append(out, name)
		} else if errors.Is(err, syscall.ERROR_ACCESS_DENIED) {
			out = append(out, name)
		}
	}
	return out, nil
}
