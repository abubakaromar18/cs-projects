import 'payload.dart';

enum HistorySource { scanned, generated }

class HistoryEntry {
  const HistoryEntry({required this.raw, required this.source, required this.at});

  final String raw;
  final HistorySource source;
  final DateTime at;

  QrPayload get payload => QrPayload.parse(raw);

  Map<String, Object> toJson() => {'raw': raw, 'source': source.name, 'at': at.toIso8601String()};

  factory HistoryEntry.fromJson(Map<String, Object?> json) => HistoryEntry(
    raw: json['raw']! as String,
    source: HistorySource.values.byName(json['source']! as String),
    at: DateTime.parse(json['at']! as String),
  );
}

/// Most-recent-first list of scanned/generated codes, bounded in size.
///
/// Re-adding a value that is already present moves it to the top instead of
/// creating a duplicate — the camera reports the same code many times per
/// second while it stays in view, so this also acts as debouncing.
class QrHistory {
  QrHistory({this.capacity = 100, Iterable<HistoryEntry> entries = const []}) {
    if (capacity < 1) throw ArgumentError.value(capacity, 'capacity', 'must be >= 1');
    for (final e in entries.toList().reversed) {
      add(e.raw, e.source, at: e.at);
    }
  }

  final int capacity;
  final List<HistoryEntry> _entries = [];

  List<HistoryEntry> get entries => List.unmodifiable(_entries);
  int get length => _entries.length;
  bool get isEmpty => _entries.isEmpty;

  /// Returns true if this was a new value (not just a move-to-top).
  bool add(String raw, HistorySource source, {DateTime? at}) {
    final idx = _entries.indexWhere((e) => e.raw == raw && e.source == source);
    final isNew = idx < 0;
    if (!isNew) _entries.removeAt(idx);
    _entries.insert(0, HistoryEntry(raw: raw, source: source, at: at ?? DateTime.now()));
    if (_entries.length > capacity) _entries.removeRange(capacity, _entries.length);
    return isNew;
  }

  void removeAt(int index) => _entries.removeAt(index);
  void clear() => _entries.clear();

  List<HistoryEntry> where(HistorySource source) =>
      _entries.where((e) => e.source == source).toList();

  /// Case-insensitive search over the raw content and the parsed summary.
  List<HistoryEntry> search(String query) {
    final q = query.trim().toLowerCase();
    if (q.isEmpty) return entries;
    return _entries
        .where(
          (e) => e.raw.toLowerCase().contains(q) || e.payload.summary.toLowerCase().contains(q),
        )
        .toList();
  }

  List<Map<String, Object>> toJson() => [for (final e in _entries) e.toJson()];

  factory QrHistory.fromJson(List<Object?> json, {int capacity = 100}) => QrHistory(
    capacity: capacity,
    entries: json.map((e) => HistoryEntry.fromJson((e! as Map).cast<String, Object?>())),
  );
}
