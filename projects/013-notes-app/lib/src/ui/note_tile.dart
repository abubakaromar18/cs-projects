import 'package:flutter/material.dart';

import '../core/format.dart';
import '../core/note.dart';
import '../core/search.dart';
import 'highlighted_text.dart';

/// One row in the notes list.
class NoteTile extends StatelessWidget {
  const NoteTile({
    super.key,
    required this.note,
    required this.query,
    required this.selected,
    required this.onTap,
    required this.onTogglePin,
  });

  final Note note;
  final SearchQuery query;
  final bool selected;
  final VoidCallback onTap;
  final VoidCallback onTogglePin;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final preview = note.preview();
    return ListTile(
      selected: selected,
      onTap: onTap,
      title: HighlightedText(
        note.displayTitle,
        query: query,
        maxLines: 1,
        style: theme.textTheme.titleMedium,
      ),
      subtitle: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (preview.isNotEmpty)
            HighlightedText(preview, query: query, maxLines: 2, style: theme.textTheme.bodySmall),
          const SizedBox(height: 4),
          // Wrap rather than Row so many tags flow onto a new line
          // instead of overflowing.
          Wrap(
            spacing: 6,
            children: [
              Text(
                formatRelative(note.updatedAt, DateTime.now()),
                style: theme.textTheme.labelSmall,
              ),
              for (final tag in (note.tags.toList()..sort()))
                Text(
                  '#$tag',
                  style: theme.textTheme.labelSmall?.copyWith(color: theme.colorScheme.primary),
                ),
            ],
          ),
        ],
      ),
      trailing: IconButton(
        tooltip: note.pinned ? 'Unpin' : 'Pin',
        icon: Icon(note.pinned ? Icons.push_pin : Icons.push_pin_outlined),
        onPressed: onTogglePin,
      ),
    );
  }
}
