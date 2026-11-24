import 'dart:convert';

import 'bit_buffer.dart';

/// QR data encoding modes supported by this encoder.
///
/// Denser modes pack more characters per bit, so the encoder picks the
/// densest mode that can represent the whole input:
///   numeric       3 digits  -> 10 bits  (3.33 bits/char)
///   alphanumeric  2 chars   -> 11 bits  (5.5 bits/char)
///   byte          1 byte    ->  8 bits  (UTF-8)
enum QrMode {
  numeric(0x1, [10, 12, 14]),
  alphanumeric(0x2, [9, 11, 13]),
  byte(0x4, [8, 16, 16]);

  const QrMode(this.indicator, this._countBits);

  /// The 4-bit mode indicator written before the segment.
  final int indicator;
  final List<int> _countBits;

  /// Width of the character-count field, which grows with the version.
  int charCountBits(int version) {
    if (version <= 9) return _countBits[0];
    if (version <= 26) return _countBits[1];
    return _countBits[2];
  }
}

/// The 45-character alphanumeric set, in code-value order.
const String alphanumericCharset = r'0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ $%*+-./:';

final RegExp _numeric = RegExp(r'^[0-9]*$');

/// An encoded run of data in a single mode.
class QrSegment {
  QrSegment._(this.mode, this.charCount, this.data);

  final QrMode mode;

  /// Number of characters (bytes in byte mode) — written in the count field.
  final int charCount;

  /// The payload bits, excluding mode indicator and count.
  final BitBuffer data;

  /// Encodes [text] in the densest mode that covers all of it.
  factory QrSegment.auto(String text) {
    if (_numeric.hasMatch(text)) return QrSegment.numeric(text);
    if (isAlphanumeric(text)) return QrSegment.alphanumeric(text);
    return QrSegment.bytes(utf8.encode(text));
  }

  factory QrSegment.numeric(String digits) {
    if (!_numeric.hasMatch(digits)) {
      throw ArgumentError.value(digits, 'digits', 'must contain only 0-9');
    }
    final bb = BitBuffer();
    // Groups of 3 digits -> 10 bits; a trailing 2 -> 7 bits, 1 -> 4 bits.
    for (var i = 0; i < digits.length; i += 3) {
      final group = digits.substring(i, (i + 3).clamp(0, digits.length));
      bb.appendBits(int.parse(group), group.length * 3 + 1);
    }
    return QrSegment._(QrMode.numeric, digits.length, bb);
  }

  factory QrSegment.alphanumeric(String text) {
    if (!isAlphanumeric(text)) {
      throw ArgumentError.value(text, 'text', 'contains characters outside the alphanumeric set');
    }
    final bb = BitBuffer();
    var i = 0;
    // Pairs -> 45*a + b in 11 bits; a leftover char -> 6 bits.
    for (; i + 1 < text.length; i += 2) {
      final v =
          alphanumericCharset.indexOf(text[i]) * 45 + alphanumericCharset.indexOf(text[i + 1]);
      bb.appendBits(v, 11);
    }
    if (i < text.length) bb.appendBits(alphanumericCharset.indexOf(text[i]), 6);
    return QrSegment._(QrMode.alphanumeric, text.length, bb);
  }

  factory QrSegment.bytes(List<int> bytes) {
    final bb = BitBuffer();
    for (final b in bytes) {
      bb.appendBits(b & 0xFF, 8);
    }
    return QrSegment._(QrMode.byte, bytes.length, bb);
  }

  static bool isAlphanumeric(String text) {
    for (var i = 0; i < text.length; i++) {
      if (!alphanumericCharset.contains(text[i])) return false;
    }
    return true;
  }

  /// Total bits this segment occupies at [version] (header + data), or null
  /// if the character count overflows the count field.
  int? totalBits(int version) {
    final ccBits = mode.charCountBits(version);
    if (charCount >= 1 << ccBits) return null;
    return 4 + ccBits + data.length;
  }
}
