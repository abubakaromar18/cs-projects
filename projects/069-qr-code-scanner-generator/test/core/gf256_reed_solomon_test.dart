import 'package:flutter_test/flutter_test.dart';
import 'package:qr_studio/qr_core.dart';

void main() {
  group('GF256', () {
    test('exp/log tables are inverse bijections', () {
      final seen = <int>{};
      for (var k = 0; k < 255; k++) {
        final v = GF256.pow2(k);
        expect(GF256.log2(v), equals(k));
        seen.add(v);
      }
      expect(seen, hasLength(255)); // 2 generates every non-zero element
      expect(seen.contains(0), isFalse);
    });

    test('multiplication: identities and reduction by 0x11D', () {
      expect(GF256.mul(0, 77), equals(0));
      expect(GF256.mul(1, 77), equals(77));
      expect(GF256.mul(0x80, 0x02), equals(0x1D)); // x^8 == x^4+x^3+x^2+1
      expect(GF256.mul(0x53, 0xCA), equals(GF256.mul(0xCA, 0x53)));
    });

    test('every non-zero element has an inverse', () {
      for (var a = 1; a < 256; a++) {
        expect(GF256.mul(a, GF256.inverse(a)), equals(1));
      }
      expect(() => GF256.inverse(0), throwsArgumentError);
      expect(() => GF256.log2(0), throwsArgumentError);
    });

    test('multiplication distributes over addition (XOR)', () {
      for (final (a, b, c) in [(3, 7, 200), (0x8E, 0x45, 0x11), (255, 254, 1)]) {
        expect(GF256.mul(a, b ^ c), equals(GF256.mul(a, b) ^ GF256.mul(a, c)));
      }
    });
  });

  group('ReedSolomon', () {
    test('generator of degree 1 is (x - 1)', () {
      expect(ReedSolomon.generator(1), equals([1]));
    });

    test('generator degree 7 matches the ISO 18004 table (log form)', () {
      // Annex A lists g(x) for 7 ECC codewords as exponents of alpha:
      // x^7 + a^87 x^6 + a^229 x^5 + a^146 x^4 + a^149 x^3 + a^238 x^2 + a^102 x + a^21
      final g = ReedSolomon.generator(7);
      expect(g.map(GF256.log2).toList(), equals([87, 229, 146, 149, 238, 102, 21]));
    });

    test('known vector: "HELLO WORLD" 1-M data codewords', () {
      // Classic worked example (Thonky QR tutorial).
      const data = [32, 91, 11, 120, 209, 114, 220, 77, 67, 64, 236, 17, 236, 17, 236, 17];
      expect(ReedSolomon.encode(data, 10), equals([196, 35, 39, 119, 235, 215, 231, 226, 93, 23]));
    });

    test('codeword has zero syndromes, corruption makes them non-zero', () {
      final data = List<int>.generate(30, (i) => (i * 37 + 11) & 0xFF);
      final ecc = ReedSolomon.encode(data, 16);
      final codeword = [...data, ...ecc];
      expect(ReedSolomon.syndromes(codeword, 16).every((s) => s == 0), isTrue);
      codeword[5] ^= 0x40;
      expect(ReedSolomon.syndromes(codeword, 16).any((s) => s != 0), isTrue);
    });

    test('rejects out-of-range degree', () {
      expect(() => ReedSolomon.generator(0), throwsRangeError);
      expect(() => ReedSolomon.generator(256), throwsRangeError);
    });
  });

  group('BitBuffer', () {
    test('appends MSB first and packs to bytes', () {
      final bb = BitBuffer()
        ..appendBits(0x4, 4)
        ..appendBits(0x5, 4)
        ..appendBits(0xA5, 8);
      expect(bb.toString(), equals('0100010110100101'));
      expect(bb.toBytes(), equals([0x45, 0xA5]));
    });

    test('rejects values that do not fit', () {
      expect(() => BitBuffer().appendBits(8, 3), throwsArgumentError);
      expect(() => (BitBuffer()..appendBits(1, 3)).toBytes(), throwsStateError);
    });
  });
}
