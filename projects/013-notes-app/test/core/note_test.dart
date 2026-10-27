import 'package:flutter_test/flutter_test.dart';
import 'package:notes_app/notes_core.dart';

void main() {
  final t0 = DateTime.utc(2026, 1, 2, 3, 4, 5);

  Note make({
    String title = 'T',
    String body = 'B',
    Set<String> tags = const {},
    bool pinned = false,
  }) => Note(
    id: 'a',
    title: title,
    body: body,
    createdAt: t0,
    updatedAt: t0,
    tags: tags,
    pinned: pinned,
  );

  group('Note', () {
    test('round-trips through JSON', () {
      final n = make(tags: {'work', 'ideas'}, pinned: true);
      expect(Note.fromJson(n.toJson()), equals(n));
    });

    test('fromJson tolerates missing optional fields and normalizes tags', () {
      final n = Note.fromJson({
        'id': 'x',
        'createdAt': '2026-01-01T00:00:00.000Z',
        'updatedAt': '2026-01-01T00:00:00.000Z',
        'tags': ['#Work', '  ', 'Big Ideas'],
      });
      expect(n.title, equals(''));
      expect(n.pinned, isFalse);
      expect(n.tags, equals({'work', 'big-ideas'}));
    });

    test('displayTitle falls back to first body line, then placeholder', () {
      expect(make(title: '  Hello ').displayTitle, equals('Hello'));
      expect(make(title: '', body: '\n\n  first line\nsecond').displayTitle, equals('first line'));
      expect(make(title: '', body: '   ').displayTitle, equals('Untitled note'));
    });

    test('isEmpty ignores whitespace', () {
      expect(make(title: ' ', body: '\n\t').isEmpty, isTrue);
      expect(make(title: '', body: 'x').isEmpty, isFalse);
    });

    test('preview flattens whitespace and truncates with an ellipsis', () {
      final n = make(body: 'one\ntwo   three ${'x' * 200}');
      final p = n.preview(maxLength: 20);
      expect(p.length, lessThanOrEqualTo(20));
      expect(p.startsWith('one two three'), isTrue);
      expect(p.endsWith('…'), isTrue);
      expect(make(body: 'short').preview(), equals('short'));
    });

    test('copyWith keeps id and createdAt', () {
      final later = t0.add(const Duration(hours: 1));
      final c = make().copyWith(title: 'New', updatedAt: later);
      expect(c.id, equals('a'));
      expect(c.createdAt, equals(t0));
      expect(c.updatedAt, equals(later));
      expect(c.title, equals('New'));
      expect(c.body, equals('B'));
    });

    test('equality ignores tag order', () {
      expect(make(tags: {'a', 'b'}), equals(make(tags: {'b', 'a'})));
      expect(make(tags: {'a', 'b'}).hashCode, equals(make(tags: {'b', 'a'}).hashCode));
    });
  });

  group('tags', () {
    test('normalizeTag', () {
      expect(normalizeTag('  ##Work Stuff '), equals('work-stuff'));
      expect(normalizeTag('#'), equals(''));
    });

    test('parseTags splits on commas and whitespace', () {
      expect(parseTags('work, #Ideas  todo,,'), equals({'work', 'ideas', 'todo'}));
      expect(parseTags('   '), isEmpty);
    });
  });

  group('formatRelative', () {
    final now = DateTime(2026, 5, 10, 12);
    test('buckets', () {
      expect(formatRelative(now.subtract(const Duration(seconds: 30)), now), equals('just now'));
      expect(formatRelative(now.subtract(const Duration(minutes: 5)), now), equals('5 min ago'));
      expect(formatRelative(now.subtract(const Duration(hours: 3)), now), equals('3 h ago'));
      expect(formatRelative(now.subtract(const Duration(hours: 30)), now), equals('yesterday'));
      expect(formatRelative(DateTime(2026, 2, 3, 9), now), equals('2026-02-03'));
    });
  });
}
