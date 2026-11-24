// Command-line front end to the pure-Dart encoder (no Flutter needed):
//
//   dart run tool/qr_cli.dart "Hello, world"            # ASCII art
//   dart run tool/qr_cli.dart --ecl H --pbm out.pbm "…"  # image file
//   dart run tool/qr_cli.dart --bits "…"                 # 0/1 rows
import 'dart:io';

import 'package:qr_studio/qr_core.dart';

void main(List<String> args) {
  var ecl = EcLevel.medium;
  int? mask;
  String? pbmPath;
  var bits = false;
  var noBoost = false;
  final rest = <String>[];
  for (var i = 0; i < args.length; i++) {
    switch (args[i]) {
      case '--ecl':
        final letter = args[++i].toUpperCase();
        ecl = EcLevel.values.firstWhere((e) => e.letter == letter);
      case '--mask':
        mask = int.parse(args[++i]);
      case '--pbm':
        pbmPath = args[++i];
      case '--bits':
        bits = true;
      case '--no-boost':
        noBoost = true;
      default:
        rest.add(args[i]);
    }
  }
  if (rest.isEmpty) {
    stderr.writeln(
      'usage: qr_cli.dart [--ecl L|M|Q|H] [--mask 0-7] [--no-boost] '
      '[--bits] [--pbm file] <text>',
    );
    exit(64);
  }

  final qr = QrCode.encodeText(rest.join(' '), ecl: ecl, mask: mask, boostEcl: !noBoost);
  stderr.writeln(
    'version ${qr.version} (${qr.size}x${qr.size}), '
    'level ${qr.errorCorrection.letter}, mask ${qr.mask}',
  );

  if (bits) {
    stdout.writeln(qr.toBitRows().join('\n'));
  } else if (pbmPath != null) {
    File(pbmPath).writeAsStringSync(_pbm(qr, scale: 8, border: 4));
  } else {
    stdout.writeln(qr.toAscii());
  }
}

/// Plain-text PBM (P1) image: 1 = black.
String _pbm(QrCode qr, {required int scale, required int border}) {
  final dim = (qr.size + 2 * border) * scale;
  final sb = StringBuffer('P1\n$dim $dim\n');
  for (var py = 0; py < dim; py++) {
    final y = py ~/ scale - border;
    for (var px = 0; px < dim; px++) {
      sb.write(qr.isDark(px ~/ scale - border, y) ? '1 ' : '0 ');
    }
    sb.writeln();
  }
  return sb.toString();
}
