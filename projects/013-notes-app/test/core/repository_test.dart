import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:notes_app/notes_core.dart';

/// A clock tests can move forward by hand.
class FakeClock {
  DateTime now = DateTime.utc(2026, 3, 1, 9);
  DateTime call() => now;
  void advance([Duration d = const Duration(minutes: 1)]) => now = now.add(d);
}

IdGenerator sequentialIds() {
  var n = 0;
  return () => 'n${++n}';
}

void main() {
  late FakeClock clock;
  late InMemoryNoteStore store;
  late NoteRepository repo;

  setUp(() async {
    clock = FakeClock();
    store = InMemoryNoteStore();
    repo = NoteRepository(store, clock: clock.call, idGenerator: sequentialIds());
    await repo.load();
  });

  group('NoteRepository', () {
    test('create persists and indexes the note', () async {
      final n = await repo.create(title: 'Hello', body: 'world', tags: {'#Greeting'});
      expect(n.id, equals('n1'));
      expect(n.tags, equals({'greeting'}));
      expect(store.saveCount, equals(1));
      expect((await store.loadAll()).single, equals(n));
      expect(repo.search('wor').single.note.id, equals('n1'));
    });

    test('notes are ordered pinned first, then most recently updated', () async {
      final a = await repo.create(title: 'a');
      clock.advance();
      final b = await repo.create(title: 'b');
      clock.advance();
      final c = await repo.create(title: 'c');
      expect(repo.notes.map((n) => n.id).toList(), equals([c.id, b.id, a.id]));
      await repo.togglePin(a.id);
      expect(repo.notes.map((n) => n.id).toList(), equals([a.id, c.id, b.id]));
    });

    test('update bumps updatedAt only when content changes', () async {
      final n = await repo.create(title: 'x');
      clock.advance();
      final pinned = await repo.update(n.id, pinned: true);
      expect(pinned.updatedAt, equals(n.updatedAt), reason: 'pinning is not an edit');

      final same = await repo.update(n.id, title: 'x', tags: {});
      expect(identical(same, pinned), isTrue, reason: 'no-op update returns the same note');
      final saves = store.saveCount;

      clock.advance();
      final edited = await repo.update(n.id, body: 'new body');
      expect(edited.updatedAt.isAfter(n.updatedAt), isTrue);
      expect(store.saveCount, equals(saves + 1));
    });

    test('update of unknown id throws', () async {
      await expectLater(repo.update('nope', title: 'x'), throwsArgumentError);
    });

    test('delete returns the note and restore brings it back', () async {
      final n = await repo.create(title: 'Keep me', body: 'precious');
      final removed = await repo.delete(n.id);
      expect(removed, equals(n));
      expect(repo.length, equals(0));
      expect(repo.search('precious'), isEmpty);
      expect(await repo.delete(n.id), isNull);

      await repo.restore(removed!);
      expect(repo.byId(n.id), equals(n));
      expect(repo.search('precious').single.note, equals(n));
    });

    test('tags are counted and sorted by frequency then name', () async {
      await repo.create(tags: {'work', 'b'});
      await repo.create(tags: {'work', 'a'});
      await repo.create(tags: {'home'});
      expect(
        repo.tags,
        equals([
          const TagCount('work', 2),
          const TagCount('a', 1),
          const TagCount('b', 1),
          const TagCount('home', 1),
        ]),
      );
    });

    test('load replaces in-memory state from the store', () async {
      await repo.create(title: 'first');
      final other = NoteRepository(store, clock: clock.call);
      await other.load();
      expect(other.notes.single.title, equals('first'));
      expect(other.search('first'), hasLength(1));
    });

    test('a failed save does not block later saves', () async {
      final flaky = _FlakyStore();
      final r = NoteRepository(flaky, clock: clock.call, idGenerator: sequentialIds());
      flaky.failNext = true;
      await expectLater(r.create(title: 'one'), throwsA(isA<StateError>()));
      await r.create(title: 'two');
      expect(flaky.saved.map((n) => n.title).toSet(), equals({'one', 'two'}));
    });
  });

  group('JsonFileNoteStore', () {
    late Directory dir;
    setUp(() async => dir = await Directory.systemTemp.createTemp('notes_test'));
    tearDown(() async => dir.delete(recursive: true));

    test('missing or blank file loads as empty', () async {
      final s = JsonFileNoteStore(File('${dir.path}/notes.json'));
      expect(await s.loadAll(), isEmpty);
      await File('${dir.path}/notes.json').writeAsString('  \n');
      expect(await s.loadAll(), isEmpty);
    });

    test('save then load round-trips and leaves no temp file', () async {
      final file = File('${dir.path}/nested/notes.json');
      final s = JsonFileNoteStore(file);
      final r = NoteRepository(s, clock: clock.call, idGenerator: sequentialIds());
      await r.create(title: 'Über', body: 'emoji 📝 ok', tags: {'x'});
      await r.create(title: 'second');

      final reloaded = await JsonFileNoteStore(file).loadAll();
      expect(reloaded, hasLength(2));
      expect(reloaded.map((n) => n.title).toSet(), equals({'Über', 'second'}));
      expect(File('${file.path}.tmp').existsSync(), isFalse);
    });

    test('corrupt or future-version files raise NoteStoreException', () async {
      final file = File('${dir.path}/notes.json');
      final s = JsonFileNoteStore(file);
      await file.writeAsString('{not json');
      await expectLater(s.loadAll(), throwsA(isA<NoteStoreException>()));
      await file.writeAsString('{"version": 99, "notes": []}');
      await expectLater(s.loadAll(), throwsA(isA<NoteStoreException>()));
      await file.writeAsString('{"version": 1, "notes": [{"id": 5}]}');
      await expectLater(s.loadAll(), throwsA(isA<NoteStoreException>()));
    });
  });
}

class _FlakyStore implements NoteStore {
  bool failNext = false;
  List<Note> saved = [];

  @override
  Future<List<Note>> loadAll() async => saved;

  @override
  Future<void> saveAll(List<Note> notes) async {
    if (failNext) {
      failNext = false;
      throw StateError('disk full');
    }
    saved = notes;
  }
}
