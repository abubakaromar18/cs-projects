import 'package:flutter/foundation.dart';

import '../../qr_core.dart';

/// App-wide state: the scan/generate history. Kept deliberately small —
/// pages own their own transient form state.
class AppState extends ChangeNotifier {
  AppState({QrHistory? history}) : history = history ?? QrHistory();

  final QrHistory history;

  /// Records a value; returns true if it was new.
  bool record(String raw, HistorySource source) {
    final isNew = history.add(raw, source);
    notifyListeners();
    return isNew;
  }

  void removeAt(int index) {
    history.removeAt(index);
    notifyListeners();
  }

  void clear() {
    history.clear();
    notifyListeners();
  }
}
