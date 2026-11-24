import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../qr_core.dart';

/// Shows a parsed payload as labelled fields with copy buttons.
class PayloadDetails extends StatelessWidget {
  const PayloadDetails({super.key, required this.payload});

  final QrPayload payload;

  static IconData iconFor(QrPayload p) => switch (p) {
    UrlPayload() => Icons.link,
    WifiPayload() => Icons.wifi,
    EmailPayload() => Icons.email_outlined,
    PhonePayload() => Icons.phone_outlined,
    SmsPayload() => Icons.sms_outlined,
    GeoPayload() => Icons.place_outlined,
    ContactPayload() => Icons.person_outline,
    TextPayload() => Icons.notes,
  };

  /// (label, value) rows for each payload type. Pattern matching on the
  /// sealed class makes the compiler check every type is handled.
  static List<(String, String)> fieldsFor(QrPayload p) => switch (p) {
    UrlPayload(:final url) => [('URL', url)],
    WifiPayload(:final ssid, :final password, :final security, :final hidden) => [
      ('Network', ssid),
      ('Security', security.name.toUpperCase()),
      if (password.isNotEmpty) ('Password', password),
      if (hidden) ('Hidden', 'yes'),
    ],
    EmailPayload(:final to, :final subject, :final body) => [
      ('To', to),
      if (subject.isNotEmpty) ('Subject', subject),
      if (body.isNotEmpty) ('Body', body),
    ],
    PhonePayload(:final number) => [('Number', number)],
    SmsPayload(:final number, :final message) => [
      ('Number', number),
      if (message.isNotEmpty) ('Message', message),
    ],
    GeoPayload(:final latitude, :final longitude) => [
      ('Latitude', '$latitude'),
      ('Longitude', '$longitude'),
    ],
    ContactPayload(:final name, :final phone, :final email, :final org) => [
      ('Name', name),
      if (org.isNotEmpty) ('Organization', org),
      if (phone.isNotEmpty) ('Phone', phone),
      if (email.isNotEmpty) ('E-mail', email),
    ],
    TextPayload(:final text) => [('Text', text)],
  };

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      children: [
        Row(
          children: [
            Icon(iconFor(payload), color: theme.colorScheme.primary),
            const SizedBox(width: 8),
            Text(payload.kind, style: theme.textTheme.titleMedium),
          ],
        ),
        const SizedBox(height: 8),
        for (final (label, value) in fieldsFor(payload))
          ListTile(
            dense: true,
            contentPadding: EdgeInsets.zero,
            title: Text(label, style: theme.textTheme.labelMedium),
            subtitle: SelectableText(value, style: theme.textTheme.bodyLarge),
            trailing: IconButton(
              tooltip: 'Copy $label',
              icon: const Icon(Icons.copy, size: 18),
              onPressed: () => _copy(context, label, value),
            ),
          ),
      ],
    );
  }

  static Future<void> _copy(BuildContext context, String label, String value) async {
    await Clipboard.setData(ClipboardData(text: value));
    if (!context.mounted) return;
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(SnackBar(content: Text('$label copied')));
  }
}

/// Bottom sheet with details and (optionally) the code itself.
Future<void> showPayloadSheet(BuildContext context, String raw, {Widget? header}) {
  return showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    showDragHandle: true,
    builder: (context) => SafeArea(
      child: SingleChildScrollView(
        padding: const EdgeInsets.fromLTRB(24, 0, 24, 24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (header != null) ...[header, const SizedBox(height: 16)],
            PayloadDetails(payload: QrPayload.parse(raw)),
          ],
        ),
      ),
    ),
  );
}
