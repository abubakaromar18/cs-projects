#include "format.h"

namespace sl {

size_t formatUnsigned(char* out, size_t cap, uint32_t value) {
    if (cap == 0) return 0;
    char tmp[10];  // uint32 max is 10 digits
    size_t n = 0;
    do {
        tmp[n++] = static_cast<char>('0' + value % 10);
        value /= 10;
    } while (value != 0);
    if (n + 1 > cap) {
        out[0] = '\0';
        return 0;
    }
    for (size_t i = 0; i < n; ++i) out[i] = tmp[n - 1 - i];  // digits were reversed
    out[n] = '\0';
    return n;
}

size_t formatFixed(char* out, size_t cap, int32_t value, uint8_t decimals) {
    if (cap == 0) return 0;
    // Work in uint32 so INT32_MIN negates safely.
    bool negative = value < 0;
    uint32_t mag = negative ? 0u - static_cast<uint32_t>(value) : static_cast<uint32_t>(value);

    uint32_t scale = 1;
    for (uint8_t i = 0; i < decimals; ++i) scale *= 10;
    uint32_t whole = mag / scale;
    uint32_t frac = mag % scale;

    char buf[24];
    size_t n = 0;
    if (negative) buf[n++] = '-';
    n += formatUnsigned(buf + n, sizeof(buf) - n, whole);
    if (decimals > 0) {
        buf[n++] = '.';
        // Zero-pad the fraction: 5 with 2 decimals is ".05", not ".5".
        for (int i = decimals - 1; i >= 0; --i) {
            uint32_t div = 1;
            for (int k = 0; k < i; ++k) div *= 10;
            buf[n++] = static_cast<char>('0' + (frac / div) % 10);
        }
    }
    if (n + 1 > cap) {
        out[0] = '\0';
        return 0;
    }
    for (size_t i = 0; i < n; ++i) out[i] = buf[i];
    out[n] = '\0';
    return n;
}

uint8_t crc8(const uint8_t* data, size_t len, uint8_t crc) {
    // Bitwise implementation: 8 shift/xor steps per byte. A 256-entry lookup
    // table would be faster but costs 256 bytes of flash; at serial speeds the
    // bitwise loop is never the bottleneck.
    for (size_t i = 0; i < len; ++i) {
        crc ^= data[i];
        for (uint8_t bit = 0; bit < 8; ++bit) {
            crc = (crc & 0x80) ? static_cast<uint8_t>((crc << 1) ^ 0x07)
                               : static_cast<uint8_t>(crc << 1);
        }
    }
    return crc;
}

void hexByte(uint8_t b, char out[2]) {
    static const char kDigits[] = "0123456789ABCDEF";
    out[0] = kDigits[b >> 4];
    out[1] = kDigits[b & 0x0F];
}

}  // namespace sl
