#include "sensor_logger.h"

#include "format.h"

namespace sl {

LoggerConfig defaultConfig() {
    LoggerConfig c;
    c.tempChannel = 0;
    c.lightChannel = 1;
    c.voltageChannel = 2;
    c.adcBits = 10;
    c.vrefMv = 5000;
    c.thermistor = Thermistor{10000.0f, 10000.0f, 25.0f, 3950.0f};
    c.periodMs = 1000;
    c.autoStart = true;
    return c;
}

SensorLogger::SensorLogger(const LoggerConfig& cfg, AnalogSource& adc, TextSink& out)
    : cfg_(cfg), adc_(adc), out_(out), timer_(cfg.periodMs), running_(cfg.autoStart) {}

void SensorLogger::begin() {
    out_.write("# SensorLogger ready. Type HELP for commands.\r\n");
    out_.write(recordHeader());
    out_.write("\r\n");
}

Record SensorLogger::sample(uint32_t nowMs) {
    Record r;
    r.seq = seq_;
    r.ms = nowMs;

    // An unplugged thermistor must not poison the average, so invalid
    // readings bypass the filter and are reported as-is.
    int32_t t = thermistorCentiC(adc_.read(cfg_.tempChannel), cfg_.adcBits, cfg_.thermistor);
    r.tempCentiC = (t == kInvalidReading) ? t : tempAvg_.update(t);

    r.lightPermille = lightAvg_.update(lightPermille(adc_.read(cfg_.lightChannel), cfg_.adcBits));
    r.supplyMv = voltEma_.update(
        adcToMillivolts(adc_.read(cfg_.voltageChannel), cfg_.vrefMv, cfg_.adcBits));
    return r;
}

bool SensorLogger::tick(uint32_t nowMs) {
    if (!running_ || !timer_.due(nowMs)) return false;
    Record r = sample(nowMs);
    char line[kMaxRecordLine];
    if (formatRecord(r, line, sizeof(line)) == 0) return false;
    out_.write(line);
    ++seq_;
    return true;
}

void SensorLogger::onByte(char c) {
    Command cmd = parser_.feed(c);
    if (cmd.type != CommandType::None) handle(cmd);
}

void SensorLogger::handle(const Command& cmd) {
    switch (cmd.type) {
        case CommandType::Start:
            if (!running_) timer_.restart();  // first record comes right away
            running_ = true;
            out_.write("# OK started\r\n");
            break;
        case CommandType::Stop:
            running_ = false;
            out_.write("# OK stopped\r\n");
            break;
        case CommandType::Rate: {
            timer_.setPeriod(cmd.arg);
            char num[12];
            formatUnsigned(num, sizeof(num), cmd.arg);
            out_.write("# OK rate ");
            out_.write(num);
            out_.write(" ms\r\n");
            break;
        }
        case CommandType::Status:
            printStatus();
            break;
        case CommandType::Help:
            out_.write("# Commands: START | STOP | RATE <50-60000 ms> | STATUS | HELP\r\n");
            break;
        case CommandType::Invalid:
            out_.write("# ERR unknown command (try HELP)\r\n");
            break;
        case CommandType::None:
            break;
    }
}

void SensorLogger::printStatus() {
    char num[12];
    out_.write("# STATUS running=");
    out_.write(running_ ? "1" : "0");
    out_.write(" rate_ms=");
    formatUnsigned(num, sizeof(num), timer_.period());
    out_.write(num);
    out_.write(" records=");
    formatUnsigned(num, sizeof(num), seq_);
    out_.write(num);
    out_.write("\r\n");
}

}  // namespace sl
