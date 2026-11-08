// One logged sample and its wire format.
//
// Each record is a single text line, framed and checksummed like NMEA:
//
//   $<seq>,<ms>,<tempC>,<light%>,<mV>*<CRC>\r\n
//   $42,21000,23.47,61.3,3021*9C
//
// `$` marks the start of a frame, `*` the end of the payload, and CRC is the
// CRC-8 of every byte between them as two hex digits. A host can resync after
// garbage by scanning for `$`, and reject lines corrupted on the wire.
#pragma once

#include <stddef.h>
#include <stdint.h>

namespace sl {

struct Record {
    uint32_t seq;           // monotonically increasing sample number
    uint32_t ms;            // millis() at sample time
    int32_t tempCentiC;     // hundredths of °C, or kInvalidReading
    int32_t lightPermille;  // 0..1000
    int32_t supplyMv;       // millivolts on the analog voltage channel
};

// Longest possible line: "$" + 10 + "," + 10 + "," + 12 + "," + 6 + "," + 11
// + "*XX\r\n" + NUL, rounded up.
constexpr size_t kMaxRecordLine = 72;

// Formats a record into `out`. Returns the line length (excluding NUL), or 0
// if `cap` is too small.
size_t formatRecord(const Record& r, char* out, size_t cap);

// The CSV header a host can print above the records.
const char* recordHeader();

}  // namespace sl
