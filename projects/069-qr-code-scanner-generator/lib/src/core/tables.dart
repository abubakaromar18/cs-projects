/// Capacity tables from ISO/IEC 18004 (QR Code Model 2), versions 1–40.
library;

/// Error-correction level. Higher levels survive more damage but hold less.
enum EcLevel {
  /// ~7% of codewords can be restored.
  low(1),

  /// ~15%.
  medium(0),

  /// ~25%.
  quartile(3),

  /// ~30%.
  high(2);

  const EcLevel(this.formatBits);

  /// The 2-bit value written into the format information.
  final int formatBits;

  String get letter => const ['L', 'M', 'Q', 'H'][index];
}

const int minVersion = 1;
const int maxVersion = 40;

// Index 0 is padding so tables can be indexed by version directly.

// dart format off
/// ECC codewords per block, by [EcLevel.index] then version.
const List<List<int>> eccCodewordsPerBlock = [
  // L
  [-1, 7, 10, 15, 20, 26, 18, 20, 24, 30, 18, 20, 24, 26, 30, 22, 24, 28, 30, 28, 28,
   28, 28, 30, 30, 26, 28, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30],
  // M
  [-1, 10, 16, 26, 18, 24, 16, 18, 22, 22, 26, 30, 22, 22, 24, 24, 28, 28, 26, 26, 26,
   26, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28, 28],
  // Q
  [-1, 13, 22, 18, 26, 18, 24, 18, 22, 20, 24, 28, 26, 24, 20, 30, 24, 28, 28, 26, 30,
   28, 30, 30, 30, 30, 28, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30],
  // H
  [-1, 17, 28, 22, 16, 22, 28, 26, 26, 24, 28, 24, 28, 22, 24, 24, 30, 28, 28, 26, 28,
   30, 24, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30, 30],
];

/// Number of error-correction blocks, by [EcLevel.index] then version.
const List<List<int>> numErrorCorrectionBlocks = [
  // L
  [-1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 4, 4, 4, 4, 4, 6, 6, 6, 6, 7, 8,
   8, 9, 9, 10, 12, 12, 12, 13, 14, 15, 16, 17, 18, 19, 19, 20, 21, 22, 24, 25],
  // M
  [-1, 1, 1, 1, 2, 2, 4, 4, 4, 5, 5, 5, 8, 9, 9, 10, 10, 11, 13, 14, 16,
   17, 17, 18, 20, 21, 23, 25, 26, 28, 29, 31, 33, 35, 37, 38, 40, 43, 45, 47, 49],
  // Q
  [-1, 1, 1, 2, 2, 4, 4, 6, 6, 8, 8, 8, 10, 12, 16, 12, 17, 16, 18, 21, 20,
   23, 23, 25, 27, 29, 34, 34, 35, 38, 40, 43, 45, 48, 51, 53, 56, 59, 62, 65, 68],
  // H
  [-1, 1, 1, 2, 4, 4, 4, 5, 6, 8, 8, 11, 11, 16, 16, 18, 16, 19, 21, 25, 25,
   25, 34, 30, 32, 35, 37, 40, 42, 45, 48, 51, 54, 57, 60, 63, 66, 70, 74, 77, 81],
];
// dart format on

/// Side length in modules: 21 for version 1, +4 per version.
int sizeForVersion(int version) => version * 4 + 17;

/// Modules available for data + ECC after all function patterns
/// (finders, timing, alignment, format/version info) are removed.
int numRawDataModules(int version) {
  _checkVersion(version);
  var result = (16 * version + 128) * version + 64;
  if (version >= 2) {
    final numAlign = version ~/ 7 + 2;
    result -= (25 * numAlign - 10) * numAlign - 55;
    if (version >= 7) result -= 36; // two 6x3 version-info blocks
  }
  return result;
}

/// Data codewords (bytes) a symbol can hold at the given level.
int numDataCodewords(int version, EcLevel ecl) =>
    numRawDataModules(version) ~/ 8 -
    eccCodewordsPerBlock[ecl.index][version] * numErrorCorrectionBlocks[ecl.index][version];

/// Center coordinates of alignment patterns (same list for rows and columns).
List<int> alignmentPatternPositions(int version) {
  _checkVersion(version);
  if (version == 1) return const [];
  final numAlign = version ~/ 7 + 2;
  final step = (version * 8 + numAlign * 3 + 5) ~/ (numAlign * 4 - 4) * 2;
  final result = <int>[];
  for (var i = 0, pos = sizeForVersion(version) - 7; i < numAlign - 1; i++, pos -= step) {
    result.insert(0, pos);
  }
  result.insert(0, 6);
  return result;
}

void _checkVersion(int version) {
  if (version < minVersion || version > maxVersion) {
    throw RangeError.range(version, minVersion, maxVersion, 'version');
  }
}
