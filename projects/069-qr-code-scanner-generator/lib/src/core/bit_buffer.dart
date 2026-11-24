/// An append-only sequence of bits, used to assemble the QR data stream.
class BitBuffer {
  final List<bool> _bits = [];

  int get length => _bits.length;

  bool operator [](int i) => _bits[i];

  /// Appends the low [count] bits of [value], most significant first.
  void appendBits(int value, int count) {
    if (count < 0 || count > 31) throw RangeError.range(count, 0, 31, 'count');
    if (value < 0 || value >> count != 0) {
      throw ArgumentError.value(value, 'value', 'does not fit in $count bits');
    }
    for (var i = count - 1; i >= 0; i--) {
      _bits.add((value >> i) & 1 == 1);
    }
  }

  void appendAll(BitBuffer other) => _bits.addAll(other._bits);

  /// Packs the bits into bytes, big-endian within each byte. The length
  /// must be a multiple of 8.
  List<int> toBytes() {
    if (length % 8 != 0) throw StateError('length $length is not a multiple of 8');
    final out = List<int>.filled(length ~/ 8, 0);
    for (var i = 0; i < length; i++) {
      if (_bits[i]) out[i >> 3] |= 0x80 >> (i & 7);
    }
    return out;
  }

  @override
  String toString() => _bits.map((b) => b ? '1' : '0').join();
}
