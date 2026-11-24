import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:qr_studio/qr_core.dart';
import 'package:qr_studio/src/ui/app.dart';
import 'package:qr_studio/src/ui/app_state.dart';
import 'package:qr_studio/src/ui/qr_view.dart';

/// Replaces the camera: exposes the callback so a test can "scan" a code.
class FakeScanner {
  ValueChanged<String>? onCode;

  Widget build(BuildContext context, ValueChanged<String> cb) {
    onCode = cb;
    return const ColoredBox(key: Key('fake-camera'), color: Colors.black);
  }
}

void main() {
  late AppState state;
  late FakeScanner scanner;

  Future<void> pumpApp(WidgetTester tester) async {
    tester.view.physicalSize = const Size(1080, 2200);
    tester.view.devicePixelRatio = 2.75;
    addTearDown(tester.view.reset);
    await tester.pumpWidget(QrStudioApp(state: state, scannerBuilder: scanner.build));
  }

  setUp(() {
    state = AppState();
    scanner = FakeScanner();
  });

  testWidgets('typing text renders a QR preview with version info', (tester) async {
    await pumpApp(tester);
    expect(find.byKey(const Key('qr-preview')), findsNothing);

    await tester.enterText(find.byKey(const ValueKey('field-text')), 'Hello Flutter');
    await tester.pump();

    expect(find.byKey(const Key('qr-preview')), findsOneWidget);
    final view = tester.widget<QrView>(find.byKey(const Key('qr-preview')));
    expect(view.code.version, 1);
    expect(find.textContaining('Version 1 · 21×21'), findsOneWidget);
  });

  testWidgets('Wi-Fi form produces a WIFI: payload and saves to history', (tester) async {
    await pumpApp(tester);
    await tester.tap(find.text('Wi-Fi'));
    await tester.pump();
    await tester.enterText(find.byKey(const ValueKey('field-ssid')), 'Home');
    await tester.enterText(find.byKey(const ValueKey('field-wifiPass')), 'secret;1');
    await tester.pump();

    await tester.tap(find.byKey(const Key('save-button')));
    await tester.pump();

    final saved = state.history.entries.single;
    expect(saved.source, HistorySource.generated);
    expect(saved.raw, r'WIFI:T:WPA;S:Home;P:secret\;1;;');
  });

  testWidgets('changing error correction re-encodes', (tester) async {
    await pumpApp(tester);
    await tester.enterText(find.byKey(const ValueKey('field-text')), 'x' * 30);
    await tester.pump();
    final before = tester.widget<QrView>(find.byKey(const Key('qr-preview'))).code;

    await tester.tap(find.text('H'));
    await tester.pump();
    final after = tester.widget<QrView>(find.byKey(const Key('qr-preview'))).code;
    expect(after.errorCorrection, EcLevel.high);
    expect(after.version, greaterThan(before.version));
  });

  testWidgets('oversized input shows an error instead of crashing', (tester) async {
    await pumpApp(tester);
    await tester.tap(find.text('H'));
    await tester.enterText(find.byKey(const ValueKey('field-text')), 'z' * 1300);
    await tester.pump();
    expect(find.byKey(const Key('qr-error')), findsOneWidget);
  });

  testWidgets('scanning shows parsed details and records history once', (tester) async {
    await pumpApp(tester);
    await tester.tap(find.text('Scan'));
    await tester.pump();
    expect(find.byKey(const Key('fake-camera')), findsOneWidget);

    scanner.onCode!('WIFI:T:WPA;S:CoffeeShop;P:latte;;');
    scanner.onCode!('WIFI:T:WPA;S:CoffeeShop;P:latte;;'); // ignored while sheet is open
    await tester.pumpAndSettle();

    expect(find.text('Wi-Fi'), findsWidgets);
    expect(find.text('CoffeeShop'), findsOneWidget);
    expect(find.text('latte'), findsOneWidget);
    expect(state.history.length, 1);
  });

  testWidgets('history lists entries and filters by search', (tester) async {
    state
      ..record('https://dart.dev', HistorySource.scanned)
      ..record('tel:+15550100', HistorySource.generated);
    await pumpApp(tester);
    await tester.tap(find.text('History'));
    await tester.pumpAndSettle();

    expect(find.text('https://dart.dev'), findsOneWidget);
    expect(find.text('+15550100'), findsOneWidget);

    await tester.enterText(find.byKey(const Key('history-search')), 'dart');
    await tester.pump();
    expect(find.text('+15550100'), findsNothing);
    expect(find.text('https://dart.dev'), findsOneWidget);
  });

  testWidgets('tapping a history entry opens its details with the code', (tester) async {
    state.record('geo:41.8781,-87.6298', HistorySource.scanned);
    await pumpApp(tester);
    await tester.tap(find.text('History'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('41.8781, -87.6298'));
    await tester.pumpAndSettle();

    expect(find.text('Latitude'), findsOneWidget);
    expect(find.byType(QrView), findsOneWidget);
  });
}
