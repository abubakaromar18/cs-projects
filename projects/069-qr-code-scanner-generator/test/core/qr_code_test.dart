import 'package:flutter_test/flutter_test.dart';
import 'package:qr_studio/qr_core.dart';

/// 32-bit FNV-1a over the '0'/'1' rows joined by '\n' — a compact fingerprint
/// of a whole symbol.
int fnv1a(String s) {
  var h = 0x811c9dc5;
  for (final c in s.codeUnits) {
    h = ((h ^ c) * 0x01000193) & 0xFFFFFFFF;
  }
  return h;
}

int fingerprint(QrCode qr) => fnv1a(qr.toBitRows().join('\n'));

void main() {
  group('tables', () {
    test('sizes and raw module counts', () {
      expect(sizeForVersion(1), equals(21));
      expect(sizeForVersion(40), equals(177));
      expect(numRawDataModules(1), equals(208)); // 26 codewords
      expect(numRawDataModules(7), equals(1568)); // 196 codewords
      expect(numRawDataModules(40), equals(29648)); // 3706 codewords
    });

    test('known capacities (bytes) per ISO 18004 Table 7', () {
      expect(numDataCodewords(1, EcLevel.low), equals(19));
      expect(numDataCodewords(1, EcLevel.high), equals(9));
      expect(numDataCodewords(10, EcLevel.medium), equals(216));
      expect(numDataCodewords(40, EcLevel.low), equals(2956));
      expect(numDataCodewords(40, EcLevel.high), equals(1276));
    });

    test('alignment pattern centers', () {
      expect(alignmentPatternPositions(1), isEmpty);
      expect(alignmentPatternPositions(2), equals([6, 18]));
      expect(alignmentPatternPositions(7), equals([6, 22, 38]));
      expect(alignmentPatternPositions(32), equals([6, 34, 60, 86, 112, 138]));
      expect(alignmentPatternPositions(40), equals([6, 30, 58, 86, 114, 142, 170]));
    });

    test('format and version BCH words match the spec tables', () {
      // Level M (00), mask 0 -> 101010000010010 (ISO 18004 Annex C).
      expect(formatInfoBits(EcLevel.medium, 0), equals(0x5412));
      expect(formatInfoBits(EcLevel.low, 4), equals(int.parse('110011000101111', radix: 2)));
      expect(versionInfoBits(7), equals(0x07C94));
      expect(versionInfoBits(40), equals(0x28C69));
    });
  });

  group('segments', () {
    test('mode auto-detection', () {
      expect(QrSegment.auto('0123').mode, equals(QrMode.numeric));
      expect(QrSegment.auto('HELLO WORLD').mode, equals(QrMode.alphanumeric));
      expect(QrSegment.auto('hello').mode, equals(QrMode.byte));
      expect(QrSegment.auto('').mode, equals(QrMode.numeric));
    });

    test('numeric packs 3 digits in 10 bits, leftovers in 7 or 4', () {
      expect(
        QrSegment.numeric('01234567').data.toString(),
        equals('000000110001010110011000011'),
      ); // 012 345 67
      expect(QrSegment.numeric('8').data.length, equals(4));
    });

    test('alphanumeric packs pairs in 11 bits', () {
      // "HE" -> 17*45 + 14 = 779
      expect(QrSegment.alphanumeric('HE').data.toString(), equals('01100001011'));
      expect(QrSegment.alphanumeric('HEL').data.length, equals(17));
      expect(() => QrSegment.alphanumeric('hi'), throwsArgumentError);
    });

    test('byte mode uses UTF-8', () {
      final seg = QrSegment.auto('é✓');
      expect(seg.mode, equals(QrMode.byte));
      expect(seg.charCount, equals(5)); // 2 + 3 bytes
    });

    test('char count field widens with version', () {
      expect(QrMode.byte.charCountBits(9), equals(8));
      expect(QrMode.byte.charCountBits(10), equals(16));
      expect(QrMode.numeric.charCountBits(27), equals(14));
    });
  });

  group('encoder', () {
    test('HELLO WORLD at Q fits version 1 and is bit-exact', () {
      final qr = QrCode.encodeText('HELLO WORLD', ecl: EcLevel.quartile, mask: 0);
      expect(qr.version, equals(1));
      expect(qr.size, equals(21));
      expect(qr.toBitRows().first, equals('111111101100001111111'));
      expect(qr.toBitRows().last, equals('111111100001011100001'));
      expect(fingerprint(qr), equals(0xb46f4819));
    });

    // Golden fingerprints produced by the independent Python `qrcode` library
    // with the same mode, level and forced mask (boosting off).
    const golden = <(String, EcLevel, int, int, int)>[
      ('https://github.com/abubakaromar18/cs-projects', EcLevel.medium, 3, 4, 0x828c2374),
      ('3141592653589793238462643383279502884197', EcLevel.high, 5, 3, 0x8fbce634),
      ('WIFI:T:WPA;S:Home Net;P:correct horse;;', EcLevel.low, 6, 3, 0x8f761333),
      ('Ünïcödé ✓', EcLevel.quartile, 2, 2, 0xf57b4575),
    ];
    for (final (text, ecl, mask, version, fp) in golden) {
      test('golden: "${text.length > 24 ? '${text.substring(0, 24)}…' : text}" ${ecl.letter}', () {
        final qr = QrCode.encodeText(text, ecl: ecl, mask: mask, boostEcl: false);
        expect(qr.version, equals(version));
        expect(fingerprint(qr), equals(fp));
      });
    }

    test('golden: larger versions (12, 17, 34) incl. version info blocks', () {
      expect(
        fingerprint(QrCode.encodeText('QR' * 200, ecl: EcLevel.medium, mask: 7, boostEcl: false)),
        equals(0xcd04965e),
      );
      final num = QrCode.encodeText('0123456789' * 150, ecl: EcLevel.low, mask: 1, boostEcl: false);
      expect(num.version, equals(17));
      expect(fingerprint(num), equals(0xfc6f6aae));
      final big = QrCode.encodeText(
        'The quick brown fox jumps over the lazy dog. ' * 20,
        ecl: EcLevel.high,
        mask: 4,
        boostEcl: false,
      );
      expect(big.version, equals(34));
      expect(fingerprint(big), equals(0xbc407cba));
    });

    test('ECC boosting raises the level without growing the symbol', () {
      final qr = QrCode.encodeText('hi', ecl: EcLevel.low);
      expect(qr.version, equals(1));
      expect(qr.errorCorrection, equals(EcLevel.high));
      final noBoost = QrCode.encodeText('hi', ecl: EcLevel.low, boostEcl: false);
      expect(noBoost.errorCorrection, equals(EcLevel.low));
    });

    test('auto mask picks the minimum penalty', () {
      const text = 'mask selection';
      final auto = QrCode.encodeText(text);
      final scores = [
        for (var m = 0; m < 8; m++)
          QrCode.penaltyScore([
            for (final r in QrCode.encodeText(text, mask: m).toBitRows())
              [for (final c in r.split('')) c == '1'],
          ]),
      ];
      final best = scores.reduce((a, b) => a < b ? a : b);
      expect(scores[auto.mask], equals(best));
      expect(scores.indexOf(best), equals(auto.mask)); // ties -> lowest index
    });

    test('function patterns are in place', () {
      final qr = QrCode.encodeText('x' * 200); // version >= 7
      expect(qr.version, greaterThanOrEqualTo(7));
      final n = qr.size;
      // Finder corners dark, separators light.
      for (final (x, y) in [(0, 0), (n - 1, 0), (0, n - 1), (6, 6), (n - 7, 6), (6, n - 7)]) {
        expect(qr.isDark(x, y), isTrue, reason: 'finder corner ($x,$y)');
      }
      expect(qr.isDark(7, 7), isFalse);
      // Timing pattern alternates along row 6.
      for (var x = 8; x < n - 8; x++) {
        expect(qr.isDark(x, 6), equals(x.isEven));
      }
      expect(qr.isDark(8, n - 8), isTrue); // dark module
      expect(qr.isDark(-1, 0), isFalse); // quiet zone
    });

    test('capacity limits: largest fits, one more byte fails', () {
      final max = QrCode.encodeText('a' * 2953, ecl: EcLevel.low);
      expect(max.version, equals(40));
      expect(
        () => QrCode.encodeText('a' * 2954, ecl: EcLevel.low),
        throwsA(isA<DataTooLongException>()),
      );
      expect(QrCode.encodeText('7' * 7089, ecl: EcLevel.low).version, equals(40));
      expect(() => QrCode.encodeText('hello', maxVersion: 0), throwsArgumentError);
      expect(() => QrCode.encodeText('hello', mask: 8), throwsRangeError);
    });

    test('version range constraint is honoured', () {
      expect(QrCode.encodeText('A', minVersion: 5).version, equals(5));
      expect(
        () => QrCode.encodeText('a' * 100, maxVersion: 2),
        throwsA(isA<DataTooLongException>()),
      );
    });

    test('ascii rendering includes quiet zone', () {
      final art = QrCode.encodeText('A').toAscii(border: 1, dark: '#', light: '.');
      final lines = art.split('\n');
      expect(lines, hasLength(23));
      expect(lines.first, equals('.' * 23));
      expect(lines[1].substring(0, 8), equals('.#######'));
    });
  });
}
