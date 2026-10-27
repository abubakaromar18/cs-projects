import 'package:flutter/material.dart';

import 'home_page.dart';
import 'notes_controller.dart';

class NotesApp extends StatelessWidget {
  const NotesApp({super.key, required this.controller});

  final NotesController controller;

  @override
  Widget build(BuildContext context) {
    const seed = Color(0xFFE8A33D); // warm amber, like a paper notepad
    return MaterialApp(
      title: 'Notes',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(colorScheme: ColorScheme.fromSeed(seedColor: seed), useMaterial3: true),
      darkTheme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: seed, brightness: Brightness.dark),
        useMaterial3: true,
      ),
      home: HomePage(controller: controller),
    );
  }
}
