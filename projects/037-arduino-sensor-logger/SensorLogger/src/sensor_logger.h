// The application core: samples sensors on a schedule, smooths them, and
// streams framed records. It talks to hardware only through two tiny
// interfaces, so the exact same code runs on the board and in host tests.
#pragma once

#include <stddef.h>
#include <stdint.h>

#include "command_parser.h"
#include "conversions.h"
#include "filters.h"
#include "periodic_timer.h"
#include "record.h"

namespace sl {

// Hardware abstraction: where samples come from.
class AnalogSource {
public:
    virtual uint16_t read(uint8_t channel) = 0;
    virtual ~AnalogSource() {}
};

// Hardware abstraction: where text goes (Serial on the board).
class TextSink {
public:
    virtual void write(const char* text) = 0;
    virtual ~TextSink() {}
};

struct LoggerConfig {
    uint8_t tempChannel;
    uint8_t lightChannel;
    uint8_t voltageChannel;
    uint8_t adcBits;
    int32_t vrefMv;
    Thermistor thermistor;
    uint32_t periodMs;
    bool autoStart;
};

// Sensible defaults for an Arduino Uno: A0 thermistor, A1 LDR, A2 voltage.
LoggerConfig defaultConfig();

class SensorLogger {
public:
    SensorLogger(const LoggerConfig& cfg, AnalogSource& adc, TextSink& out);

    // Prints the banner and header. Call once from setup().
    void begin();

    // Call from every loop() iteration with the current millis().
    // Returns true if a record was emitted.
    bool tick(uint32_t nowMs);

    // Feed one received serial byte.
    void onByte(char c);

    bool running() const { return running_; }
    uint32_t periodMs() const { return timer_.period(); }
    uint32_t recordsSent() const { return seq_; }

    // Takes one filtered sample without emitting it (useful for tests).
    Record sample(uint32_t nowMs);

private:
    void handle(const Command& cmd);
    void printStatus();

    LoggerConfig cfg_;
    AnalogSource& adc_;
    TextSink& out_;
    PeriodicTimer timer_;
    CommandParser parser_;
    MovingAverage<8> tempAvg_;  // thermistors are slow; average more
    MovingAverage<4> lightAvg_;
    EmaFilter voltEma_{64};     // alpha = 0.25
    uint32_t seq_ = 0;
    bool running_;
};

}  // namespace sl
