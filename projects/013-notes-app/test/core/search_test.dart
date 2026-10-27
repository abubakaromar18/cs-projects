import 'package:flutter_test/flutter_test.dart';
import 'package:notes_app/notes_core.dart';

Note note(
  String id,
  String title,
  String body, {
  Set<String> tags = const {},
  bool pinned = false,
  int minute = 0,
}) {
  final t = DateTime.utc(2026, 1, 1, 0, minute);
  return Note(
    id: id,
    title: title,
    body: body,
    createdAt: t,
    updatedAt: t,
    tags: tags,
    pinned: pinned,
  );
}

List<String> ids(List<SearchResult> rs) => [for (final r in rs) r.note.id];

void main() {
  group('tokenize', () {
    test('lower-cases, keeps offsets, handles unicode and apostrophes', () {
      final toks = tokenize("Café déjà-vu, it's 42!");
      expect(toks.map((t) => t.term).toList(), equals(['café', 'déjà', 'vu', "it's", '42']));
      expect(toks.first.start, equals(0));
      expect(toks.first.end, equals(4));
    });

    test('empty and punctuation-only input', () {
      expect(tokenize(''), isEmpty);
      expect(tokenize('!!! ... ---'), isEmpty);
    });
  });

  group('SearchQuery.parse', () {
    test('plain words, phrases, exclusions, tags, pinned', () {
      final q = SearchQuery.parse('Flutter "state management" -redux tag:Work #ideas is:pinned');
      expect(q.terms, equals(['flutter']));
      expect(
        q.phrases,
        equals([
          ['state', 'management'],
        ]),
      );
      expect(q.excluded, equals(['redux']));
      expect(q.tags, equals({'work', 'ideas'}));
      expect(q.pinnedOnly, isTrue);
    });

    test('single-word phrase becomes a term; unterminated quote is lenient', () {
      final q = SearchQuery.parse('"hello" "open phrase');
      expect(q.terms, equals(['hello']));
      expect(
        q.phrases,
        equals([
          ['open', 'phrase'],
        ]),
      );
    });

    test('lone symbols are ignored', () {
      expect(SearchQuery.parse('  -  #  "" ').isEmpty, isTrue);
    });
  });

  group('SearchIndex', () {
    late SearchIndex index;

    setUp(() {
      index = SearchIndex()
        ..put(note('1', 'Grocery list', 'milk eggs bread', tags: {'home'}, minute: 1))
        ..put(
          note('2', 'Flutter ideas', 'state management with riverpod', tags: {'work'}, minute: 2),
        )
        ..put(
          note(
            '3',
            'Meeting notes',
            'discussed flutter release and state of the project',
            tags: {'work'},
            minute: 3,
          ),
        )
        ..put(note('4', 'Recipes', 'bread bread bread bread', pinned: true, minute: 0));
    });

    test('empty query returns all notes, pinned first then newest', () {
      expect(ids(index.search(const SearchQuery())), equals(['4', '3', '2', '1']));
    });

    test('words are ANDed', () {
      expect(ids(index.search(SearchQuery.parse('flutter state'))).toSet(), equals({'2', '3'}));
      expect(ids(index.search(SearchQuery.parse('flutter milk'))), isEmpty);
    });

    test('prefix matching (search as you type)', () {
      expect(ids(index.search(SearchQuery.parse('flut'))).toSet(), equals({'2', '3'}));
      expect(ids(index.search(SearchQuery.parse('gro'))), equals(['1']));
    });

    test('title matches outrank body matches', () {
      // "flutter" is in note 2's title but only in note 3's body.
      expect(ids(index.search(SearchQuery.parse('flutter'))).first, equals('2'));
    });

    test('exact match outranks prefix match', () {
      index.put(note('5', 'x', 'bread', minute: 9));
      index.put(note('6', 'x', 'breadcrumbs', minute: 9));
      final r = index.search(SearchQuery.parse('bread'));
      expect(ids(r).indexOf('5'), lessThan(ids(r).indexOf('6')));
    });

    test('phrases require adjacent words', () {
      expect(ids(index.search(SearchQuery.parse('"state management"'))), equals(['2']));
      // Note 3 has both words but not adjacent.
      expect(ids(index.search(SearchQuery.parse('"flutter state"'))), isEmpty);
    });

    test('exclusions, tags and pinned filters', () {
      expect(ids(index.search(SearchQuery.parse('flutter -riverpod'))), equals(['3']));
      expect(ids(index.search(SearchQuery.parse('#home'))), equals(['1']));
      expect(ids(index.search(SearchQuery.parse('bread is:pinned'))), equals(['4']));
      expect(ids(index.search(SearchQuery.parse('tag:work state'))).toSet(), equals({'2', '3'}));
    });

    test('updating a note re-indexes it', () {
      index.put(note('1', 'Grocery list', 'apples only'));
      expect(ids(index.search(SearchQuery.parse('milk'))), isEmpty);
      expect(ids(index.search(SearchQuery.parse('apples'))), equals(['1']));
      expect(index.length, equals(4));
    });

    test('removing a note drops its terms from the dictionary', () {
      index.remove('1');
      expect(index.termsWithPrefix('mil'), isEmpty);
      expect(index.termsWithPrefix('bre'), equals(['bread'])); // still in note 4
      index.remove('missing'); // no-op
      expect(index.length, equals(3));
    });

    test('termsWithPrefix returns sorted matches via binary search', () {
      index.put(note('9', '', 'stack stash stage stale zebra a'));
      expect(index.termsWithPrefix('sta'), equals(['stack', 'stage', 'stale', 'stash', 'state']));
      expect(index.termsWithPrefix('zz'), isEmpty);
      expect(index.termsWithPrefix('a'), contains('a'));
    });
  });

  group('highlightRanges', () {
    test('finds prefix matches and merges touching ranges', () {
      final q = SearchQuery.parse('fl st');
      expect(highlightRanges('Flutter state', q), equals([(0, 7), (8, 13)]));
      expect(highlightRanges('nothing here', q), isEmpty);
      expect(highlightRanges('anything', const SearchQuery()), isEmpty);
    });
  });
}
