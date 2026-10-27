/// The immutable note model.
///
/// Notes are value objects: every edit produces a new instance via
/// [Note.copyWith]. Immutability keeps the repository and the search index
/// consistent, because nothing can change a note behind their backs.
library;

class Note {
  const Note({
    required this.id,
    required this.title,
    required this.body,
    required this.createdAt,
    required this.updatedAt,
    this.pinned = false,
    this.tags = const <String>{},
  });

  final String id;
  final String title;
  final String body;
  final DateTime createdAt;
  final DateTime updatedAt;
  final bool pinned;

  /// Lower-case tag names without the leading `#`.
  final Set<String> tags;

  /// A note with no title and no body is treated as empty and can be
  /// discarded when the user leaves the editor.
  bool get isEmpty => title.trim().isEmpty && body.trim().isEmpty;

  /// The title shown in lists: the explicit title, or else the first
  /// non-blank line of the body, or else a placeholder.
  String get displayTitle {
    if (title.trim().isNotEmpty) return title.trim();
    for (final line in body.split('\n')) {
      if (line.trim().isNotEmpty) return line.trim();
    }
    return 'Untitled note';
  }

  /// A single-line preview of the body (at most [maxLength] characters).
  String preview({int maxLength = 120}) {
    final flat = body.replaceAll(RegExp(r'\s+'), ' ').trim();
    if (flat.length <= maxLength) return flat;
    return '${flat.substring(0, maxLength - 1).trimRight()}…';
  }

  Note copyWith({
    String? title,
    String? body,
    DateTime? updatedAt,
    bool? pinned,
    Set<String>? tags,
  }) {
    return Note(
      id: id,
      title: title ?? this.title,
      body: body ?? this.body,
      createdAt: createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      pinned: pinned ?? this.pinned,
      tags: tags ?? this.tags,
    );
  }

  Map<String, Object?> toJson() => {
    'id': id,
    'title': title,
    'body': body,
    'createdAt': createdAt.toUtc().toIso8601String(),
    'updatedAt': updatedAt.toUtc().toIso8601String(),
    'pinned': pinned,
    'tags': (tags.toList()..sort()),
  };

  factory Note.fromJson(Map<String, Object?> json) {
    return Note(
      id: json['id']! as String,
      title: (json['title'] as String?) ?? '',
      body: (json['body'] as String?) ?? '',
      createdAt: DateTime.parse(json['createdAt']! as String),
      updatedAt: DateTime.parse(json['updatedAt']! as String),
      pinned: (json['pinned'] as bool?) ?? false,
      tags: {
        for (final t in (json['tags'] as List<Object?>?) ?? const []) normalizeTag(t! as String),
      }..remove(''),
    );
  }

  @override
  bool operator ==(Object other) =>
      other is Note &&
      other.id == id &&
      other.title == title &&
      other.body == body &&
      other.createdAt == createdAt &&
      other.updatedAt == updatedAt &&
      other.pinned == pinned &&
      other.tags.length == tags.length &&
      other.tags.containsAll(tags);

  @override
  int get hashCode =>
      Object.hash(id, title, body, createdAt, updatedAt, pinned, Object.hashAllUnordered(tags));

  @override
  String toString() => 'Note($id, "$displayTitle")';
}

/// Normalizes user-entered tags: trims, strips a leading `#`, lower-cases
/// and collapses inner whitespace to `-` ("#Work Stuff" → "work-stuff").
String normalizeTag(String raw) {
  var t = raw.trim();
  while (t.startsWith('#')) {
    t = t.substring(1);
  }
  return t.toLowerCase().replaceAll(RegExp(r'\s+'), '-');
}

/// Parses a comma- or space-separated tag field into a normalized set.
Set<String> parseTags(String input) =>
    {for (final part in input.split(RegExp(r'[,\s]+'))) normalizeTag(part)}..remove('');
