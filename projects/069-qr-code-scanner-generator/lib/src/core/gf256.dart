/// Arithmetic in the finite field GF(2^8), as used by QR codes.
///
/// Elements are bytes (0..255) interpreted as polynomials over GF(2) with
/// degree < 8. Addition is XOR. Multiplication is polynomial multiplication
/// reduced modulo the primitive polynomial
///   x^8 + x^4 + x^3 + x^2 + 1   (0x11D).
///
/// Because 0x02 ("x") is a generator of the multiplicative group, every
/// non-zero element equals 2^k for exactly one k in 0..254. We precompute
/// `exp[k] = 2^k` and its inverse `log`, which turns multiplication into an
/// addition of exponents.
library;

const int _primitive = 0x11D;

final List<int> _exp = _buildExp();
final List<int> _log = _buildLog();

List<int> _buildExp() {
  // 510 entries so exp[a + b] never needs a modulo (a, b <= 254).
  final table = List<int>.filled(510, 0);
  var x = 1;
  for (var i = 0; i < 255; i++) {
    table[i] = x;
    x <<= 1;
    if (x & 0x100 != 0) x ^= _primitive;
  }
  for (var i = 255; i < 510; i++) {
    table[i] = table[i - 255];
  }
  return table;
}

List<int> _buildLog() {
  final table = List<int>.filled(256, 0);
  for (var i = 0; i < 255; i++) {
    table[_exp[i]] = i;
  }
  return table;
}

/// Field operations on bytes.
abstract final class GF256 {
  /// Addition and subtraction are the same operation: XOR.
  static int add(int a, int b) => a ^ b;

  /// Multiplies two field elements.
  static int mul(int a, int b) {
    if (a == 0 || b == 0) return 0;
    return _exp[_log[a] + _log[b]];
  }

  /// Returns 2^k (k may be any non-negative integer).
  static int pow2(int k) => _exp[k % 255];

  /// Discrete logarithm base 2. Throws for 0, which has no logarithm.
  static int log2(int a) {
    if (a == 0) throw ArgumentError.value(a, 'a', 'log(0) is undefined');
    return _log[a];
  }

  /// Multiplicative inverse. Throws for 0.
  static int inverse(int a) {
    if (a == 0) throw ArgumentError.value(a, 'a', '0 has no inverse');
    return _exp[255 - _log[a]];
  }
}
