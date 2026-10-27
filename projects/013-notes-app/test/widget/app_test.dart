import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:notes_app/notes_core.dart';
import 'package:notes_app/src/ui/app.dart';
import 'package:notes_app/src/ui/notes_controller.dart';

Note _seed(String id, String title, String body, {Set<String> tags = const {}, int minute = 0}) {
  final t = DateTime(2026, 1, 1, 0, minute);
  return Note(id: id, title: title, body: body, createdAt: t, updatedAt: t, tags: tags);
}

Future<NotesController> _pumpApp(
  WidgetTester tester, {
  required Size size,
  List<Note> notes = const [],
}) async {
  tester.view.physicalSize = size;
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.reset);

  final controller = NotesController(NoteRepository(InMemoryNoteStore(notes)));
  await controller.load();
  await tester.pumpWidget(NotesApp(controller: controller));
  await tester.pumpAndSettle();
  return controller;
}

final _seedNotes = [
  _seed('1', 'Groceries', 'milk, eggs and bread', tags: {'home'}, minute: 1),
  _seed('2', 'Flutter ideas', 'try a master-detail layout', tags: {'work'}, minute: 2),
];

void main() {
  testWidgets('shows an empty state when there are no notes', (tester) async {
    await _pumpApp(tester, size: const Size(400, 800));
    expect(find.textContaining('No notes yet'), findsOneWidget);
  });

  testWidgets('search filters the list', (tester) async {
    await _pumpApp(tester, size: const Size(400, 800), notes: _seedNotes);
    expect(find.text('Groceries'), findsOneWidget);
    expect(find.text('Flutter ideas'), findsOneWidget);

    await tester.enterText(find.byKey(const Key('searchField')), 'milk');
    await tester.pump();
    expect(find.text('Groceries'), findsOneWidget);
    expect(find.text('Flutter ideas'), findsNothing);

    await tester.enterText(find.byKey(const Key('searchField')), 'nothing-matches-this');
    await tester.pump();
    expect(find.text('No matching notes'), findsOneWidget);
  });

  testWidgets('tag chip filters by tag', (tester) async {
    await _pumpApp(tester, size: const Size(400, 800), notes: _seedNotes);
    await tester.tap(find.widgetWithText(FilterChip, '#work (1)'));
    await tester.pump();
    expect(find.text('Flutter ideas'), findsOneWidget);
    expect(find.text('Groceries'), findsNothing);
  });

  testWidgets('phone layout: create a note, type, go back, see it listed', (tester) async {
    final controller = await _pumpApp(tester, size: const Size(400, 800));

    await tester.tap(find.byType(FloatingActionButton));
    await tester.pumpAndSettle();
    expect(find.text('Edit note'), findsOneWidget);

    await tester.enterText(find.byKey(const Key('titleField')), 'Shopping');
    await tester.enterText(find.byKey(const Key('bodyField')), 'Buy apples');
    await tester.pump(const Duration(milliseconds: 500)); // let autosave fire

    await tester.pageBack();
    await tester.pumpAndSettle();

    expect(find.text('Shopping'), findsOneWidget);
    expect(controller.repository.notes.single.body, equals('Buy apples'));
  });

  testWidgets('phone layout: a blank new note is discarded on back', (tester) async {
    final controller = await _pumpApp(tester, size: const Size(400, 800));
    await tester.tap(find.byType(FloatingActionButton));
    await tester.pumpAndSettle();
    await tester.pageBack();
    await tester.pumpAndSettle();
    expect(controller.repository.length, equals(0));
  });

  testWidgets('desktop layout: list and editor side by side', (tester) async {
    await _pumpApp(tester, size: const Size(1200, 800), notes: _seedNotes);
    expect(find.text('Select a note or create a new one'), findsOneWidget);

    await tester.tap(find.text('Groceries'));
    await tester.pumpAndSettle();

    // Editor opened next to the list, without navigating away.
    expect(find.text('Edit note'), findsOneWidget);
    expect(find.byKey(const Key('searchField')), findsOneWidget);
    final title = tester.widget<TextField>(find.byKey(const Key('titleField')));
    expect(title.controller!.text, equals('Groceries'));
  });

  testWidgets('delete offers undo', (tester) async {
    final controller = await _pumpApp(tester, size: const Size(1200, 800), notes: _seedNotes);
    await tester.tap(find.text('Groceries'));
    await tester.pumpAndSettle();

    await tester.tap(find.byTooltip('Delete'));
    await tester.pumpAndSettle();
    expect(controller.repository.length, equals(1));
    expect(find.text('Undo'), findsOneWidget);

    await tester.tap(find.text('Undo'));
    await tester.pumpAndSettle();
    expect(controller.repository.length, equals(2));
  });
}
