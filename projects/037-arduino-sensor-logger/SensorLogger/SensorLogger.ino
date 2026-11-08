// SensorLogger — reads a thermistor, a light sensor and an analog voltage,
// smooths them, and streams checksummed CSV records over Serial.
//
// Wiring (Arduino Uno, 5 V):
//   A0: 10k resistor from 5V to A0, 10k NTC thermistor from A0 to GND
//   A1: LDR from 5V to A1, 10k resistor from A1 to GND
//   A2: any 0–5 V signal (e.g. a potentiometer wiper)
//
// Open the Serial Monitor at 115200 baud, line ending "Newline", and type
// HELP. All logic lives in src/ and is unit-tested on a PC; this file is only
// the glue between that core and the Arduino runtime.

#include "src/sensor_logger.h"

namespace {

// Adapts analogRead() to the core's AnalogSource interface.
class ArduinoAdc : public sl::AnalogSource {
public:
    uint16_t read(uint8_t channel) override {
        static const uint8_t kPins[] = {A0, A1, A2, A3, A4, A5};
        if (channel >= sizeof(kPins)) return 0;
        return static_cast<uint16_t>(analogRead(kPins[channel]));
    }
};

// Adapts Serial to the core's TextSink interface.
class SerialSink : public sl::TextSink {
public:
    void write(const char* text) override { Serial.print(text); }
};

ArduinoAdc adc;
SerialSink sink;
sl::SensorLogger logger(sl::defaultConfig(), adc, sink);

}  // namespace

void setup() {
    Serial.begin(115200);
    while (!Serial) {
        // Native-USB boards (Leonardo, Zero) need a moment to enumerate.
    }
    pinMode(LED_BUILTIN, OUTPUT);
    logger.begin();
}

void loop() {
    // Drain all pending command bytes without blocking.
    while (Serial.available() > 0) {
        logger.onByte(static_cast<char>(Serial.read()));
    }

    if (logger.tick(millis())) {
        // Blink on every record so you can see it is alive without a PC.
        digitalWrite(LED_BUILTIN, !digitalRead(LED_BUILTIN));
    }
}
