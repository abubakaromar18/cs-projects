// Fixed-capacity circular buffer.
//
// Embedded targets like the ATmega328P (2 KB of RAM) have no heap worth
// using, so every container is sized at compile time. When the buffer is
// full, push() overwrites the oldest element, which is exactly the behaviour
// a sliding window over sensor samples needs.
#pragma once

#include <stddef.h>
#include <stdint.h>

namespace sl {

template <typename T, size_t N>
class RingBuffer {
    static_assert(N > 0, "RingBuffer capacity must be positive");

public:
    // Adds a value. Returns true if an old value was evicted to make room.
    bool push(const T& value, T* evicted = nullptr) {
        bool overwrote = false;
        if (count_ == N) {
            if (evicted) *evicted = data_[head_];
            overwrote = true;
        } else {
            ++count_;
        }
        data_[head_] = value;
        head_ = (head_ + 1) % N;
        return overwrote;
    }

    // Element i, where 0 is the oldest value still held.
    const T& operator[](size_t i) const {
        size_t start = (head_ + N - count_) % N;
        return data_[(start + i) % N];
    }

    // Most recently pushed value. Undefined when empty.
    const T& newest() const { return data_[(head_ + N - 1) % N]; }

    size_t size() const { return count_; }
    bool empty() const { return count_ == 0; }
    bool full() const { return count_ == N; }
    static constexpr size_t capacity() { return N; }

    void clear() {
        head_ = 0;
        count_ = 0;
    }

private:
    T data_[N] = {};
    size_t head_ = 0;   // index where the next push will land
    size_t count_ = 0;  // number of valid elements
};

}  // namespace sl
