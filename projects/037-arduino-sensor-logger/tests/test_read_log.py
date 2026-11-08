"""Tests for the host-side reader (run: python3 -m unittest discover tests)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))

from read_log import FrameError, Stats, crc8, parse_line, read_records  # noqa: E402


def frame(payload: str) -> str:
    return f"${payload}*{crc8(payload.encode()):02X}\r\n"


class Crc8Test(unittest.TestCase):
    def test_standard_check_value(self):
        self.assertEqual(crc8(b"123456789"), 0xF4)


class ParseLineTest(unittest.TestCase):
    def test_valid_record(self):
        rec = parse_line(frame("42,21000,23.47,61.3,3021"))
        self.assertEqual((rec.seq, rec.ms, rec.temp_c, rec.light_pct, rec.analog_mv),
                         (42, 21000, 23.47, 61.3, 3021))

    def test_nan_temperature(self):
        self.assertIsNone(parse_line(frame("1,2,NaN,0.0,0")).temp_c)

    def test_comments_and_blank_lines_are_ignored(self):
        self.assertIsNone(parse_line("# OK started\r\n"))
        self.assertIsNone(parse_line("   \n"))

    def test_resyncs_after_leading_garbage(self):
        rec = parse_line("\x00\xff" + frame("7,700,20.00,50.0,1000"))
        self.assertEqual(rec.seq, 7)

    def test_corruption_is_rejected(self):
        good = frame("42,21000,23.47,61.3,3021")
        with self.assertRaises(FrameError):
            parse_line(good.replace("23.47", "28.47"))
        with self.assertRaises(FrameError):
            parse_line(good[:-5])  # truncated
        with self.assertRaises(FrameError):
            parse_line("garbage")


class ReadRecordsTest(unittest.TestCase):
    def test_counts_good_corrupt_and_gaps(self):
        lines = [
            "# SensorLogger ready\r\n",
            frame("0,0,20.00,50.0,1000"),
            frame("1,1000,20.00,50.0,1000").replace("50.0", "59.0"),  # corrupt
            frame("3,3000,20.10,50.0,1000"),                          # seq 1,2 lost
        ]
        stats = Stats()
        recs = list(read_records(lines, stats))
        self.assertEqual([r.seq for r in recs], [0, 3])
        self.assertEqual((stats.good, stats.corrupt, stats.gaps), (2, 1, 2))


if __name__ == "__main__":
    unittest.main()
