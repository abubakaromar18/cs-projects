import 'dart:async';

import 'package:flutter/material.dart';

import '../core/note.dart';
import 'notes_controller.dart';

/// Editor for one note, with debounced autosave.
///
/// Typing schedules a save [saveDelay] after the last keystroke, so a fast
/// typist triggers one disk write per pause rather than one per character.
/// Pending edits are flushed when the editor is closed.
class NoteEditor extends StatefulWidget {
  const NoteEditor({
    super.key,
    required this.controller,
    required this.noteId,
    this.showBackButton = true,
    this.onClosed,
    this.saveDelay = const Duration(milliseconds: 400),
  });

  final NotesController controller;
  final String noteId;
  final bool showBackButton;

  /// Called after the note is deleted from inside the editor.
  final VoidCallback? onClosed;
  final Duration saveDelay;

  @override
  State<NoteEditor> createState() => _NoteEditorState();
}

class _NoteEditorState extends State<NoteEditor> {
  late final TextEditingController _title;
  late final TextEditingController _body;
  late final TextEditingController _tags;
  Timer? _debounce;
  bool _dirty = false;

  @override
  void initState() {
    super.initState();
    final note = widget.controller.repository.byId(widget.noteId);
    _title = TextEditingController(text: note?.title ?? '');
    _body = TextEditingController(text: note?.body ?? '');
    _tags = TextEditingController(text: (note?.tags.toList()?..sort())?.join(', ') ?? '');
  }

  void _onChanged(String _) {
    _dirty = true;
    _debounce?.cancel();
    _debounce = Timer(widget.saveDelay, _flush);
  }

  Future<void> _flush() async {
    _debounce?.cancel();
    _debounce = null;
    if (!_dirty) return;
    _dirty = false;
    await widget.controller.updateNote(
      widget.noteId,
      title: _title.text,
      body: _body.text,
      tags: parseTags(_tags.text),
    );
  }

  @override
  void dispose() {
    // Save anything still pending, then drop the note if it is blank.
    final controller = widget.controller;
    final id = widget.noteId;
    unawaited(_flush().then((_) => controller.discardIfEmpty(id)));
    _title.dispose();
    _body.dispose();
    _tags.dispose();
    super.dispose();
  }

  Future<void> _delete() async {
    _debounce?.cancel();
    _dirty = false;
    final messenger = ScaffoldMessenger.of(context);
    final controller = widget.controller; // the editor may be gone by "Undo"
    final removed = await controller.delete(widget.noteId);
    widget.onClosed?.call();
    if (removed == null || removed.isEmpty) return;
    messenger.showSnackBar(
      SnackBar(
        content: Text('Deleted "${removed.displayTitle}"'),
        action: SnackBarAction(label: 'Undo', onPressed: () => controller.restore(removed)),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final note = widget.controller.repository.byId(widget.noteId);
    final theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(
        automaticallyImplyLeading: widget.showBackButton,
        title: const Text('Edit note'),
        actions: [
          if (note != null)
            IconButton(
              tooltip: note.pinned ? 'Unpin' : 'Pin',
              icon: Icon(note.pinned ? Icons.push_pin : Icons.push_pin_outlined),
              onPressed: () async {
                await widget.controller.togglePin(widget.noteId);
                if (mounted) setState(() {});
              },
            ),
          IconButton(tooltip: 'Delete', icon: const Icon(Icons.delete_outline), onPressed: _delete),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
        children: [
          TextField(
            key: const Key('titleField'),
            controller: _title,
            onChanged: _onChanged,
            style: theme.textTheme.headlineSmall,
            textInputAction: TextInputAction.next,
            decoration: const InputDecoration(hintText: 'Title', border: InputBorder.none),
          ),
          TextField(
            key: const Key('tagsField'),
            controller: _tags,
            onChanged: _onChanged,
            style: theme.textTheme.bodySmall?.copyWith(color: theme.colorScheme.primary),
            decoration: const InputDecoration(
              hintText: 'Tags (comma separated)',
              prefixIcon: Icon(Icons.sell_outlined, size: 18),
              border: InputBorder.none,
            ),
          ),
          const Divider(),
          TextField(
            key: const Key('bodyField'),
            controller: _body,
            onChanged: _onChanged,
            autofocus: note?.isEmpty ?? false,
            maxLines: null,
            minLines: 12,
            keyboardType: TextInputType.multiline,
            decoration: const InputDecoration(hintText: 'Start writing…', border: InputBorder.none),
          ),
        ],
      ),
    );
  }
}
