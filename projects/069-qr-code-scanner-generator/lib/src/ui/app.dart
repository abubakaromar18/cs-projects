import 'package:flutter/material.dart';

import 'app_state.dart';
import 'generate_page.dart';
import 'history_page.dart';
import 'scan_page.dart';

class QrStudioApp extends StatefulWidget {
  const QrStudioApp({super.key, this.state, this.scannerBuilder = defaultScannerBuilder});

  /// Injected in tests; a fresh [AppState] otherwise.
  final AppState? state;
  final ScannerBuilder scannerBuilder;

  @override
  State<QrStudioApp> createState() => _QrStudioAppState();
}

class _QrStudioAppState extends State<QrStudioApp> {
  late final AppState _state = widget.state ?? AppState();
  int _tab = 0;

  @override
  Widget build(BuildContext context) {
    const seed = Color(0xFF3949AB);
    return MaterialApp(
      title: 'QR Studio',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(colorSchemeSeed: seed, useMaterial3: true),
      darkTheme: ThemeData(colorSchemeSeed: seed, brightness: Brightness.dark, useMaterial3: true),
      home: Scaffold(
        appBar: AppBar(title: const Text('QR Studio')),
        // IndexedStack keeps the generator's form state when switching tabs,
        // but the scanner is only built while its tab is visible so the
        // camera is released when you leave it.
        body: IndexedStack(
          index: _tab,
          children: [
            GeneratePage(state: _state),
            _tab == 1
                ? ScanPage(state: _state, scannerBuilder: widget.scannerBuilder)
                : const SizedBox.shrink(),
            HistoryPage(state: _state),
          ],
        ),
        bottomNavigationBar: NavigationBar(
          selectedIndex: _tab,
          onDestinationSelected: (i) => setState(() => _tab = i),
          destinations: const [
            NavigationDestination(icon: Icon(Icons.qr_code_2), label: 'Generate'),
            NavigationDestination(icon: Icon(Icons.qr_code_scanner), label: 'Scan'),
            NavigationDestination(icon: Icon(Icons.history), label: 'History'),
          ],
        ),
      ),
    );
  }
}
