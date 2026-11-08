// Desktop simulator: runs the real SensorLogger core against synthetic
// sensors and prints what the board would send over Serial. Handy for trying
// the host tools without hardware:
//
//   make sim                       # 10 seconds of output
//   ./build/simulate 30 | python3 tools/read_log.py --csv out.csv
//
// Optional first argument: number of simulated seconds (default 10).

#include <math.h>
#include <stdio.h>
#include <stdlib.h>

#include "sensor_logger.h"

namespace {

// A room slowly warming up, a light that dims, a slightly noisy 3.3 V rail.
class SyntheticAdc : public sl::AnalogSource {
public:
    uint32_t nowMs = 0;

    uint16_t read(uint8_t channel) override {
        float t = nowMs / 1000.0f;
        float noise = static_cast<float>(rand() % 7 - 3);  // ±3 counts
        float value = 0;
        switch (channel) {
            case 0: value = 520 - 0.6f * t; break;               // thermistor: warming
            case 1: value = 700 + 150 * sinf(t / 4.0f); break;   // light: slow wave
            case 2: value = 675; break;                          // ~3.3 V of 5 V
            default: value = 0;
        }
        value += noise;
        if (value < 0) value = 0;
        if (value > 1023) value = 1023;
        return static_cast<uint16_t>(value);
    }
};

class StdoutSink : public sl::TextSink {
public:
    void write(const char* text) override { fputs(text, stdout); }
};

}  // namespace

int main(int argc, char** argv) {
    long seconds = argc > 1 ? strtol(argv[1], nullptr, 10) : 10;
    if (seconds <= 0) seconds = 10;
    srand(37);

    SyntheticAdc adc;
    StdoutSink out;
    sl::SensorLogger logger(sl::defaultConfig(), adc, out);
    logger.begin();

    // Step simulated time in 1 ms increments, exactly like loop() polling millis().
    for (uint32_t ms = 0; ms <= static_cast<uint32_t>(seconds) * 1000; ++ms) {
        adc.nowMs = ms;
        logger.tick(ms);
    }
    return 0;
}
