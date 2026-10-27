/// Full-text search over notes.
///
/// Implements a small search engine:
///  * a Unicode-aware tokenizer,
///  * an inverted index (term → postings) for fast lookups,
///  * prefix ("search-as-you-type") expansion with binary search over a
///    sorted term dictionary,
///  * a tiny query language: `words`, `"exact phrases"`, `-excluded`,
///    `tag:work` / `#work`, and `is:pinned`,
///  * TF-IDF ranking with a title boost.
library;

import 'dart:math' as math;

import 'note.dart';

// ---------------------------------------------------------------------------
// Tokenizer
// ---------------------------------------------------------------------------

/// A token and its character offsets in the source text (end exclusive).
class Token {
  const Token(this.term, this.start, this.end);
  final String term;
  final int start;
  final int end;

  @override
  String toString() => 'Token($term, $start, $end)';
}

final RegExp _wordPattern = RegExp(r"[\p{L}\p{N}]+(?:'[\p{L}]+)?", unicode: true);

/// Splits [text] into lower-case word tokens, keeping their offsets so the
/// UI can highlight matches in the original text.
List<Token> tokenize(String text) => [
  for (final m in _wordPattern.allMatches(text)) Token(m[0]!.toLowerCase(), m.start, m.end),
];

// ---------------------------------------------------------------------------
// Query parsing
// ---------------------------------------------------------------------------

/// A parsed search query.
class SearchQuery {
  const SearchQuery({
    this.terms = const [],
    this.phrases = const [],
    this.excluded = const [],
    this.tags = const {},
    this.pinnedOnly = false,
  });

  /// Required words; each matches any indexed term it is a prefix of.
  final List<String> terms;

  /// Required exact phrases, each already tokenized.
  final List<List<String>> phrases;

  /// Words that must not appear (exact match).
  final List<String> excluded;

  /// Required tags (all must be present).
  final Set<String> tags;

  final bool pinnedOnly;

  bool get isEmpty =>
      terms.isEmpty && phrases.isEmpty && excluded.isEmpty && tags.isEmpty && !pinnedOnly;

  /// Every word the user is looking for, used for highlighting.
  Iterable<String> get highlightTerms sync* {
    yield* terms;
    for (final p in phrases) {
      yield* p;
    }
  }

  static final RegExp _chunk = RegExp(r'(-?)"([^"]*)"?|(\S+)');

  /// Parses a raw query string. Never throws: malformed input such as an
  /// unterminated quote is interpreted as leniently as possible.
  factory SearchQuery.parse(String input) {
    final terms = <String>[];
    final phrases = <List<String>>[];
    final excluded = <String>[];
    final tags = <String>{};
    var pinnedOnly = false;

    for (final m in _chunk.allMatches(input)) {
      final phrase = m[2];
      if (phrase != null) {
        final words = tokenize(phrase).map((t) => t.term).toList();
        if (words.isEmpty) continue;
        if (m[1] == '-') {
          excluded.addAll(words);
        } else if (words.length == 1) {
          terms.add(words.single);
        } else {
          phrases.add(words);
        }
        continue;
      }

      final raw = m[3]!;
      final lower = raw.toLowerCase();
      if (lower == 'is:pinned') {
        pinnedOnly = true;
      } else if (lower.startsWith('tag:') || (raw.startsWith('#') && raw.length > 1)) {
        final tag = normalizeTag(lower.startsWith('tag:') ? raw.substring(4) : raw);
        if (tag.isNotEmpty) tags.add(tag);
      } else if (raw.startsWith('-') && raw.length > 1) {
        excluded.addAll(tokenize(raw.substring(1)).map((t) => t.term));
      } else {
        terms.addAll(tokenize(raw).map((t) => t.term));
      }
    }

    return SearchQuery(
      terms: terms,
      phrases: phrases,
      excluded: excluded,
      tags: tags,
      pinnedOnly: pinnedOnly,
    );
  }
}

// ---------------------------------------------------------------------------
// Inverted index
// ---------------------------------------------------------------------------

/// How often a term occurs in one note's title and body.
class _Posting {
  int titleFreq = 0;
  int bodyFreq = 0;
}

class SearchResult {
  const SearchResult(this.note, this.score);
  final Note note;
  final double score;

  @override
  String toString() => 'SearchResult(${note.id}, ${score.toStringAsFixed(3)})';
}

/// An incrementally maintained inverted index over a set of notes.
class SearchIndex {
  /// Weight of a title occurrence relative to a body occurrence.
  static const double titleBoost = 3.0;

  /// Score multiplier when a query word only matches as a prefix.
  static const double prefixPenalty = 0.6;

  final Map<String, Map<String, _Posting>> _postings = {};
  final Map<String, Set<String>> _termsByNote = {};
  final Map<String, Note> _notes = {};

  // Sorted term dictionary for prefix search; rebuilt lazily when stale.
  List<String> _sortedTerms = const [];
  bool _dictionaryStale = false;

  int get length => _notes.length;
  int get termCount => _postings.length;

  /// Adds [note], replacing any earlier version with the same id.
  void put(Note note) {
    remove(note.id);
    _notes[note.id] = note;
    final terms = <String>{};
    for (final t in tokenize(note.title)) {
      _postingFor(t.term, note.id).titleFreq++;
      terms.add(t.term);
    }
    for (final t in tokenize(note.body)) {
      _postingFor(t.term, note.id).bodyFreq++;
      terms.add(t.term);
    }
    _termsByNote[note.id] = terms;
  }

  void remove(String id) {
    if (_notes.remove(id) == null) return;
    for (final term in _termsByNote.remove(id) ?? const <String>{}) {
      final postings = _postings[term]!;
      postings.remove(id);
      if (postings.isEmpty) {
        _postings.remove(term);
        _dictionaryStale = true;
      }
    }
  }

  void clear() {
    _postings.clear();
    _termsByNote.clear();
    _notes.clear();
    _sortedTerms = const [];
    _dictionaryStale = false;
  }

  _Posting _postingFor(String term, String id) {
    final postings = _postings.putIfAbsent(term, () {
      _dictionaryStale = true;
      return {};
    });
    return postings.putIfAbsent(id, _Posting.new);
  }

  /// All indexed terms that start with [prefix], in sorted order.
  ///
  /// Uses binary search to find the first candidate (O(log n)) and then
  /// walks forward while terms still share the prefix.
  List<String> termsWithPrefix(String prefix) {
    if (_dictionaryStale) {
      _sortedTerms = _postings.keys.toList()..sort();
      _dictionaryStale = false;
    }
    var lo = 0, hi = _sortedTerms.length;
    while (lo < hi) {
      final mid = (lo + hi) >> 1;
      if (_sortedTerms[mid].compareTo(prefix) < 0) {
        lo = mid + 1;
      } else {
        hi = mid;
      }
    }
    final out = <String>[];
    for (var i = lo; i < _sortedTerms.length && _sortedTerms[i].startsWith(prefix); i++) {
      out.add(_sortedTerms[i]);
    }
    return out;
  }

  /// Inverse document frequency: rare terms count more than common ones.
  double _idf(String term) {
    final df = _postings[term]?.length ?? 0;
    return math.log(1 + _notes.length / (df + 1)) + 1e-6;
  }

  /// Runs [query] and returns matches, best first. An empty query returns
  /// every note in default order (pinned, then most recently updated).
  List<SearchResult> search(SearchQuery query) {
    Iterable<String> candidates = _notes.keys;
    final scores = <String, double>{};

    // Each query word must match (AND); its prefix expansions are OR-ed.
    for (final word in query.terms) {
      final wordScores = <String, double>{};
      for (final term in termsWithPrefix(word)) {
        final weight = _idf(term) * (term == word ? 1.0 : prefixPenalty);
        _postings[term]!.forEach((id, p) {
          final tf = titleBoost * p.titleFreq + p.bodyFreq;
          // Sub-linear TF so one word repeated 50 times doesn't dominate.
          final s = weight * (1 + math.log(tf));
          wordScores[id] = math.max(wordScores[id] ?? 0, s);
        });
      }
      candidates = candidates.where(wordScores.containsKey).toList();
      for (final id in candidates) {
        scores[id] = (scores[id] ?? 0) + wordScores[id]!;
      }
    }

    // Phrases: cheap filter via the index, then verify adjacency.
    for (final phrase in query.phrases) {
      candidates = candidates.where((id) {
        final terms = _termsByNote[id]!;
        if (!phrase.every(terms.contains)) return false;
        final note = _notes[id]!;
        return _containsPhrase(note.title, phrase) || _containsPhrase(note.body, phrase);
      }).toList();
      for (final id in candidates) {
        scores[id] = (scores[id] ?? 0) + phrase.map(_idf).fold(0.0, (a, b) => a + b) * 2;
      }
    }

    final results = <SearchResult>[];
    for (final id in candidates) {
      final note = _notes[id]!;
      if (query.pinnedOnly && !note.pinned) continue;
      if (!note.tags.containsAll(query.tags)) continue;
      if (query.excluded.any(_termsByNote[id]!.contains)) continue;
      results.add(SearchResult(note, scores[id] ?? 0));
    }

    results.sort((a, b) {
      final byScore = b.score.compareTo(a.score);
      if (byScore != 0) return byScore;
      return compareNotes(a.note, b.note);
    });
    return results;
  }

  static bool _containsPhrase(String text, List<String> phrase) {
    final words = tokenize(text).map((t) => t.term).toList();
    outer:
    for (var i = 0; i + phrase.length <= words.length; i++) {
      for (var j = 0; j < phrase.length; j++) {
        if (words[i + j] != phrase[j]) continue outer;
      }
      return true;
    }
    return false;
  }
}

/// Default note ordering: pinned first, then most recently updated, then id
/// as a stable tie-breaker.
int compareNotes(Note a, Note b) {
  if (a.pinned != b.pinned) return a.pinned ? -1 : 1;
  final byDate = b.updatedAt.compareTo(a.updatedAt);
  if (byDate != 0) return byDate;
  return a.id.compareTo(b.id);
}

/// Character ranges in [text] that match the query's words (prefix match),
/// merged so adjacent/overlapping ranges become one. Used for highlighting.
List<(int, int)> highlightRanges(String text, SearchQuery query) {
  final words = query.highlightTerms.toSet();
  if (words.isEmpty) return const [];
  final ranges = <(int, int)>[];
  for (final t in tokenize(text)) {
    if (words.any(t.term.startsWith)) {
      if (ranges.isNotEmpty && ranges.last.$2 >= t.start) {
        ranges[ranges.length - 1] = (ranges.last.$1, t.end);
      } else {
        ranges.add((t.start, t.end));
      }
    }
  }
  return ranges;
}
