import 'package:flutter/material.dart';

import '../../qr_core.dart';

/// Draws a [QrCode] with a quiet zone. Always dark-on-light regardless of
/// theme: many scanners cannot read inverted codes.
class QrView extends StatelessWidget {
  const QrView({super.key, required this.code, this.size = 240, this.border = 4});

  final QrCode code;
  final double size;

  /// Quiet zone in modules; the spec asks for 4.
  final int border;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label:
          'QR code, version ${code.version}, '
          'error correction ${code.errorCorrection.letter}',
      image: true,
      child: CustomPaint(
        size: Size.square(size),
        painter: QrPainter(code, border: border),
      ),
    );
  }
}

class QrPainter extends CustomPainter {
  QrPainter(this.code, {this.border = 4, this.dark = Colors.black, this.light = Colors.white});

  final QrCode code;
  final int border;
  final Color dark;
  final Color light;

  @override
  void paint(Canvas canvas, Size size) {
    final modules = code.size + 2 * border;
    final cell = size.shortestSide / modules;
    canvas.drawRect(Offset.zero & size, Paint()..color = light);

    // One path for all dark modules: far fewer draw calls than a rect each.
    // Rows of adjacent dark modules are merged into single rectangles.
    final path = Path();
    for (var y = 0; y < code.size; y++) {
      var x = 0;
      while (x < code.size) {
        if (!code.isDark(x, y)) {
          x++;
          continue;
        }
        final start = x;
        while (x < code.size && code.isDark(x, y)) {
          x++;
        }
        path.addRect(
          Rect.fromLTWH((start + border) * cell, (y + border) * cell, (x - start) * cell, cell),
        );
      }
    }
    // Anti-aliasing off avoids hairline seams between neighbouring rows.
    canvas.drawPath(
      path,
      Paint()
        ..color = dark
        ..isAntiAlias = false,
    );
  }

  @override
  bool shouldRepaint(QrPainter old) =>
      !identical(old.code, code) || old.border != border || old.dark != dark || old.light != light;
}
