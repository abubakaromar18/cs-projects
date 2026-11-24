import 'bit_buffer.dart';
import 'reed_solomon.dart';
import 'segment.dart';
import 'tables.dart';

/// Thrown when the input does not fit in any allowed version.
class DataTooLongException implements Exception {
  DataTooLongException(this.message);
  final String message;
  @override
  String toString() => 'DataTooLongException: $message';
}

/// An immutable QR Code (Model 2) symbol: a square grid of dark/light modules.
///
/// Pipeline implemented by [QrCode.encodeText]:
///  1. choose a mode and build the bit stream (mode, count, data, terminator,
///     padding) — see [QrSegment];
///  2. pick the smallest version that fits, optionally boosting ECC level;
///  3. split codewords into blocks, add Reed–Solomon ECC, interleave;
///  4. draw function patterns, place codewords in the zig-zag order;
///  5. apply each of the 8 masks, score with the penalty rules, keep the best;
///  6. write BCH-protected format (and version) information.
class QrCode {
  QrCode._(this.version, this.errorCorrection, this.mask, this._modules);

  final int version;
  final EcLevel errorCorrection;

  /// Mask pattern 0..7 actually applied.
  final int mask;

  final List<List<bool>> _modules;

  /// Side length in modules (without quiet zone).
  int get size => _modules.length;

  /// True if the module at column [x], row [y] is dark. Out of range = light,
  /// which makes rendering a quiet zone trivial.
  bool isDark(int x, int y) => x >= 0 && y >= 0 && x < size && y < size && _modules[y][x];

  /// Encodes [text], choosing the densest mode automatically.
  ///
  /// [mask] forces a mask pattern (0..7); by default the lowest-penalty one is
  /// chosen. With [boostEcl] the level is raised as long as the version does
  /// not grow, because that extra robustness is free.
  static QrCode encodeText(
    String text, {
    EcLevel ecl = EcLevel.medium,
    int minVersion = 1,
    int maxVersion = 40,
    int? mask,
    bool boostEcl = true,
  }) {
    return encodeSegment(
      QrSegment.auto(text),
      ecl: ecl,
      minVersion: minVersion,
      maxVersion: maxVersion,
      mask: mask,
      boostEcl: boostEcl,
    );
  }

  static QrCode encodeSegment(
    QrSegment seg, {
    EcLevel ecl = EcLevel.medium,
    int minVersion = 1,
    int maxVersion = 40,
    int? mask,
    bool boostEcl = true,
  }) {
    if (minVersion < 1 || maxVersion > 40 || minVersion > maxVersion) {
      throw ArgumentError('invalid version range $minVersion..$maxVersion');
    }
    if (mask != null && (mask < 0 || mask > 7)) throw RangeError.range(mask, 0, 7, 'mask');

    // 2. Smallest version whose capacity holds the segment.
    int? version;
    int? usedBits;
    for (var v = minVersion; v <= maxVersion; v++) {
      final bits = seg.totalBits(v);
      if (bits != null && bits <= numDataCodewords(v, ecl) * 8) {
        version = v;
        usedBits = bits;
        break;
      }
    }
    if (version == null || usedBits == null) {
      throw DataTooLongException(
        '${seg.charCount} ${seg.mode.name} chars exceed version $maxVersion at level ${ecl.letter}',
      );
    }
    if (boostEcl) {
      for (final higher in EcLevel.values) {
        if (_rank(higher) > _rank(ecl) && usedBits <= numDataCodewords(version, higher) * 8) {
          ecl = higher;
        }
      }
    }

    // 1. Assemble the data bit stream.
    final capacityBits = numDataCodewords(version, ecl) * 8;
    final bb = BitBuffer()
      ..appendBits(seg.mode.indicator, 4)
      ..appendBits(seg.charCount, seg.mode.charCountBits(version))
      ..appendAll(seg.data);
    // Terminator: up to four 0 bits, then pad to a byte boundary.
    bb.appendBits(0, (capacityBits - bb.length).clamp(0, 4));
    bb.appendBits(0, (8 - bb.length % 8) % 8);
    // Fill remaining capacity with the alternating pad bytes 0xEC, 0x11.
    for (var pad = 0xEC; bb.length < capacityBits; pad ^= 0xEC ^ 0x11) {
      bb.appendBits(pad, 8);
    }

    // 3. ECC + interleaving.
    final codewords = addEccAndInterleave(bb.toBytes(), version, ecl);

    // 4–6. Build the matrix.
    final builder = _MatrixBuilder(version);
    builder.drawFunctionPatterns(ecl);
    builder.drawCodewords(codewords);

    var chosen = mask;
    if (chosen == null) {
      var best = 1 << 62;
      for (var m = 0; m < 8; m++) {
        builder.applyMask(m);
        builder.drawFormatBits(ecl, m);
        final p = penaltyScore(builder.modules);
        if (p < best) {
          best = p;
          chosen = m;
        }
        builder.applyMask(m); // XOR again undoes it
      }
    }
    builder.applyMask(chosen!);
    builder.drawFormatBits(ecl, chosen);
    return QrCode._(version, ecl, chosen, builder.modules);
  }

  static int _rank(EcLevel e) => EcLevel.values.indexOf(e);

  /// Splits [data] into the version's blocks, appends RS ECC to each, and
  /// interleaves them column-wise so a burst of damage is spread across
  /// blocks instead of wiping out one.
  static List<int> addEccAndInterleave(List<int> data, int version, EcLevel ecl) {
    if (data.length != numDataCodewords(version, ecl)) {
      throw ArgumentError('expected ${numDataCodewords(version, ecl)} data codewords');
    }
    final numBlocks = numErrorCorrectionBlocks[ecl.index][version];
    final blockEccLen = eccCodewordsPerBlock[ecl.index][version];
    final rawCodewords = numRawDataModules(version) ~/ 8;
    // Some blocks ("short") hold one fewer data byte than the others.
    final numShortBlocks = numBlocks - rawCodewords % numBlocks;
    final shortBlockLen = rawCodewords ~/ numBlocks;

    final gen = ReedSolomon.generator(blockEccLen);
    final blocks = <List<int>>[];
    for (var i = 0, k = 0; i < numBlocks; i++) {
      final datLen = shortBlockLen - blockEccLen + (i < numShortBlocks ? 0 : 1);
      final dat = data.sublist(k, k + datLen);
      k += datLen;
      final ecc = ReedSolomon.remainder(dat, gen);
      // Placeholder byte keeps all blocks the same length for interleaving.
      if (i < numShortBlocks) dat.add(0);
      blocks.add([...dat, ...ecc]);
    }

    final result = <int>[];
    for (var i = 0; i < blocks[0].length; i++) {
      for (var j = 0; j < blocks.length; j++) {
        // Skip the placeholder in short blocks.
        if (i != shortBlockLen - blockEccLen || j >= numShortBlocks) result.add(blocks[j][i]);
      }
    }
    assert(result.length == rawCodewords);
    return result;
  }

  /// Penalty score from ISO/IEC 18004 §7.8.3. Lower is easier to scan.
  static int penaltyScore(List<List<bool>> m) {
    final n = m.length;
    var result = 0;

    // Rule 1: runs of >= 5 same-colored modules in a row/column.
    for (var y = 0; y < n; y++) {
      result += _runPenalty((i) => m[y][i], n);
    }
    for (var x = 0; x < n; x++) {
      result += _runPenalty((i) => m[i][x], n);
    }

    // Rule 2: each 2x2 block of one color.
    for (var y = 0; y < n - 1; y++) {
      for (var x = 0; x < n - 1; x++) {
        final c = m[y][x];
        if (c == m[y][x + 1] && c == m[y + 1][x] && c == m[y + 1][x + 1]) result += 3;
      }
    }

    // Rule 3: finder-like 1:1:3:1:1 pattern with 4 light modules on a side.
    // Modules outside the symbol count as light (the quiet zone).
    bool at(int x, int y) => x >= 0 && y >= 0 && x < n && y < n && m[y][x];
    const core = [true, false, true, true, true, false, true];
    for (var a = 0; a < n; a++) {
      for (var b = -4; b < n; b++) {
        for (final horizontal in [true, false]) {
          bool get(int k) => horizontal ? at(b + k, a) : at(a, b + k);
          var matches = true;
          for (var k = 0; k < 7 && matches; k++) {
            matches = get(k) == core[k];
          }
          if (!matches) continue;
          final lightBefore = !get(-1) && !get(-2) && !get(-3) && !get(-4);
          final lightAfter = !get(7) && !get(8) && !get(9) && !get(10);
          if (lightBefore) result += 40;
          if (lightAfter) result += 40;
        }
      }
    }

    // Rule 4: balance of dark vs light. 10 points per 5% away from 50%.
    var dark = 0;
    for (final row in m) {
      for (final c in row) {
        if (c) dark++;
      }
    }
    final total = n * n;
    final k = ((dark * 20 - total * 10).abs() + total - 1) ~/ total - 1;
    result += k * 10;
    return result;
  }

  static int _runPenalty(bool Function(int) cell, int n) {
    var result = 0;
    var runLen = 1;
    for (var i = 1; i <= n; i++) {
      if (i < n && cell(i) == cell(i - 1)) {
        runLen++;
      } else {
        if (runLen >= 5) result += 3 + (runLen - 5);
        runLen = 1;
      }
    }
    return result;
  }

  /// Renders the symbol as text using two characters per module, with a
  /// quiet zone of [border] modules. Handy for terminals and tests.
  String toAscii({int border = 2, String dark = '██', String light = '  '}) {
    final sb = StringBuffer();
    for (var y = -border; y < size + border; y++) {
      for (var x = -border; x < size + border; x++) {
        sb.write(isDark(x, y) ? dark : light);
      }
      if (y < size + border - 1) sb.writeln();
    }
    return sb.toString();
  }

  /// Rows of '1'/'0' without border — a compact, comparable fingerprint.
  List<String> toBitRows() => [for (final row in _modules) row.map((c) => c ? '1' : '0').join()];
}

/// Mutable grid used while building a symbol.
class _MatrixBuilder {
  _MatrixBuilder(this.version)
    : size = sizeForVersion(version),
      modules = List.generate(
        sizeForVersion(version),
        (_) => List.filled(sizeForVersion(version), false),
      ),
      isFunction = List.generate(
        sizeForVersion(version),
        (_) => List.filled(sizeForVersion(version), false),
      );

  final int version;
  final int size;
  final List<List<bool>> modules;

  /// Marks modules that belong to function patterns (never masked or overwritten by data).
  final List<List<bool>> isFunction;

  void _setFunction(int x, int y, bool dark) {
    modules[y][x] = dark;
    isFunction[y][x] = true;
  }

  void drawFunctionPatterns(EcLevel ecl) {
    // Timing patterns: alternating modules along row 6 and column 6.
    for (var i = 0; i < size; i++) {
      _setFunction(6, i, i % 2 == 0);
      _setFunction(i, 6, i % 2 == 0);
    }
    // Three finder patterns (with their light separators).
    _drawFinder(3, 3);
    _drawFinder(size - 4, 3);
    _drawFinder(3, size - 4);

    // Alignment patterns everywhere on the grid except over the finders.
    final pos = alignmentPatternPositions(version);
    final last = pos.length - 1;
    for (var i = 0; i < pos.length; i++) {
      for (var j = 0; j < pos.length; j++) {
        final overlapsFinder = (i == 0 && j == 0) || (i == 0 && j == last) || (i == last && j == 0);
        if (!overlapsFinder) _drawAlignment(pos[i], pos[j]);
      }
    }

    // Reserve format area (real bits written after masking) and draw version info.
    drawFormatBits(ecl, 0);
    _drawVersion();
  }

  void _drawFinder(int cx, int cy) {
    for (var dy = -4; dy <= 4; dy++) {
      for (var dx = -4; dx <= 4; dx++) {
        final dist = dx.abs() > dy.abs() ? dx.abs() : dy.abs(); // Chebyshev distance
        final x = cx + dx, y = cy + dy;
        if (x >= 0 && x < size && y >= 0 && y < size) _setFunction(x, y, dist != 2 && dist != 4);
      }
    }
  }

  void _drawAlignment(int cx, int cy) {
    for (var dy = -2; dy <= 2; dy++) {
      for (var dx = -2; dx <= 2; dx++) {
        final dist = dx.abs() > dy.abs() ? dx.abs() : dy.abs();
        _setFunction(cx + dx, cy + dy, dist != 1);
      }
    }
  }

  /// 15-bit format info: 2 bits ECC level + 3 bits mask, protected by a
  /// (15,5) BCH code and XOR-ed with 0x5412 so it is never all zeros.
  /// Written twice for redundancy.
  void drawFormatBits(EcLevel ecl, int mask) {
    final bits = formatInfoBits(ecl, mask);
    bool bit(int i) => (bits >> i) & 1 == 1;

    // Copy 1: around the top-left finder.
    for (var i = 0; i <= 5; i++) {
      _setFunction(8, i, bit(i));
    }
    _setFunction(8, 7, bit(6));
    _setFunction(8, 8, bit(7));
    _setFunction(7, 8, bit(8));
    for (var i = 9; i < 15; i++) {
      _setFunction(14 - i, 8, bit(i));
    }
    // Copy 2: split between the top-right and bottom-left finders.
    for (var i = 0; i < 8; i++) {
      _setFunction(size - 1 - i, 8, bit(i));
    }
    for (var i = 8; i < 15; i++) {
      _setFunction(8, size - 15 + i, bit(i));
    }
    _setFunction(8, size - 8, true); // the "dark module", always dark
  }

  /// Versions >= 7 carry an 18-bit version number protected by a (18,6)
  /// Golay code, in two 6x3 blocks near the top-right and bottom-left.
  void _drawVersion() {
    if (version < 7) return;
    final bits = versionInfoBits(version);
    for (var i = 0; i < 18; i++) {
      final dark = (bits >> i) & 1 == 1;
      final a = size - 11 + i % 3;
      final b = i ~/ 3;
      _setFunction(a, b, dark);
      _setFunction(b, a, dark);
    }
  }

  /// Places codewords in the standard zig-zag: two-module-wide columns from
  /// right to left, alternately upward and downward, skipping column 6
  /// (vertical timing) and every function module.
  void drawCodewords(List<int> data) {
    var i = 0;
    for (var right = size - 1; right >= 1; right -= 2) {
      if (right == 6) right = 5;
      final upward = ((right + 1) & 2) == 0;
      for (var vert = 0; vert < size; vert++) {
        final y = upward ? size - 1 - vert : vert;
        for (var j = 0; j < 2; j++) {
          final x = right - j;
          if (!isFunction[y][x] && i < data.length * 8) {
            modules[y][x] = (data[i >> 3] >> (7 - (i & 7))) & 1 == 1;
            i++;
          }
          // Leftover "remainder bits" stay light (0) as the spec requires.
        }
      }
    }
    assert(i == data.length * 8);
  }

  /// XORs the data area with mask pattern [m]. Self-inverse.
  void applyMask(int m) {
    for (var y = 0; y < size; y++) {
      for (var x = 0; x < size; x++) {
        if (!isFunction[y][x] && maskCondition(m, x, y)) modules[y][x] = !modules[y][x];
      }
    }
  }
}

/// The 8 mask predicates; x is the column, y the row.
bool maskCondition(int mask, int x, int y) => switch (mask) {
  0 => (x + y) % 2 == 0,
  1 => y % 2 == 0,
  2 => x % 3 == 0,
  3 => (x + y) % 3 == 0,
  4 => (x ~/ 3 + y ~/ 2) % 2 == 0,
  5 => x * y % 2 + x * y % 3 == 0,
  6 => (x * y % 2 + x * y % 3) % 2 == 0,
  7 => ((x + y) % 2 + x * y % 3) % 2 == 0,
  _ => throw RangeError.range(mask, 0, 7, 'mask'),
};

/// BCH(15,5) format word for an ECC level and mask, already XOR-masked.
int formatInfoBits(EcLevel ecl, int mask) {
  final data = ecl.formatBits << 3 | mask;
  var rem = data;
  for (var i = 0; i < 10; i++) {
    rem = (rem << 1) ^ ((rem >> 9) * 0x537);
  }
  return (data << 10 | rem) ^ 0x5412;
}

/// Golay(18,6) version word.
int versionInfoBits(int version) {
  var rem = version;
  for (var i = 0; i < 12; i++) {
    rem = (rem << 1) ^ ((rem >> 11) * 0x1F25);
  }
  return version << 12 | rem;
}
