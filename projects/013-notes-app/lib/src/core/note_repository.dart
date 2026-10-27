/// The single source of truth for notes.
///
/// Owns the in-memory collection, keeps the [SearchIndex] in sync with it,
/// and writes every change through to a [NoteStore]. Contains no Flutter
/// code, so it is fully unit-testable with plain `dart test`.
library;

import 'dart:math';

import 'note.dart';
import 'note_store.dart';
import 'search.dart';

typedef Clock = DateTime Function();
typedef IdGenerator = String Function();

/// Default id: time-based prefix (roughly sortable) plus random suffix.
IdGenerator defaultIdGenerator([Random? random]) {
  final rng = random ?? Random.secure();
  return () {
    final time = DateTime.now().microsecondsSinceEpoch.toRadixString(36);
    final rand = rng.nextInt(1 << 32).toRadixString(36).padLeft(7, '0');
    return '$time-$rand';
  };
}

class TagCount {
  const TagCount(this.tag, this.count);
  final String tag;
  final int count;

  @override
  bool operator ==(Object other) => other is TagCount && other.tag == tag && other.count == count;
  @override
  int get hashCode => Object.hash(tag, count);
  @override
  String toString() => '$tag($count)';
}

class NoteRepository {
  NoteRepository(this._store, {Clock? clock, IdGenerator? idGenerator})
    : _clock = clock ?? DateTime.now,
      _newId = idGenerator ?? defaultIdGenerator();

  final NoteStore _store;
  final Clock _clock;
  final IdGenerator _newId;
  final Map<String, Note> _notes = {};
  final SearchIndex _index = SearchIndex();

  // Serializes writes so saves land on disk in the order they were made.
  Future<void> _pendingSave = Future.value();

  /// Loads notes from the store, replacing whatever is in memory.
  Future<void> load() async {
    final loaded = await _store.loadAll();
    _notes.clear();
    _index.clear();
    for (final n in loaded) {
      _notes[n.id] = n;
      _index.put(n);
    }
  }

  int get length => _notes.length;

  /// All notes in display order (pinned first, newest first).
  List<Note> get notes => _notes.values.toList()..sort(compareNotes);

  Note? byId(String id) => _notes[id];

  Future<Note> create({String title = '', String body = '', Set<String> tags = const {}}) async {
    final now = _clock();
    final note = Note(
      id: _newId(),
      title: title,
      body: body,
      createdAt: now,
      updatedAt: now,
      tags: {for (final t in tags) normalizeTag(t)}..remove(''),
    );
    _put(note);
    await _save();
    return note;
  }

  /// Updates the given fields. `updatedAt` only moves when the title, body
  /// or tags actually change; pinning is not treated as an edit.
  Future<Note> update(
    String id, {
    String? title,
    String? body,
    Set<String>? tags,
    bool? pinned,
  }) async {
    final old = _notes[id];
    if (old == null) throw ArgumentError.value(id, 'id', 'no such note');
    final normalizedTags = tags == null
        ? null
        : ({for (final t in tags) normalizeTag(t)}..remove(''));
    final contentChanged =
        (title != null && title != old.title) ||
        (body != null && body != old.body) ||
        (normalizedTags != null &&
            (normalizedTags.length != old.tags.length || !normalizedTags.containsAll(old.tags)));
    final updated = old.copyWith(
      title: title,
      body: body,
      tags: normalizedTags,
      pinned: pinned,
      updatedAt: contentChanged ? _clock() : null,
    );
    if (updated == old) return old;
    _put(updated);
    await _save();
    return updated;
  }

  Future<Note> togglePin(String id) {
    final note = _notes[id];
    if (note == null) throw ArgumentError.value(id, 'id', 'no such note');
    return update(id, pinned: !note.pinned);
  }

  /// Deletes a note and returns it so the caller can offer "Undo".
  Future<Note?> delete(String id) async {
    final removed = _notes.remove(id);
    if (removed == null) return null;
    _index.remove(id);
    await _save();
    return removed;
  }

  /// Puts back a previously deleted note exactly as it was.
  Future<void> restore(Note note) async {
    _put(note);
    await _save();
  }

  /// Runs a query string (see [SearchQuery.parse] for the syntax).
  List<SearchResult> search(String query) => _index.search(SearchQuery.parse(query));

  /// Every tag in use with its note count, most used first.
  List<TagCount> get tags {
    final counts = <String, int>{};
    for (final n in _notes.values) {
      for (final t in n.tags) {
        counts[t] = (counts[t] ?? 0) + 1;
      }
    }
    return [for (final e in counts.entries) TagCount(e.key, e.value)]
      ..sort((a, b) => b.count != a.count ? b.count - a.count : a.tag.compareTo(b.tag));
  }

  void _put(Note note) {
    _notes[note.id] = note;
    _index.put(note);
  }

  Future<void> _save() {
    final snapshot = _notes.values.toList()..sort(compareNotes);
    // A failed earlier save must not poison every later one, so the chain
    // swallows the previous error (the caller that awaited it already saw it).
    return _pendingSave = _pendingSave
        .catchError((Object _) {})
        .then((_) => _store.saveAll(snapshot));
  }
}
