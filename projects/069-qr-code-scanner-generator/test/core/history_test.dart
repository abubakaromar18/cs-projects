import 'package:flutter_test/flutter_test.dart';
import 'package:qr_studio/qr_core.dart';

void main() {
  final t0 = DateTime.utc(2026, 11, 23, 12);
  late QrHistory h;

  setUp(() => h = QrHistory(capacity: 3));

  test('newest first', () {
    h.add('a', HistorySource.scanned, at: t0);
    h.add('b', HistorySource.scanned, at: t0);
    expect(h.entries.map((e) => e.raw).toList(), equals(['b', 'a']));
  });

  test('re-adding moves to top instead of duplicating (scan debounce)', () {
    expect(h.add('a', HistorySource.scanned), isTrue);
    h.add('b', HistorySource.scanned);
    expect(h.add('a', HistorySource.scanned), isFalse);
    expect(h.entries.map((e) => e.raw).toList(), equals(['a', 'b']));
  });

  test('same content from different sources is kept separately', () {
    h.add('a', HistorySource.scanned);
    h.add('a', HistorySource.generated);
    expect(h.length, equals(2));
    expect(h.where(HistorySource.generated), hasLength(1));
  });

  test('capacity evicts the oldest', () {
    for (final s in ['1', '2', '3', '4']) {
      h.add(s, HistorySource.scanned);
    }
    expect(h.entries.map((e) => e.raw).toList(), equals(['4', '3', '2']));
  });

  test('search matches raw text and parsed summary', () {
    h.add('WIFI:T:WPA;S:CoffeeShop;P:x;;', HistorySource.scanned);
    h.add('https://dart.dev', HistorySource.scanned);
    expect(h.search('coffee'), hasLength(1));
    expect(h.search('DART'), hasLength(1));
    expect(h.search('  '), hasLength(2));
  });

  test('JSON round trip preserves order, source and time', () {
    h.add('x', HistorySource.generated, at: t0);
    h.add('y', HistorySource.scanned, at: t0.add(const Duration(minutes: 1)));
    final copy = QrHistory.fromJson(h.toJson(), capacity: 3);
    expect(copy.toJson(), equals(h.toJson()));
    expect(copy.entries.first.payload, isA<TextPayload>());
  });

  test('remove and clear', () {
    h.add('x', HistorySource.scanned);
    h.add('y', HistorySource.scanned);
    h.removeAt(0);
    expect(h.entries.single.raw, equals('x'));
    h.clear();
    expect(h.isEmpty, isTrue);
    expect(() => QrHistory(capacity: 0), throwsArgumentError);
  });
}
