import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'note_editor.dart';
import 'note_tile.dart';
import 'notes_controller.dart';

/// Main screen. Adapts to the window size:
///  * wide (desktop / tablet): list and editor side by side (master-detail),
///  * narrow (phone): list only; tapping a note pushes the editor.
class HomePage extends StatefulWidget {
  const HomePage({super.key, required this.controller});

  static const double wideBreakpoint = 720;
  final NotesController controller;

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  final _searchController = TextEditingController();
  final _searchFocus = FocusNode();

  NotesController get _c => widget.controller;

  @override
  void dispose() {
    _searchController.dispose();
    _searchFocus.dispose();
    super.dispose();
  }

  Future<void> _open(String id, {required bool wide}) async {
    if (wide) {
      _c.select(id);
      return;
    }
    _c.select(id);
    await Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (context) => NoteEditor(
          controller: _c,
          noteId: id,
          onClosed: () => Navigator.of(context).maybePop(),
        ),
      ),
    );
    _c.select(null);
  }

  Future<void> _newNote({required bool wide}) async {
    final note = await _c.createNote();
    if (!mounted) return;
    await _open(note.id, wide: wide);
  }

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final wide = constraints.maxWidth >= HomePage.wideBreakpoint;
        return CallbackShortcuts(
          bindings: {
            const SingleActivator(LogicalKeyboardKey.keyN, control: true): () =>
                _newNote(wide: wide),
            const SingleActivator(LogicalKeyboardKey.keyN, meta: true): () => _newNote(wide: wide),
            const SingleActivator(LogicalKeyboardKey.keyF, control: true):
                _searchFocus.requestFocus,
            const SingleActivator(LogicalKeyboardKey.keyF, meta: true): _searchFocus.requestFocus,
          },
          child: Focus(
            autofocus: true,
            child: ListenableBuilder(
              listenable: _c,
              builder: (context, _) =>
                  wide ? _buildWide(context) : _buildList(context, wide: false),
            ),
          ),
        );
      },
    );
  }

  Widget _buildWide(BuildContext context) {
    final selected = _c.selected;
    return Row(
      children: [
        SizedBox(width: 360, child: _buildList(context, wide: true)),
        const VerticalDivider(width: 1),
        Expanded(
          child: selected == null
              ? const Scaffold(body: Center(child: Text('Select a note or create a new one')))
              : NoteEditor(
                  // A new key per note gives each note a fresh editor state.
                  key: ValueKey(selected.id),
                  controller: _c,
                  noteId: selected.id,
                  showBackButton: false,
                ),
        ),
      ],
    );
  }

  Widget _buildList(BuildContext context, {required bool wide}) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Notes'),
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(64),
          child: Padding(
            padding: const EdgeInsets.fromLTRB(12, 0, 12, 12),
            child: TextField(
              key: const Key('searchField'),
              controller: _searchController,
              focusNode: _searchFocus,
              onChanged: _c.setQuery,
              decoration: InputDecoration(
                hintText: 'Search  (try "phrase", -word, #tag, is:pinned)',
                prefixIcon: const Icon(Icons.search),
                suffixIcon: _c.query.isEmpty
                    ? null
                    : IconButton(
                        tooltip: 'Clear search',
                        icon: const Icon(Icons.close),
                        onPressed: () {
                          _searchController.clear();
                          _c.setQuery('');
                        },
                      ),
                filled: true,
                isDense: true,
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(28),
                  borderSide: BorderSide.none,
                ),
              ),
            ),
          ),
        ),
      ),
      floatingActionButton: FloatingActionButton(
        tooltip: 'New note (Ctrl+N)',
        onPressed: () => _newNote(wide: wide),
        child: const Icon(Icons.add),
      ),
      body: _buildBody(context, wide: wide),
    );
  }

  Widget _buildBody(BuildContext context, {required bool wide}) {
    if (_c.loading) return const Center(child: CircularProgressIndicator());
    if (_c.loadError != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Text('Could not load notes:\n${_c.loadError}', textAlign: TextAlign.center),
        ),
      );
    }
    if (!_c.hasNotes) {
      return const Center(
        child: Text('No notes yet.\nTap + to write your first one.', textAlign: TextAlign.center),
      );
    }
    final results = _c.results;
    final tags = _c.tags;
    return Column(
      children: [
        if (tags.isNotEmpty)
          SizedBox(
            height: 48,
            child: ListView(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 8),
              children: [
                for (final t in tags)
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 4),
                    child: FilterChip(
                      label: Text('#${t.tag} (${t.count})'),
                      selected: _c.parsedQuery.tags.contains(t.tag),
                      onSelected: (on) => _toggleTagFilter(t.tag, on),
                    ),
                  ),
              ],
            ),
          ),
        Expanded(
          child: results.isEmpty
              ? const Center(child: Text('No matching notes'))
              : ListView.separated(
                  itemCount: results.length,
                  separatorBuilder: (context, index) => const Divider(height: 1),
                  itemBuilder: (context, i) {
                    final note = results[i].note;
                    return NoteTile(
                      key: ValueKey(note.id),
                      note: note,
                      query: _c.parsedQuery,
                      selected: wide && note.id == _c.selectedId,
                      onTap: () => _open(note.id, wide: wide),
                      onTogglePin: () => _c.togglePin(note.id),
                    );
                  },
                ),
        ),
      ],
    );
  }

  /// Adds or removes `#tag` in the search box so chips and typed queries
  /// stay in sync.
  void _toggleTagFilter(String tag, bool on) {
    final words = _searchController.text.split(' ').where((w) => w.isNotEmpty).toList();
    words.removeWhere((w) => w.toLowerCase() == '#$tag' || w.toLowerCase() == 'tag:$tag');
    if (on) words.add('#$tag');
    final text = words.join(' ');
    _searchController.text = text;
    _c.setQuery(text);
  }
}
