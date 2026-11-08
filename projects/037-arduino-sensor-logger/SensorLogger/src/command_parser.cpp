#include "command_parser.h"

namespace sl {

namespace {

char upper(char c) { return (c >= 'a' && c <= 'z') ? static_cast<char>(c - 'a' + 'A') : c; }
bool isSpace(char c) { return c == ' ' || c == '\t'; }

// Case-insensitive match of `word` at the start of `s`, followed by end or space.
// On success, advances *s past the word.
bool matchWord(const char** s, const char* word) {
    const char* p = *s;
    while (*word) {
        if (upper(*p) != *word) return false;
        ++p;
        ++word;
    }
    if (*p != '\0' && !isSpace(*p)) return false;
    *s = p;
    return true;
}

void skipSpaces(const char** s) {
    while (isSpace(**s)) ++*s;
}

// Strict unsigned decimal parse; rejects empty input, signs, junk and overflow.
bool parseUint(const char* s, uint32_t* out) {
    if (*s == '\0') return false;
    uint32_t v = 0;
    while (*s >= '0' && *s <= '9') {
        uint32_t d = static_cast<uint32_t>(*s - '0');
        if (v > (UINT32_MAX - d) / 10) return false;
        v = v * 10 + d;
        ++s;
    }
    skipSpaces(&s);
    if (*s != '\0') return false;
    *out = v;
    return true;
}

}  // namespace

Command CommandParser::parseLine(const char* line) {
    Command cmd;
    const char* p = line;
    skipSpaces(&p);
    if (*p == '\0') return cmd;  // blank line: nothing to do

    auto noArgs = [&](CommandType t) {
        skipSpaces(&p);
        cmd.type = (*p == '\0') ? t : CommandType::Invalid;
        return cmd;
    };

    if (matchWord(&p, "START")) return noArgs(CommandType::Start);
    if (matchWord(&p, "STOP")) return noArgs(CommandType::Stop);
    if (matchWord(&p, "STATUS")) return noArgs(CommandType::Status);
    if (matchWord(&p, "HELP")) return noArgs(CommandType::Help);
    if (matchWord(&p, "RATE")) {
        skipSpaces(&p);
        uint32_t v = 0;
        if (parseUint(p, &v) && v >= kMinPeriodMs && v <= kMaxPeriodMs) {
            cmd.type = CommandType::Rate;
            cmd.arg = v;
        } else {
            cmd.type = CommandType::Invalid;
        }
        return cmd;
    }
    cmd.type = CommandType::Invalid;
    return cmd;
}

Command CommandParser::feed(char c) {
    if (c == '\n' || c == '\r') {
        Command cmd;
        if (overflow_) {
            cmd.type = CommandType::Invalid;  // report the dropped line once
        } else {
            buf_[len_] = '\0';
            cmd = parseLine(buf_);
        }
        len_ = 0;
        overflow_ = false;
        return cmd;
    }
    if (len_ + 1 < kCap) {
        buf_[len_++] = c;
    } else {
        overflow_ = true;  // keep swallowing until the newline
    }
    return Command{};
}

}  // namespace sl
