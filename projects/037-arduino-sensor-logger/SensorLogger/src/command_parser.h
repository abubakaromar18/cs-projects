// Line-oriented command parser fed one byte at a time from Serial.
//
// Commands (case-insensitive, terminated by \n or \r):
//   START            begin streaming records
//   STOP             pause streaming
//   RATE <ms>        set sample period (50..60000 ms)
//   STATUS           print current settings
//   HELP             list commands
//
// The parser never blocks and never allocates: bytes accumulate in a fixed
// buffer, and a line that overflows it is discarded up to the next newline.
#pragma once

#include <stddef.h>
#include <stdint.h>

namespace sl {

enum class CommandType : uint8_t {
    None,     // no complete line yet
    Start,
    Stop,
    Rate,
    Status,
    Help,
    Invalid,  // a line arrived but was not understood
};

struct Command {
    CommandType type = CommandType::None;
    uint32_t arg = 0;  // RATE period in ms
};

constexpr uint32_t kMinPeriodMs = 50;
constexpr uint32_t kMaxPeriodMs = 60000;

class CommandParser {
public:
    // Feeds one byte. Returns a Command whose type is None until a full line
    // has been received.
    Command feed(char c);

    // Parses a complete line (without terminator). Exposed for testing.
    static Command parseLine(const char* line);

private:
    static constexpr size_t kCap = 32;
    char buf_[kCap] = {};
    size_t len_ = 0;
    bool overflow_ = false;
};

}  // namespace sl
