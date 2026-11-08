// Host-side unit tests for the SensorLogger core. Built with the system C++
// compiler (no Arduino needed). A tiny assertion harness keeps it dependency
// free; run with `make test`.

#include <math.h>
#include <stdio.h>
#include <string.h>

#include <string>
#include <vector>

#include "command_parser.h"
#include "conversions.h"
#include "filters.h"
#include "format.h"
#include "periodic_timer.h"
#include "record.h"
#include "ring_buffer.h"
#include "sensor_logger.h"

using namespace sl;

// ---------------------------------------------------------------- harness
static int g_failures = 0;
static int g_checks = 0;

#define CHECK(cond)                                                       \
    do {                                                                  \
        ++g_checks;                                                       \
        if (!(cond)) {                                                    \
            ++g_failures;                                                 \
            printf("  FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond);      \
        }                                                                 \
    } while (0)

#define CHECK_EQ(a, b)                                                    \
    do {                                                                  \
        ++g_checks;                                                       \
        long long va = (long long)(a), vb = (long long)(b);               \
        if (va != vb) {                                                   \
            ++g_failures;                                                 \
            printf("  FAIL %s:%d: %s == %s (%lld vs %lld)\n", __FILE__,   \
                   __LINE__, #a, #b, va, vb);                             \
        }                                                                 \
    } while (0)

#define CHECK_STR(a, b)                                                   \
    do {                                                                  \
        ++g_checks;                                                       \
        std::string sa(a), sb(b);                                         \
        if (sa != sb) {                                                   \
            ++g_failures;                                                 \
            printf("  FAIL %s:%d: \"%s\" != \"%s\"\n", __FILE__, __LINE__,\
                   sa.c_str(), sb.c_str());                               \
        }                                                                 \
    } while (0)

#define TEST(name) static void name()
#define RUN(name)                      \
    do {                               \
        printf("%s\n", #name);         \
        name();                        \
    } while (0)

// ---------------------------------------------------------------- fakes
struct FakeAdc : AnalogSource {
    uint16_t values[6] = {512, 512, 512, 0, 0, 0};
    uint16_t read(uint8_t ch) override { return ch < 6 ? values[ch] : 0; }
};

struct CaptureSink : TextSink {
    std::string text;
    void write(const char* s) override { text += s; }
    std::vector<std::string> lines() const {
        std::vector<std::string> out;
        size_t start = 0;
        while (true) {
            size_t nl = text.find("\r\n", start);
            if (nl == std::string::npos) break;
            out.push_back(text.substr(start, nl - start));
            start = nl + 2;
        }
        return out;
    }
};

static void feed(SensorLogger& lg, const char* s) {
    while (*s) lg.onByte(*s++);
}

// ---------------------------------------------------------------- ring buffer
TEST(ring_buffer_fills_and_overwrites_oldest) {
    RingBuffer<int, 3> rb;
    CHECK(rb.empty());
    CHECK(!rb.push(1));
    CHECK(!rb.push(2));
    CHECK(!rb.push(3));
    CHECK(rb.full());
    int evicted = -1;
    CHECK(rb.push(4, &evicted));
    CHECK_EQ(evicted, 1);
    CHECK_EQ(rb.size(), 3);
    CHECK_EQ(rb[0], 2);
    CHECK_EQ(rb[1], 3);
    CHECK_EQ(rb[2], 4);
    CHECK_EQ(rb.newest(), 4);
    rb.clear();
    CHECK(rb.empty());
}

// ---------------------------------------------------------------- filters
TEST(moving_average_tracks_window) {
    MovingAverage<4> ma;
    CHECK_EQ(ma.value(), 0);
    CHECK_EQ(ma.update(10), 10);
    CHECK_EQ(ma.update(20), 15);
    ma.update(30);
    CHECK_EQ(ma.update(40), 25);
    CHECK(ma.warmedUp());
    // 10 falls out: (20+30+40+100)/4 = 47.5 -> 48
    CHECK_EQ(ma.update(100), 48);
}

TEST(moving_average_rounds_negative_values_symmetrically) {
    MovingAverage<2> ma;
    ma.update(-1);
    CHECK_EQ(ma.update(-2), -2);  // -1.5 rounds away from zero
    MovingAverage<2> pos;
    pos.update(1);
    CHECK_EQ(pos.update(2), 2);
}

TEST(ema_seeds_with_first_sample_and_converges) {
    EmaFilter ema(64);  // alpha 0.25
    CHECK_EQ(ema.update(1000), 1000);
    CHECK_EQ(ema.update(2000), 1250);
    int32_t v = 0;
    for (int i = 0; i < 60; ++i) v = ema.update(2000);
    CHECK_EQ(v, 2000);
    ema.reset();
    CHECK_EQ(ema.update(-500), -500);
}

// ---------------------------------------------------------------- conversions
TEST(adc_to_millivolts) {
    CHECK_EQ(adcToMillivolts(0, 5000, 10), 0);
    CHECK_EQ(adcToMillivolts(1023, 5000, 10), 5000);
    CHECK_EQ(adcToMillivolts(512, 5000, 10), 2502);
    CHECK_EQ(adcToMillivolts(4095, 3300, 12), 3300);
    CHECK_EQ(adcToMillivolts(2000, 5000, 10), 5000);  // clamps out-of-range input
}

TEST(thermistor_at_midscale_reads_nominal_temperature) {
    Thermistor t{10000, 10000, 25, 3950};
    // Equal resistors -> half scale. 1023/2 is not exact, so allow 0.1 °C.
    int32_t c = thermistorCentiC(512, 10, t);
    CHECK(c > 2490 && c < 2510);
}

TEST(thermistor_direction_and_known_point) {
    Thermistor t{10000, 10000, 25, 3950};
    // NTC: colder -> higher resistance -> higher reading on the low side.
    CHECK(thermistorCentiC(700, 10, t) < thermistorCentiC(512, 10, t));
    CHECK(thermistorCentiC(300, 10, t) > thermistorCentiC(512, 10, t));

    // Pick the reading for R = 32650 Ω (≈ 0 °C for B=3950 around 25 °C):
    // raw = 1023 * R / (R + 10000) ≈ 783.
    float r = thermistorOhms(783, 10, t);
    CHECK(fabsf(r - 32650.0f) / 32650.0f < 0.01f);
    int32_t c = thermistorCentiC(783, 10, t);
    CHECK(c > -100 && c < 100);
}

TEST(thermistor_rails_are_invalid) {
    Thermistor t{10000, 10000, 25, 3950};
    CHECK_EQ(thermistorCentiC(0, 10, t), kInvalidReading);
    CHECK_EQ(thermistorCentiC(1023, 10, t), kInvalidReading);
}

TEST(light_permille) {
    CHECK_EQ(lightPermille(0, 10), 0);
    CHECK_EQ(lightPermille(1023, 10), 1000);
    CHECK_EQ(lightPermille(512, 10), 500);
}

// ---------------------------------------------------------------- formatting
TEST(format_fixed_cases) {
    char b[24];
    formatFixed(b, sizeof b, 2345, 2);
    CHECK_STR(b, "23.45");
    formatFixed(b, sizeof b, -5, 2);
    CHECK_STR(b, "-0.05");
    formatFixed(b, sizeof b, 100, 2);
    CHECK_STR(b, "1.00");
    formatFixed(b, sizeof b, 0, 1);
    CHECK_STR(b, "0.0");
    formatFixed(b, sizeof b, 42, 0);
    CHECK_STR(b, "42");
    formatFixed(b, sizeof b, INT32_MIN, 0);
    CHECK_STR(b, "-2147483648");
    CHECK_EQ(formatFixed(b, 4, 12345, 2), 0);  // "123.45" doesn't fit
    CHECK_STR(b, "");
}

TEST(format_unsigned_cases) {
    char b[12];
    CHECK_EQ(formatUnsigned(b, sizeof b, 0), 1);
    CHECK_STR(b, "0");
    formatUnsigned(b, sizeof b, 4294967295u);
    CHECK_STR(b, "4294967295");
    CHECK_EQ(formatUnsigned(b, 3, 123), 0);
}

TEST(crc8_matches_standard_check_value) {
    const char* s = "123456789";
    CHECK_EQ(crc8(reinterpret_cast<const uint8_t*>(s), strlen(s)), 0xF4);
    CHECK_EQ(crc8(nullptr, 0), 0);
    // Incremental computation equals one-shot.
    uint8_t part = crc8(reinterpret_cast<const uint8_t*>(s), 4);
    CHECK_EQ(crc8(reinterpret_cast<const uint8_t*>(s + 4), 5, part), 0xF4);
}

TEST(crc8_detects_single_bit_flip) {
    char msg[] = "1,1000,23.45,50.0,2500";
    uint8_t good = crc8(reinterpret_cast<uint8_t*>(msg), strlen(msg));
    for (size_t i = 0; i < strlen(msg); ++i) {
        for (int bit = 0; bit < 8; ++bit) {
            msg[i] ^= static_cast<char>(1 << bit);
            CHECK(crc8(reinterpret_cast<uint8_t*>(msg), strlen(msg)) != good);
            msg[i] ^= static_cast<char>(1 << bit);
        }
    }
}

TEST(record_line_format) {
    Record r{42, 21000, 2347, 613, 3021};
    char line[kMaxRecordLine];
    size_t n = formatRecord(r, line, sizeof line);
    CHECK(n > 0);
    std::string s(line);
    CHECK_EQ(n, s.size());
    CHECK(s.rfind("$42,21000,23.47,61.3,3021*", 0) == 0);
    CHECK(s.size() >= 4 && s.substr(s.size() - 2) == "\r\n");

    // Verify the embedded checksum.
    size_t star = s.find('*');
    std::string payload = s.substr(1, star - 1);
    uint8_t crc = crc8(reinterpret_cast<const uint8_t*>(payload.data()), payload.size());
    char hex[3] = {0, 0, 0};
    hexByte(crc, hex);
    CHECK_STR(s.substr(star + 1, 2), hex);
}

TEST(record_invalid_temperature_and_worst_case_length) {
    Record bad{1, 2, kInvalidReading, 0, 0};
    char line[kMaxRecordLine];
    formatRecord(bad, line, sizeof line);
    CHECK(std::string(line).find(",NaN,") != std::string::npos);

    Record worst{UINT32_MAX, UINT32_MAX, INT32_MIN + 1, INT32_MIN, INT32_MIN};
    CHECK(formatRecord(worst, line, sizeof line) > 0);  // kMaxRecordLine is enough

    char tiny[10];
    CHECK_EQ(formatRecord(worst, tiny, sizeof tiny), 0);
    CHECK_STR(tiny, "");
}

// ---------------------------------------------------------------- commands
TEST(parse_commands) {
    CHECK(CommandParser::parseLine("START").type == CommandType::Start);
    CHECK(CommandParser::parseLine("  stop  ").type == CommandType::Stop);
    CHECK(CommandParser::parseLine("Status").type == CommandType::Status);
    CHECK(CommandParser::parseLine("help").type == CommandType::Help);
    CHECK(CommandParser::parseLine("").type == CommandType::None);
    CHECK(CommandParser::parseLine("   ").type == CommandType::None);

    Command c = CommandParser::parseLine("rate 250");
    CHECK(c.type == CommandType::Rate);
    CHECK_EQ(c.arg, 250);

    CHECK(CommandParser::parseLine("RATE").type == CommandType::Invalid);
    CHECK(CommandParser::parseLine("RATE 10").type == CommandType::Invalid);     // too fast
    CHECK(CommandParser::parseLine("RATE 99999").type == CommandType::Invalid);  // too slow
    CHECK(CommandParser::parseLine("RATE -5").type == CommandType::Invalid);
    CHECK(CommandParser::parseLine("RATE 1e3").type == CommandType::Invalid);
    CHECK(CommandParser::parseLine("RATE 99999999999999").type == CommandType::Invalid);
    CHECK(CommandParser::parseLine("STARTX").type == CommandType::Invalid);
    CHECK(CommandParser::parseLine("START now").type == CommandType::Invalid);
    CHECK(CommandParser::parseLine("launch").type == CommandType::Invalid);
}

TEST(parser_streams_bytes_and_handles_crlf_and_overflow) {
    CommandParser p;
    const char* in = "RATE 500\r\n";
    std::vector<Command> got;
    for (const char* c = in; *c; ++c) {
        Command cmd = p.feed(*c);
        if (cmd.type != CommandType::None) got.push_back(cmd);
    }
    CHECK_EQ(got.size(), 1);  // the \n after \r is a blank line, ignored
    CHECK(got[0].type == CommandType::Rate && got[0].arg == 500);

    // A 100-byte line overflows the 32-byte buffer and is rejected once,
    // then the parser recovers for the next line.
    for (int i = 0; i < 100; ++i) CHECK(p.feed('A').type == CommandType::None);
    CHECK(p.feed('\n').type == CommandType::Invalid);
    for (const char* c = "STOP"; *c; ++c) p.feed(*c);
    CHECK(p.feed('\n').type == CommandType::Stop);
}

// ---------------------------------------------------------------- timer
TEST(timer_fires_on_schedule_without_drift) {
    PeriodicTimer t(100);
    CHECK(t.due(0));
    CHECK(!t.due(50));
    CHECK(t.due(103));   // late by 3 ms...
    CHECK(!t.due(199));
    CHECK(t.due(200));   // ...but the next tick is still at 200, not 203
}

TEST(timer_resyncs_after_long_stall) {
    PeriodicTimer t(100);
    t.due(0);
    CHECK(t.due(1000));   // way behind: fire once...
    CHECK(!t.due(1001));  // ...not a burst of nine catch-up ticks
    CHECK(t.due(1100));
}

TEST(timer_survives_millis_rollover) {
    PeriodicTimer t(100);
    uint32_t start = UINT32_MAX - 150;
    CHECK(t.due(start));
    CHECK(t.due(start + 100));   // UINT32_MAX - 50
    CHECK(!t.due(10));           // wrapped: only 60 ms elapsed
    CHECK(t.due(49));            // 100 ms after UINT32_MAX - 50
}

// ---------------------------------------------------------------- integration
TEST(logger_emits_records_at_rate) {
    FakeAdc adc;
    CaptureSink out;
    LoggerConfig cfg = defaultConfig();
    cfg.periodMs = 100;
    SensorLogger lg(cfg, adc, out);
    lg.begin();

    int emitted = 0;
    for (uint32_t ms = 0; ms <= 1000; ms += 10) emitted += lg.tick(ms) ? 1 : 0;
    CHECK_EQ(emitted, 11);  // t = 0, 100, ..., 1000
    CHECK_EQ(lg.recordsSent(), 11);

    std::vector<std::string> lines = out.lines();
    CHECK_EQ(lines.size(), 2 + 11);
    CHECK(lines[0].rfind("# SensorLogger", 0) == 0);
    CHECK(lines[2].rfind("$0,0,", 0) == 0);
    CHECK(lines[12].rfind("$10,1000,", 0) == 0);
}

TEST(logger_commands_change_behaviour) {
    FakeAdc adc;
    CaptureSink out;
    SensorLogger lg(defaultConfig(), adc, out);

    feed(lg, "STOP\n");
    CHECK(!lg.running());
    CHECK(!lg.tick(0));
    CHECK(out.text.find("# OK stopped") != std::string::npos);

    feed(lg, "RATE 250\n");
    CHECK_EQ(lg.periodMs(), 250);
    CHECK(out.text.find("# OK rate 250 ms") != std::string::npos);

    feed(lg, "START\n");
    CHECK(lg.running());
    CHECK(lg.tick(5000));   // restart fires immediately
    CHECK(!lg.tick(5100));
    CHECK(lg.tick(5250));

    feed(lg, "STATUS\n");
    CHECK(out.text.find("# STATUS running=1 rate_ms=250 records=2") != std::string::npos);

    feed(lg, "bogus\n");
    CHECK(out.text.find("# ERR unknown command") != std::string::npos);
}

TEST(logger_filters_noise_and_reports_unplugged_sensor) {
    FakeAdc adc;
    CaptureSink out;
    SensorLogger lg(defaultConfig(), adc, out);

    // Alternate the light channel between two values: the 4-sample average
    // should settle at their midpoint.
    Record r{};
    for (int i = 0; i < 8; ++i) {
        adc.values[1] = (i % 2) ? 600 : 400;
        r = lg.sample(i);
    }
    CHECK_EQ(r.lightPermille, 489);  // (391 + 587) / 2
    CHECK(r.tempCentiC > 2490 && r.tempCentiC < 2510);

    adc.values[0] = 1023;  // thermistor disconnected -> divider pulled high
    r = lg.sample(100);
    CHECK_EQ(r.tempCentiC, kInvalidReading);
    adc.values[0] = 512;   // plug it back in: the average was not poisoned
    r = lg.sample(200);
    CHECK(r.tempCentiC > 2490 && r.tempCentiC < 2510);
}

int main() {
    RUN(ring_buffer_fills_and_overwrites_oldest);
    RUN(moving_average_tracks_window);
    RUN(moving_average_rounds_negative_values_symmetrically);
    RUN(ema_seeds_with_first_sample_and_converges);
    RUN(adc_to_millivolts);
    RUN(thermistor_at_midscale_reads_nominal_temperature);
    RUN(thermistor_direction_and_known_point);
    RUN(thermistor_rails_are_invalid);
    RUN(light_permille);
    RUN(format_fixed_cases);
    RUN(format_unsigned_cases);
    RUN(crc8_matches_standard_check_value);
    RUN(crc8_detects_single_bit_flip);
    RUN(record_line_format);
    RUN(record_invalid_temperature_and_worst_case_length);
    RUN(parse_commands);
    RUN(parser_streams_bytes_and_handles_crlf_and_overflow);
    RUN(timer_fires_on_schedule_without_drift);
    RUN(timer_resyncs_after_long_stall);
    RUN(timer_survives_millis_rollover);
    RUN(logger_emits_records_at_rate);
    RUN(logger_commands_change_behaviour);
    RUN(logger_filters_noise_and_reports_unplugged_sensor);

    printf("\n%d checks, %d failures\n", g_checks, g_failures);
    return g_failures == 0 ? 0 : 1;
}
