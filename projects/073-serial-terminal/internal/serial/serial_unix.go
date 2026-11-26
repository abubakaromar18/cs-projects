//go:build linux || darwin

package serial

import (
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"syscall"
	"unsafe"
)

// openDevice opens a tty in raw mode and applies cfg.
//
// The descriptor is opened O_NONBLOCK and handed to os.NewFile, which
// registers it with Go's runtime poller. Reads then park the goroutine instead
// of a whole OS thread, and Close reliably wakes a blocked Read with
// os.ErrClosed. That is what lets the terminal shut down cleanly.
func openDevice(name string, cfg Config) (Port, error) {
	fd, err := syscall.Open(name, syscall.O_RDWR|syscall.O_NOCTTY|syscall.O_NONBLOCK|syscall.O_CLOEXEC, 0)
	if err != nil {
		return nil, &os.PathError{Op: "open", Path: name, Err: err}
	}
	if err := configure(fd, cfg); err != nil {
		syscall.Close(fd)
		return nil, fmt.Errorf("configure %s: %w", name, err)
	}
	return os.NewFile(uintptr(fd), name), nil
}

// ioctl wraps the raw syscall used for termios get/set.
func ioctl(fd int, req uintptr, arg unsafe.Pointer) error {
	_, _, errno := syscall.Syscall(syscall.SYS_IOCTL, uintptr(fd), req, uintptr(arg))
	if errno != 0 {
		return errno
	}
	return nil
}

// listPorts globs the platform's conventional device names.
func listPorts() ([]string, error) {
	var out []string
	for _, pattern := range devicePatterns {
		matches, err := filepath.Glob(pattern)
		if err != nil {
			return nil, err
		}
		out = append(out, matches...)
	}
	sort.Strings(out)
	return out, nil
}
