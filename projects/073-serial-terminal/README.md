# 073 · Serial Terminal

A cross-platform serial monitor in Go, like a small `picocom` or the Arduino Serial Monitor, with **no third-party dependencies**. It opens a port, sets baud/frame/flow control, and pumps bytes between the device and your console. It can also show received data as a hex dump, timestamp each line, make control characters visible, and log raw captures.

Each OS back-end talks to the kernel directly: termios `ioctl`s on Linux and macOS, and the Win32 comm API (`DCB`, `COMMTIMEOUTS`) on Windows, all through Go's standard `syscall` package.

```
 stdin ──lines──► Session.handleLine ──(~ escapes | EOL encode)──► Port.Write ──► device
                                                                                     │
stdout ◄── Hex / Timestamp / Escape filters ◄── Session.receive ◄── Port.Read ◄──────┘
                                                      └──► raw -log file
```

## Features

- Ports: `/dev/ttyUSB0`, `/dev/ttyACM0` (Linux), `/dev/cu.usbserial-*` (macOS), `COM3` (Windows), or `tcp://host:port` for ser2net/ESP-Link bridges and local simulators
- `-list` finds candidate ports (globs on Unix, probes COM1–COM64 on Windows)
- Any frame: `-frame 8N1 | 7E1 | 8O2 ...`, `-baud`, `-flow rtscts`
- `-eol cr|lf|crlf|none`: Enter sends the same bytes on every OS
- Display modes: `-hex` (streaming 16-byte rows, flushed after 150 ms of silence), `-timestamps`, `-escape` (`\r`, `<00>`, `<1B>` ...)
- `-echo` local echo, `-log file` raw capture of received bytes
- `ssh`/`cu`-style escapes at the start of a line: `~.` quit, `~?` help, `~s` byte counters, `~b 01 03 ff` send raw hex bytes, `~~` a literal tilde
- Pipe-friendly: `echo AT | serialterm -port ... -eol cr` sends, waits briefly for the reply, and exits

## CS concepts

- **Terminal line discipline.** A tty is not a plain file. By default the kernel echoes, buffers lines (`ICANON`), maps CR→NL (`ICRNL`) and NL→CRNL (`OPOST`). The terminal turns all of that off (the same as `cfmakeraw`) so bytes reach the device unchanged. The tests check this on a real pseudo-terminal.
- **Bit-field encoding.** Frame settings are flag bits in `c_cflag` (`CSIZE`, `PARENB`, `PARODD`, `CSTOPB`, `CRTSCTS`). Linux also stores the *speed* as a symbolic code in the `CBAUD` bits, while BSD/macOS store a plain number. Windows packs about 14 one-bit fields into the `DCB.Flags` word.
- **Platform abstraction with build tags.** `serial_unix.go` (`linux || darwin`), `serial_linux.go`, `serial_darwin.go` and `serial_windows.go` all provide `openDevice`/`listPorts` behind one `Port` interface. `make cross` compiles all three from any host.
- **Non-blocking I/O and the Go netpoller.** The tty is opened `O_NONBLOCK` and wrapped with `os.NewFile`, so it joins the runtime poller. A blocked `Read` parks a goroutine rather than a thread, and `Close` wakes it with an error. Windows has no poller for comm handles, so it uses `COMMTIMEOUTS` (return on first byte or after 100 ms) and checks a closed flag on each loop.
- **Concurrency.** The receive loop, the console reader and the idle-flush timer are separate goroutines. A mutex serialises writes to the display, and channels plus `context` handle shutdown. The tests pass under `-race`.
- **Streaming formatters.** `HexWriter` keeps a partial row across arbitrary chunk boundaries, and `TimestampWriter` is a tiny state machine (at-line-start or not). Both are `io.Writer` decorators that compose.

## Layout

```
cmd/serialterm/        CLI: flags → serial.Config, filter chain, Session
internal/serial/       Config/validation, Open (device or tcp://), OS back-ends
internal/term/         LineEnding, hex parsing, HexWriter, TimestampWriter, EscapeWriter, Session
```

## Build, run, test

Requires Go 1.22+.

```sh
make build                      # → bin/serialterm
bin/serialterm -list
bin/serialterm -port /dev/ttyUSB0 -baud 9600
make test                       # or: go test ./...
make race                       # tests under the race detector
make cross                      # compile-check linux/darwin/windows
```

On Linux you may need to be in the `dialout` group (`sudo usermod -aG dialout $USER`) to open real devices.

**Tests:** 30 tests, all passing on Linux. They cover:

- config validation and frame parsing
- line-ending encoding and hex parsing
- the hex, timestamp and escape formatters
- the session: escapes, local echo, logging, idle flush, device hang-up
- an end-to-end CLI run against a localhost TCP "device"
- Linux-only **pseudo-terminal integration tests**, which open a real `/dev/ptmx` pair and check that termios settings are applied, that data is not translated, and that `Close` unblocks `Read`

The macOS and Windows back-ends compile and `go vet` clean via cross-compilation, but have not been run against hardware here.

Note: the Linux pty driver always forces `CS8` and no parity on the slave. So the 7-bit and parity flags are tested against `applyRaw` directly, not read back from the pty.

### Try it without hardware

```sh
# Linux/macOS: create a virtual null-modem cable
socat -d -d pty,raw,echo=0 pty,raw,echo=0      # prints two /dev/pts/N paths
bin/serialterm -port /dev/pts/3 -eol lf          # in one shell
cat /dev/pts/4                                    # or another serialterm on the other end
```

## Example

Talking to an ESP8266 AT firmware in hex mode (captured from a pty-backed fake device):

```
$ serialterm -port /dev/ttyUSB0 -baud 9600 -hex
--- connected to /dev/ttyUSB0 (9600 8N1), eol=crlf. Type ~? for help, ~. to quit
AT+GMR
00000000  41 54 20 76 65 72 73 69  6f 6e 3a 31 2e 37 2e 34  |AT version:1.7.4|
00000010  0d 0a 4f 4b 0d 0a 00                              |..OK...|
~.

--- disconnected after 2.09s: tx 8 bytes, rx 23 bytes
```

Sending a Modbus RTU "read holding registers" frame:

```
~b 01 03 00 00 00 0a c5 cd
```

## Possible extensions

- Raw keyboard mode (put the *console* in raw mode too) for interactive shells and bootloader menus that react to single keys
- Non-standard baud rates on Linux via `termios2`/`BOTHER` (`TCSETS2`), and `IOSSIOSPEED` on macOS
- Control lines: toggle DTR/RTS (`TIOCMBIS`/`EscapeCommFunction`) to reset an Arduino or ESP32 into its bootloader
- XON/XOFF software flow control, and BREAK (`TCSBRK`)
- Hot-plug detection: reconnect automatically when a USB adapter comes back
- Windows port listing from the `HARDWARE\DEVICEMAP\SERIALCOMM` registry key with friendly names
- A TUI split view (sent vs. received) or a built-in plotter for numeric CSV streams
