#!/usr/bin/env python3
"""Host-side reader for SensorLogger output.

Reads lines from a serial port (needs `pyserial`) or from stdin, verifies the
CRC-8 on every record, and prints or saves clean CSV. Corrupted lines are
counted and skipped instead of silently producing bad data.

    python3 tools/read_log.py --port /dev/ttyACM0            # live from a board
    ./build/simulate 30 | python3 tools/read_log.py --csv out.csv
"""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass
from typing import Iterable, Iterator, Optional, TextIO

FIELDS = ["seq", "ms", "temp_c", "light_pct", "analog_mv"]


def crc8(data: bytes, crc: int = 0) -> int:
    """CRC-8/SMBUS (poly 0x07, init 0) — must match format.cpp on the board."""
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = ((crc << 1) ^ 0x07) & 0xFF if crc & 0x80 else (crc << 1) & 0xFF
    return crc


@dataclass
class Record:
    seq: int
    ms: int
    temp_c: Optional[float]  # None when the thermistor was unplugged
    light_pct: float
    analog_mv: int

    def row(self) -> list:
        return [self.seq, self.ms, "" if self.temp_c is None else self.temp_c,
                self.light_pct, self.analog_mv]


class FrameError(ValueError):
    """A line looked like a record but failed validation."""


def parse_line(line: str) -> Optional[Record]:
    """Parse one line. Returns None for comments/blank lines, raises FrameError
    for corrupted records."""
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    start = line.rfind("$")  # resync: ignore any garbage before the last '$'
    if start < 0:
        raise FrameError("no start marker")
    line = line[start:]
    star = line.find("*")
    if star < 0 or len(line) != star + 3:
        raise FrameError("bad framing")
    payload = line[1:star]
    try:
        expected = int(line[star + 1:], 16)
    except ValueError as exc:
        raise FrameError("bad checksum digits") from exc
    actual = crc8(payload.encode("ascii", errors="replace"))
    if actual != expected:
        raise FrameError(f"checksum mismatch ({actual:02X} != {expected:02X})")
    parts = payload.split(",")
    if len(parts) != len(FIELDS):
        raise FrameError("wrong field count")
    try:
        return Record(
            seq=int(parts[0]),
            ms=int(parts[1]),
            temp_c=None if parts[2] == "NaN" else float(parts[2]),
            light_pct=float(parts[3]),
            analog_mv=int(parts[4]),
        )
    except ValueError as exc:
        raise FrameError("bad number") from exc


@dataclass
class Stats:
    good: int = 0
    corrupt: int = 0
    gaps: int = 0  # records lost between good ones, judged by sequence numbers


def read_records(lines: Iterable[str], stats: Stats, verbose: bool = False) -> Iterator[Record]:
    last_seq: Optional[int] = None
    for line in lines:
        try:
            rec = parse_line(line)
        except FrameError as err:
            stats.corrupt += 1
            if verbose:
                print(f"skip: {err}: {line.strip()!r}", file=sys.stderr)
            continue
        if rec is None:
            continue
        if last_seq is not None and rec.seq > last_seq + 1:
            stats.gaps += rec.seq - last_seq - 1
        last_seq = rec.seq
        stats.good += 1
        yield rec


def serial_lines(port: str, baud: int) -> Iterator[str]:
    try:
        import serial  # type: ignore
    except ImportError:
        sys.exit("pyserial is required for --port: pip install pyserial")
    with serial.Serial(port, baud, timeout=2) as ser:
        while True:
            raw = ser.readline()
            if raw:
                yield raw.decode("ascii", errors="replace")


def main(argv: Optional[list] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--port", help="serial port, e.g. /dev/ttyACM0 or COM3 (default: stdin)")
    ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--csv", help="write validated records to this CSV file")
    ap.add_argument("-v", "--verbose", action="store_true", help="report skipped lines")
    args = ap.parse_args(argv)

    lines = serial_lines(args.port, args.baud) if args.port else sys.stdin
    stats = Stats()
    out: TextIO = open(args.csv, "w", newline="") if args.csv else sys.stdout
    try:
        writer = csv.writer(out)
        writer.writerow(FIELDS)
        for rec in read_records(lines, stats, args.verbose):
            writer.writerow(rec.row())
            out.flush()
    except KeyboardInterrupt:
        pass
    finally:
        if args.csv:
            out.close()
    print(f"{stats.good} records, {stats.corrupt} corrupt, {stats.gaps} missing",
          file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
