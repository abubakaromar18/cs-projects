import 'dart:io';

import 'package:flutter/material.dart';
import 'package:path_provider/path_provider.dart';

import 'notes_core.dart';
import 'src/ui/app.dart';
import 'src/ui/notes_controller.dart';

/// Entry point: notes live in `notes.json` inside the platform's
/// application-support directory (e.g. ~/Library/Application Support on
/// macOS, %APPDATA% on Windows, ~/.local/share on Linux, app sandbox on
/// Android/iOS).
Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final dir = await getApplicationSupportDirectory();
  final store = JsonFileNoteStore(File('${dir.path}${Platform.pathSeparator}notes.json'));
  final controller = NotesController(NoteRepository(store));
  runApp(NotesApp(controller: controller));
  await controller.load();
}
