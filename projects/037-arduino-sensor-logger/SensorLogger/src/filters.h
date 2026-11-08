// Integer-only smoothing filters for noisy ADC readings.
//
// AVR chips have no FPU, so filters work on int32_t and avoid division in
// the hot path where possible.
#pragma once

#include <stdint.h>

#include "ring_buffer.h"

namespace sl {

// Simple moving average over the last N samples, O(1) per update thanks to a
// running sum: add the new sample, subtract the one that fell out of the
// window.
template <size_t N>
class MovingAverage {
public:
    int32_t update(int32_t sample) {
        int32_t evicted = 0;
        if (window_.push(sample, &evicted)) sum_ -= evicted;
        sum_ += sample;
        return value();
    }

    // Rounded mean of the samples currently in the window (0 when empty).
    int32_t value() const {
        int32_t n = static_cast<int32_t>(window_.size());
        if (n == 0) return 0;
        // Round half away from zero so negative temperatures behave too.
        return sum_ >= 0 ? (sum_ + n / 2) / n : (sum_ - n / 2) / n;
    }

    bool warmedUp() const { return window_.full(); }
    size_t count() const { return window_.size(); }
    void reset() {
        window_.clear();
        sum_ = 0;
    }

private:
    RingBuffer<int32_t, N> window_;
    int32_t sum_ = 0;
};

// Exponential moving average: y += alpha * (x - y), with alpha expressed as
// alphaQ8 / 256. The state is kept with 8 extra fractional bits so small
// steps are not lost to integer truncation.
class EmaFilter {
public:
    explicit EmaFilter(uint8_t alphaQ8 = 64) : alpha_(alphaQ8) {}

    int32_t update(int32_t sample) {
        int32_t scaled = sample * 256;
        if (!primed_) {
            state_ = scaled;  // first sample seeds the filter: no slow ramp from 0
            primed_ = true;
        } else {
            state_ += ((scaled - state_) * alpha_) / 256;
        }
        return value();
    }

    int32_t value() const {
        return state_ >= 0 ? (state_ + 128) / 256 : (state_ - 128) / 256;
    }

    void reset() { primed_ = false; state_ = 0; }

private:
    int32_t state_ = 0;  // Q8 fixed point
    uint8_t alpha_;
    bool primed_ = false;
};

}  // namespace sl
