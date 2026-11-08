// Small, allocation-free text helpers: fixed-point formatting and CRC-8.
#pragma once

#include <stddef.h>
#include <stdint.h>

namespace sl {

// Writes `value / 10^decimals` as decimal text, e.g. (2345, 2) -> "23.45",
// (-5, 2) -> "-0.05". Always NUL-terminates when cap > 0.
// Returns the number of characters written (excluding NUL), or 0 if the
// buffer was too small.
size_t formatFixed(char* out, size_t cap, int32_t value, uint8_t decimals);

// Same idea for unsigned integers (no decimal point).
size_t formatUnsigned(char* out, size_t cap, uint32_t value);

// CRC-8/SMBUS: polynomial x^8 + x^2 + x + 1 (0x07), init 0, no reflection.
// Check value for "123456789" is 0xF4.
uint8_t crc8(const uint8_t* data, size_t len, uint8_t crc = 0);

// Two upper-case hex digits for a byte.
void hexByte(uint8_t b, char out[2]);

}  // namespace sl
