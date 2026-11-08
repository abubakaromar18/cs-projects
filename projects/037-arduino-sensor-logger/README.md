# 037 · Arduino Sensor Logger (C++ / Arduino)

An Arduino sketch that reads three analog sensors (an NTC thermistor, a light
sensor and a raw voltage), smooths them with integer filters, and streams
**framed, CRC-checked CSV records** over Serial. You can change the sample
rate, start or stop logging, and check status by typing commands in the Serial Monitor. A
Python reader on the PC validates each line and saves clean CSV.

All the logic lives in a hardware-independent core (`SensorLogger/src/`).
The same code runs on the board, in a desktop simulator, and in about 400 unit
test checks on a normal PC.

```
$0,0,24.08,68.3,3284*0B
$1,1000,24.34,70.1,3290*06
#  seq  ms   temp°C light% mV  CRC-8
```

## Key CS concepts

- **Hardware abstraction / ports and adapters.** The core only knows two
  interfaces, `AnalogSource` and `TextSink`. The `.ino` file adapts them to
  `analogRead()` and `Serial`. The tests use fakes, and the simulator uses
  synthetic signals.
- **Non-blocking cooperative scheduling.** No `delay()` anywhere. `loop()`
  polls a `PeriodicTimer`, so serial commands are handled instantly
  while sampling.
- **Unsigned wrap-around arithmetic.** `millis()` overflows after about 49.7 days.
  The timer compares *elapsed* time (`now - last`), which stays correct
  modulo 2³², and the tests cover the wrap. It also avoids drift (it advances by
  whole periods) and does not fire a burst of catch-up ticks after a stall.
- **Static memory only.** A compile-time-sized `RingBuffer<T, N>`, no heap,
  no STL, no exceptions. This fits a 2 KB ATmega328P.
- **Signal processing with integers.** An O(1) moving average with a running
  sum, and an exponential moving average in Q8 fixed point, so small steps
  aren't lost to truncation. Both round negative values symmetrically.
- **Physical modelling.** Voltage-divider math and the thermistor
  **Beta equation** `1/T = 1/T₀ + ln(R/R₀)/B`. Shorted or open sensors are
  detected, reported as `NaN`, and kept out of the filter.
- **Fixed-point text formatting.** AVR `printf` has no `%f`, so values are
  carried as hundredths and printed by a small formatter that handles
  `INT32_MIN` and buffer limits.
- **Framing and error detection.** NMEA-style `$…*CS` frames with a bitwise
  CRC-8/SMBUS (poly 0x07; the standard check value `0xF4` is tested). The host
  can resync after garbage, reject corrupted lines, and count dropped records
  from sequence-number gaps. A test confirms that every single-bit flip is
  detected.
- **Streaming parser.** Commands arrive one byte at a time into a fixed
  32-byte buffer. Overlong lines are dropped safely and parsing recovers on
  the next line. Numbers are parsed strictly, with overflow checks.

## Layout

```
SensorLogger/SensorLogger.ino      Arduino glue: setup()/loop(), adapters for analogRead and Serial
SensorLogger/src/
  ring_buffer.h                    fixed-capacity circular buffer
  filters.h                        MovingAverage<N>, EmaFilter
  conversions.h/.cpp               ADC → mV, thermistor °C, light %
  format.h/.cpp                    fixed-point formatting, CRC-8, hex
  record.h/.cpp                    record struct + framed line format
  command_parser.h/.cpp            byte-stream command parser
  periodic_timer.h                 rollover-safe, drift-free timer
  sensor_logger.h/.cpp             the application core
tests/test_main.cpp                C++ unit + integration tests (host)
tests/test_read_log.py             tests for the PC reader
tools/simulate.cpp                 desktop simulator using synthetic sensors
tools/read_log.py                  PC reader: serial/stdin → validated CSV
Makefile
```

## Hardware

Arduino Uno (or any 5 V board with A0–A2):

| Pin | Circuit |
|-----|---------|
| A0  | 10 kΩ resistor from 5 V to A0; 10 kΩ NTC thermistor (B = 3950) from A0 to GND |
| A1  | LDR from 5 V to A1; 10 kΩ resistor from A1 to GND |
| A2  | Any 0–5 V signal, e.g. a potentiometer wiper |

For a 3.3 V or 12-bit board, change `vrefMv` and `adcBits` in `defaultConfig()`
(`sensor_logger.cpp`).

## Build, run, test

```bash
make test          # C++ core tests + Python reader tests (needs g++ and python3)
make sim           # run the core against simulated sensors for 10 s
./build/simulate 30 | python3 tools/read_log.py --csv out.csv

# Flash a real board (needs arduino-cli and `arduino-cli core install arduino:avr`)
make arduino                       # compile for arduino:avr:uno
make upload PORT=/dev/ttyACM0      # flash
python3 tools/read_log.py --port /dev/ttyACM0 --csv log.csv   # needs pyserial
```

You can also open `SensorLogger/SensorLogger.ino` in the Arduino IDE. It
compiles the `src/` folder automatically. Then use the Serial Monitor at
**115200 baud** with the line ending set to **Newline**.

> **Test note:** this run executed the host tests (394 C++ checks plus 7 Python
> tests, all passing) and the simulator. The AVR toolchain could not be
> downloaded here, so the sketch was not cross-compiled for the Uno. The core
> avoids the STL and exceptions, and its sources compile with
> `-fno-exceptions -fno-rtti` as on Arduino. Run `make arduino` locally to
> confirm.

### Serial commands

```
HELP                 # Commands: START | STOP | RATE <50-60000 ms> | STATUS | HELP
RATE 250             # OK rate 250 ms
STATUS               # STATUS running=1 rate_ms=250 records=17
STOP                 # OK stopped
START                # OK started
```

Lines that start with `#` are comments or responses. The reader ignores them.

### Example simulator output

```
# SensorLogger ready. Type HELP for commands.
# seq,ms,temp_c,light_pct,analog_mv
$0,0,24.08,68.3,3284*0B
$5,5000,24.49,79.2,3293*0F
$6,6000,24.47,81.2,3292*01
$10,10000,24.63,80.6,3302*B4
```

The reader writes clean CSV and prints a summary on stderr:

```
seq,ms,temp_c,light_pct,analog_mv
0,0,24.08,68.3,3284
1,1000,24.34,70.1,3290
...
31 records, 0 corrupt, 0 missing
```

## Possible extensions

- Log to an SD card (FAT16/32) with file rotation, and add a real-time clock
  for wall-clock timestamps.
- Use a binary framing format (COBS + CRC-16) to cut bandwidth by about 3×.
- Add I²C sensors (BME280, BH1750) behind the same `AnalogSource`-style
  interface.
- Sample with a timer interrupt into a lock-free single-producer/single-consumer ring buffer
  for jitter-free timing.
- Persist `RATE` in EEPROM so settings survive a reset.
- Live-plot in the browser with the Web Serial API.
- Use sleep modes between samples for battery-powered logging.
