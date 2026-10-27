import 'package:flutter/foundation.dart';

import '../../notes_core.dart';

/// UI state for the app: the current search query, the selected note and
/// load status. Wraps [NoteRepository] and notifies widgets on every change.
class NotesController extends ChangeNotifier {
  NotesController(this.repository);

  final NoteRepository repository;

  bool _loading = true;
  Object? _loadError;
  String _query = '';
  SearchQuery _parsed = const SearchQuery();
  String? _selectedId;

  bool get loading => _loading;
  Object? get loadError => _loadError;
  String get query => _query;
  SearchQuery get parsedQuery => _parsed;
  String? get selectedId => _selectedId;
  Note? get selected => _selectedId == null ? null : repository.byId(_selectedId!);
  bool get hasNotes => repository.length > 0;

  /// Notes matching the current query, best match first.
  List<SearchResult> get results => repository.search(_query);

  List<TagCount> get tags => repository.tags;

  Future<void> load() async {
    _loading = true;
    notifyListeners();
    try {
      await repository.load();
      _loadError = null;
    } catch (e) {
      _loadError = e;
    }
    _loading = false;
    notifyListeners();
  }

  void setQuery(String value) {
    if (value == _query) return;
    _query = value;
    _parsed = SearchQuery.parse(value);
    notifyListeners();
  }

  void select(String? id) {
    if (id == _selectedId) return;
    _selectedId = id;
    notifyListeners();
  }

  Future<Note> createNote() async {
    final tag = _parsed.tags.length == 1 ? _parsed.tags : const <String>{};
    // A new note created while filtering by one tag gets that tag, so it
    // stays visible in the filtered list.
    final note = await repository.create(tags: tag);
    _selectedId = note.id;
    notifyListeners();
    return note;
  }

  Future<void> updateNote(String id, {String? title, String? body, Set<String>? tags}) async {
    if (repository.byId(id) == null) return;
    await repository.update(id, title: title, body: body, tags: tags);
    notifyListeners();
  }

  Future<void> togglePin(String id) async {
    await repository.togglePin(id);
    notifyListeners();
  }

  /// Deletes a note; returns it so the UI can offer Undo.
  Future<Note?> delete(String id) async {
    final removed = await repository.delete(id);
    if (_selectedId == id) _selectedId = null;
    notifyListeners();
    return removed;
  }

  Future<void> restore(Note note) async {
    await repository.restore(note);
    notifyListeners();
  }

  /// Removes the note if the user left it completely blank.
  Future<void> discardIfEmpty(String id) async {
    final note = repository.byId(id);
    if (note != null && note.isEmpty) await delete(id);
  }
}
