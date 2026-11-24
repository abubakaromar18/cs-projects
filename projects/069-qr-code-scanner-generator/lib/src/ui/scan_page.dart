import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';

import '../../qr_core.dart';
import 'app_state.dart';
import 'payload_details.dart';

/// Builds the camera view. [onCode] is called with each decoded string.
/// Injectable so widget tests can replace the camera with a fake.
typedef ScannerBuilder = Widget Function(BuildContext context, ValueChanged<String> onCode);

Widget defaultScannerBuilder(BuildContext context, ValueChanged<String> onCode) =>
    CameraScanner(onCode: onCode);

class ScanPage extends StatefulWidget {
  const ScanPage({super.key, required this.state, this.scannerBuilder = defaultScannerBuilder});

  final AppState state;
  final ScannerBuilder scannerBuilder;

  @override
  State<ScanPage> createState() => _ScanPageState();
}

class _ScanPageState extends State<ScanPage> {
  /// While a result sheet is open, further detections are ignored — the
  /// camera keeps streaming frames of the same code many times per second.
  bool _showingResult = false;

  Future<void> _onCode(String raw) async {
    if (_showingResult || raw.isEmpty) return;
    _showingResult = true;
    widget.state.record(raw, HistorySource.scanned);
    await showPayloadSheet(context, raw);
    if (mounted) _showingResult = false;
  }

  @override
  Widget build(BuildContext context) {
    return Stack(
      fit: StackFit.expand,
      children: [
        widget.scannerBuilder(context, _onCode),
        const IgnorePointer(child: _Viewfinder()),
        Positioned(
          left: 0,
          right: 0,
          bottom: 24,
          child: Center(
            child: DecoratedBox(
              decoration: BoxDecoration(
                color: Colors.black54,
                borderRadius: BorderRadius.circular(20),
              ),
              child: const Padding(
                padding: EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                child: Text('Point the camera at a QR code', style: TextStyle(color: Colors.white)),
              ),
            ),
          ),
        ),
      ],
    );
  }
}

/// Dimmed overlay with a clear square in the middle.
class _Viewfinder extends StatelessWidget {
  const _Viewfinder();

  @override
  Widget build(BuildContext context) => CustomPaint(painter: _ViewfinderPainter());
}

class _ViewfinderPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final side = size.shortestSide * 0.65;
    final hole = RRect.fromRectAndRadius(
      Rect.fromCenter(center: size.center(Offset.zero), width: side, height: side),
      const Radius.circular(16),
    );
    final dim = Path()
      ..fillType = PathFillType.evenOdd
      ..addRect(Offset.zero & size)
      ..addRRect(hole);
    canvas.drawPath(dim, Paint()..color = Colors.black45);
    canvas.drawRRect(
      hole,
      Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 3
        ..color = Colors.white,
    );
  }

  @override
  bool shouldRepaint(_ViewfinderPainter oldDelegate) => false;
}

/// The real camera, via `mobile_scanner` (ML Kit / Apple Vision). Detection
/// is limited to QR codes, which makes it faster and avoids false hits.
class CameraScanner extends StatefulWidget {
  const CameraScanner({super.key, required this.onCode});

  final ValueChanged<String> onCode;

  @override
  State<CameraScanner> createState() => _CameraScannerState();
}

class _CameraScannerState extends State<CameraScanner> {
  final MobileScannerController _controller = MobileScannerController(
    formats: const [BarcodeFormat.qrCode],
    detectionSpeed: DetectionSpeed.normal,
  );

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _onDetect(BarcodeCapture capture) {
    for (final barcode in capture.barcodes) {
      final raw = barcode.rawValue;
      if (raw != null && raw.isNotEmpty) {
        widget.onCode(raw);
        return;
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Stack(
      fit: StackFit.expand,
      children: [
        MobileScanner(controller: _controller, onDetect: _onDetect),
        Positioned(
          top: 16,
          right: 16,
          child: Column(
            children: [
              IconButton.filledTonal(
                tooltip: 'Torch',
                icon: const Icon(Icons.flashlight_on_outlined),
                onPressed: () => _controller.toggleTorch(),
              ),
              const SizedBox(height: 8),
              IconButton.filledTonal(
                tooltip: 'Switch camera',
                icon: const Icon(Icons.cameraswitch_outlined),
                onPressed: () => _controller.switchCamera(),
              ),
            ],
          ),
        ),
      ],
    );
  }
}
