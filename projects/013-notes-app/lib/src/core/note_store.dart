/// Persistence backends for notes.
///
/// The repository depends only on the abstract [NoteStore], so the app can
/// use a JSON file on disk while tests use [InMemoryNoteStore]
/// (dependency inversion).
library;

import 'dart:convert';
import 'dart:io';

import 'note.dart';

abstract interface class NoteStore {
  Future<List<Note>> loadAll();
  Future<void> saveAll(List<Note> notes);
}

/// Keeps notes in memory only. Useful for tests and previews.
class InMemoryNoteStore implements NoteStore {
  InMemoryNoteStore([List<Note> initial = const []]) : _notes = [...initial];

  List<Note> _notes;
  int saveCount = 0;

  @override
  Future<List<Note>> loadAll() async => [..._notes];

  @override
  Future<void> saveAll(List<Note> notes) async {
    saveCount++;
    _notes = [...notes];
  }
}

/// Thrown when the notes file exists but cannot be parsed.
class NoteStoreException implements Exception {
  NoteStoreException(this.message);
  final String message;
  @override
  String toString() => 'NoteStoreException: $message';
}

/// Stores every note in one versioned JSON document.
///
/// Writes are atomic: data goes to a temporary sibling file which is then
/// renamed over the real one. A rename within one directory is atomic on
/// POSIX and NTFS, so a crash mid-write can never leave a half-written file.
class JsonFileNoteStore implements NoteStore {
  JsonFileNoteStore(this.file);

  static const int formatVersion = 1;
  final File file;

  @override
  Future<List<Note>> loadAll() async {
    if (!await file.exists()) return [];
    final text = await file.readAsString();
    if (text.trim().isEmpty) return [];
    try {
      final decoded = jsonDecode(text);
      if (decoded is! Map<String, Object?>) {
        throw NoteStoreException('top-level JSON must be an object');
      }
      final version = decoded['version'];
      if (version is! int || version > formatVersion) {
        throw NoteStoreException('unsupported format version: $version');
      }
      final list = decoded['notes'] as List<Object?>? ?? const [];
      return [for (final n in list) Note.fromJson(n! as Map<String, Object?>)];
    } on FormatException catch (e) {
      throw NoteStoreException('invalid JSON: ${e.message}');
    } on TypeError catch (e) {
      throw NoteStoreException('malformed note data: $e');
    }
  }

  @override
  Future<void> saveAll(List<Note> notes) async {
    await file.parent.create(recursive: true);
    final payload = const JsonEncoder.withIndent('  ').convert({
      'version': formatVersion,
      'notes': [for (final n in notes) n.toJson()],
    });
    final tmp = File('${file.path}.tmp');
    await tmp.writeAsString(payload, flush: true);
    await tmp.rename(file.path);
  }
}
