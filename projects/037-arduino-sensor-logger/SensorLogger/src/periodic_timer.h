// Non-blocking periodic timer driven by millis().
//
// millis() is a uint32_t that wraps to 0 after ~49.7 days. Comparing
// `now >= next` breaks at the wrap; comparing the *elapsed* time
// `now - last >= period` with unsigned arithmetic stays correct across it,
// because unsigned subtraction is modulo 2^32.
#pragma once

#include <stdint.h>

namespace sl {

class PeriodicTimer {
public:
    explicit PeriodicTimer(uint32_t periodMs) : period_(periodMs) {}

    // Returns true at most once per period. Advances by whole periods so the
    // schedule does not drift when loop() runs late, but if we fell more than
    // one period behind it resyncs to `now` rather than firing a burst.
    bool due(uint32_t now) {
        if (!started_) {
            started_ = true;
            last_ = now;
            return true;  // fire immediately on the first call
        }
        uint32_t elapsed = now - last_;
        if (elapsed < period_) return false;
        last_ = (elapsed < 2 * period_) ? last_ + period_ : now;
        return true;
    }

    void setPeriod(uint32_t periodMs) { period_ = periodMs; }
    uint32_t period() const { return period_; }
    void restart() { started_ = false; }

private:
    uint32_t period_;
    uint32_t last_ = 0;
    bool started_ = false;
};

}  // namespace sl
