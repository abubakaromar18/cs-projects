import 'gf256.dart';

/// Reed–Solomon error-correction encoding over GF(256).
///
/// A QR block of `k` data bytes gets `n` extra ECC bytes. Treat the data as
/// the coefficients of a polynomial D(x) (first byte = highest degree). The
/// ECC bytes are the remainder of D(x)·x^n divided by the generator
///
///   G(x) = (x - 2^0)(x - 2^1)…(x - 2^(n-1)).
///
/// The full codeword D(x)·x^n + R(x) is then divisible by G(x), i.e. it is
/// zero at every root 2^i. A decoder evaluates those "syndromes" to locate
/// and fix up to n/2 corrupted bytes.
abstract final class ReedSolomon {
  /// Coefficients of G(x) for [degree] ECC bytes, highest power first and
  /// with the leading 1 omitted (it is always 1). Length == [degree].
  static List<int> generator(int degree) {
    if (degree < 1 || degree > 255) {
      throw RangeError.range(degree, 1, 255, 'degree');
    }
    // Start with the constant polynomial 1, stored as [0, 0, …, 1].
    final result = List<int>.filled(degree, 0);
    result[degree - 1] = 1;
    var root = 1;
    for (var i = 0; i < degree; i++) {
      // Multiply the current product by (x - root). In GF(2^8), -root == root.
      for (var j = 0; j < degree; j++) {
        result[j] = GF256.mul(result[j], root);
        if (j + 1 < degree) result[j] ^= result[j + 1];
      }
      root = GF256.mul(root, 0x02);
    }
    return result;
  }

  /// Computes the ECC bytes for [data] using a precomputed [generator].
  ///
  /// This is polynomial long division done like an LFSR: shift in one data
  /// byte at a time and subtract (XOR) a multiple of the generator.
  static List<int> remainder(List<int> data, List<int> generator) {
    final result = List<int>.filled(generator.length, 0);
    for (final b in data) {
      final factor = b ^ result[0];
      // Shift left by one coefficient.
      for (var i = 0; i < result.length - 1; i++) {
        result[i] = result[i + 1];
      }
      result[result.length - 1] = 0;
      for (var i = 0; i < result.length; i++) {
        result[i] ^= GF256.mul(generator[i], factor);
      }
    }
    return result;
  }

  /// Convenience: ECC bytes for [data] with [eccLength] check symbols.
  static List<int> encode(List<int> data, int eccLength) => remainder(data, generator(eccLength));

  /// Evaluates the syndromes S_i = C(2^i) of a full codeword
  /// (data followed by ECC). All zeros means "no detectable error".
  static List<int> syndromes(List<int> codeword, int eccLength) {
    return List<int>.generate(eccLength, (i) {
      final x = GF256.pow2(i);
      var acc = 0;
      for (final c in codeword) {
        acc = GF256.mul(acc, x) ^ c; // Horner's rule
      }
      return acc;
    });
  }
}
