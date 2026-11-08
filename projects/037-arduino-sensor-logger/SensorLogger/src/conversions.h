// Converting raw ADC counts into physical units.
//
// Results are fixed-point integers (e.g. centi-degrees Celsius) so they can
// be filtered and printed without floating point formatting, which the AVR
// printf family does not support by default.
#pragma once

#include <stdint.h>

namespace sl {

// Raw ADC count -> millivolts at the pin. `bits` is the ADC resolution
// (10 on an Uno, 12 on many ARM boards).
int32_t adcToMillivolts(uint16_t raw, int32_t vrefMv, uint8_t bits);

// Parameters of an NTC thermistor wired as the low side of a divider:
//   Vcc --- [seriesOhms] ---+--- [thermistor] --- GND
//                           |
//                         ADC pin
struct Thermistor {
    float seriesOhms;   // fixed resistor, e.g. 10000
    float nominalOhms;  // thermistor resistance at nominalC, e.g. 10000
    float nominalC;     // usually 25
    float beta;         // B coefficient from the datasheet, e.g. 3950
};

// Thermistor resistance from the divider reading. Returns a negative value
// for readings at the rails (open or shorted sensor).
float thermistorOhms(uint16_t raw, uint8_t bits, const Thermistor& t);

// Temperature in hundredths of a degree Celsius using the Beta equation:
//   1/T = 1/T0 + ln(R/R0)/B   (T in kelvin)
// Returns kInvalidReading if the sensor looks disconnected.
int32_t thermistorCentiC(uint16_t raw, uint8_t bits, const Thermistor& t);

// Light level in per-mille (0..1000) of full scale. With an LDR on the high
// side of the divider, brighter light -> lower LDR resistance -> higher count.
int32_t lightPermille(uint16_t raw, uint8_t bits);

constexpr int32_t kInvalidReading = INT32_MIN;

}  // namespace sl
