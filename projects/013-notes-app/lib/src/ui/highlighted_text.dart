import 'package:flutter/material.dart';

import '../core/search.dart';

/// Text with search matches highlighted.
class HighlightedText extends StatelessWidget {
  const HighlightedText(this.text, {super.key, required this.query, this.style, this.maxLines});

  final String text;
  final SearchQuery query;
  final TextStyle? style;
  final int? maxLines;

  @override
  Widget build(BuildContext context) {
    final ranges = highlightRanges(text, query);
    final base = style ?? DefaultTextStyle.of(context).style;
    if (ranges.isEmpty) {
      return Text(text, style: base, maxLines: maxLines, overflow: TextOverflow.ellipsis);
    }
    final scheme = Theme.of(context).colorScheme;
    final highlight = base.copyWith(
      backgroundColor: scheme.tertiaryContainer,
      color: scheme.onTertiaryContainer,
      fontWeight: FontWeight.w600,
    );
    final spans = <TextSpan>[];
    var cursor = 0;
    for (final (start, end) in ranges) {
      if (start > cursor) spans.add(TextSpan(text: text.substring(cursor, start)));
      spans.add(TextSpan(text: text.substring(start, end), style: highlight));
      cursor = end;
    }
    if (cursor < text.length) spans.add(TextSpan(text: text.substring(cursor)));
    return Text.rich(
      TextSpan(style: base, children: spans),
      maxLines: maxLines,
      overflow: TextOverflow.ellipsis,
    );
  }
}
