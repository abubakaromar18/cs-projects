#include "conversions.h"

#include <math.h>

namespace sl {

namespace {
constexpr float kKelvinOffset = 273.15f;

int32_t fullScale(uint8_t bits) { return (int32_t(1) << bits) - 1; }
}  // namespace

int32_t adcToMillivolts(uint16_t raw, int32_t vrefMv, uint8_t bits) {
    int32_t max = fullScale(bits);
    if (raw > max) raw = static_cast<uint16_t>(max);
    // Multiply before dividing to keep precision; add half the divisor to round.
    return (static_cast<int32_t>(raw) * vrefMv + max / 2) / max;
}

float thermistorOhms(uint16_t raw, uint8_t bits, const Thermistor& t) {
    int32_t max = fullScale(bits);
    if (raw == 0 || raw >= max) return -1.0f;  // shorted or open circuit
    // Divider: V = Vcc * Rt / (Rs + Rt)  =>  Rt = Rs * raw / (max - raw)
    return t.seriesOhms * static_cast<float>(raw) / static_cast<float>(max - raw);
}

int32_t thermistorCentiC(uint16_t raw, uint8_t bits, const Thermistor& t) {
    float r = thermistorOhms(raw, bits, t);
    if (r <= 0.0f) return kInvalidReading;
    float invT = 1.0f / (t.nominalC + kKelvinOffset) + logf(r / t.nominalOhms) / t.beta;
    float celsius = 1.0f / invT - kKelvinOffset;
    // Round to the nearest hundredth.
    float centi = celsius * 100.0f;
    return static_cast<int32_t>(centi >= 0 ? centi + 0.5f : centi - 0.5f);
}

int32_t lightPermille(uint16_t raw, uint8_t bits) {
    int32_t max = fullScale(bits);
    if (raw > max) raw = static_cast<uint16_t>(max);
    return (static_cast<int32_t>(raw) * 1000 + max / 2) / max;
}

}  // namespace sl
