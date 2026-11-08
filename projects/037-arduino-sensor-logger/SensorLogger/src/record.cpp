#include "record.h"

#include "conversions.h"
#include "format.h"

namespace sl {

namespace {

// Appends text at out[*pos], tracking overflow instead of writing past cap.
class LineBuilder {
public:
    LineBuilder(char* out, size_t cap) : out_(out), cap_(cap) {}

    void put(char c) {
        if (pos_ + 1 < cap_) out_[pos_++] = c;
        else ok_ = false;
    }
    void put(const char* s) {
        while (*s) put(*s++);
    }
    void fixed(int32_t v, uint8_t decimals) {
        char tmp[16];
        formatFixed(tmp, sizeof(tmp), v, decimals);
        put(tmp);
    }
    void unsignedNum(uint32_t v) {
        char tmp[12];
        formatUnsigned(tmp, sizeof(tmp), v);
        put(tmp);
    }

    size_t pos() const { return pos_; }
    bool ok() const { return ok_; }
    void terminate() {
        if (cap_ > 0) out_[pos_ < cap_ ? pos_ : cap_ - 1] = '\0';
    }

private:
    char* out_;
    size_t cap_;
    size_t pos_ = 0;
    bool ok_ = true;
};

}  // namespace

size_t formatRecord(const Record& r, char* out, size_t cap) {
    if (cap == 0) return 0;
    LineBuilder b(out, cap);
    b.put('$');
    b.unsignedNum(r.seq);
    b.put(',');
    b.unsignedNum(r.ms);
    b.put(',');
    if (r.tempCentiC == kInvalidReading) b.put("NaN");  // sensor unplugged
    else b.fixed(r.tempCentiC, 2);
    b.put(',');
    b.fixed(r.lightPermille, 1);  // per-mille with one decimal = percent
    b.put(',');
    b.fixed(r.supplyMv, 0);

    // Checksum covers the payload between '$' and '*'.
    size_t payloadEnd = b.pos();
    uint8_t crc = crc8(reinterpret_cast<const uint8_t*>(out + 1), payloadEnd - 1);
    char hex[3] = {0, 0, 0};
    hexByte(crc, hex);
    b.put('*');
    b.put(hex);
    b.put("\r\n");
    b.terminate();
    if (!b.ok()) {
        out[0] = '\0';
        return 0;
    }
    return b.pos();
}

const char* recordHeader() { return "# seq,ms,temp_c,light_pct,analog_mv"; }

}  // namespace sl
